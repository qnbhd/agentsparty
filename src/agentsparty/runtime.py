"""Binds participants to roles and executes a global protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Sequence
from typing import Final, Protocol, cast

from agentsparty._utils.assertions import post
from agentsparty.journal.types import (
    NULL_JOURNAL,
    ROOT_TRACK,
    Decision,
    Journal,
    Script,
    StepIndex,
    Track,
)
from agentsparty.kernel.budget import (
    DEFAULT_ALLOWANCE,
    NOTHING_SPENT,
    ONE_STEP,
    ONE_UNFOLDING,
    Allowance,
    Spent,
)
from agentsparty.kernel.errors import (
    DeadlineExceeded,
    JournalError,
    PayloadError,
    RecursionLimitError,
    StepLimitError,
    fault,
)
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.participant import Cancelled, Envelope, Participant
from agentsparty.protocol.language.core import Chosen, Deadline, Fragment, Label
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.protocol.session import (
    as_global,
    assert_wellformed,
    ensure_session,
    participants,
    project,
    unfold,
)
from agentsparty.protocol.session.types import (
    GlobalType,
    Interaction,
    Parallel,
    SessionBranchCase,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
)
from agentsparty.tracing.scope import Scope, new_scope
from agentsparty.tracing.signals import (
    Delivered,
    Failed,
    Forked,
    Recalled,
    Selected,
    SessionCancelled,
    SessionFinished,
    SessionStarted,
    StepStarted,
    Unfolded,
)
from agentsparty.tracing.types import NULL_TRACER, Tracer

_NAMES_SEPARATOR: Final = ', '


class Casting(Protocol):
    """Factory that binds a role to a participant given its projected endpoint.

    The type of the second argument to :meth:`Cast.play`. Implemented by the
    factories in :mod:`agentsparty.agent`, :mod:`agentsparty.human`, :mod:`agentsparty.machine`,
    and :mod:`agentsparty.toolbox`.
    """

    def __call__(self, role: Role, endpoint: EndpointType, /) -> Participant:
        """Return a participant for *role* under *endpoint*."""
        ...


async def _tell(participant: Participant, notice: Cancelled, scope: Scope) -> Role:
    """Tell *participant* the session is over; return the role that heard it.

    A participant whose own ``cancel`` raises must not silence the others and
    must not replace the failure that caused the cancellation: its fault is
    recorded and the broadcast goes on. This is the one place in the runtime
    that swallows an exception, and it swallows it into the trace.

    Args:
        participant: The peer to notify.
        notice: Why the session was rolled up.
        scope: The session scope, where a failing ``cancel`` is recorded.

    Returns:
        The role that was told.
    """
    try:
        await participant.cancel(notice)
    except Exception as error:
        role = participant.role.name
        reason = fault(error)
        scope.record(Failed(f'`{role}` could not be told: {reason}'))
    return participant.role


async def _tell_each(
    participants: Sequence[Participant],
    notice: Cancelled,
    scope: Scope,
) -> list[Role]:
    """Notify bound participants sequentially; preserve binding order."""
    remaining = list(participants)
    heard: list[Role] = []
    while remaining:
        heard.append(await _tell(remaining.pop(0), notice, scope))
    return heard


async def _select_within(
    selecting: Awaitable[Chosen[SessionBranchCase]],
    window: Deadline,
    sender: Role,
    receiver: Role,
) -> Chosen[SessionBranchCase]:
    """Await *selecting* under *window*; raise DeadlineExceeded on timeout."""
    try:
        return await asyncio.wait_for(selecting, timeout=window.total_seconds())
    except asyncio.TimeoutError as error:
        # On 3.10 ``asyncio.TimeoutError`` is not the builtin ``TimeoutError``.
        raise DeadlineExceeded(_deadline_message(window, sender, receiver)) from error


def _deadline_message(window: Deadline, sender: Role, receiver: Role) -> str:
    seconds = window.total_seconds()
    window_text = format(seconds, 'g')
    sender_name = sender.name
    receiver_name = receiver.name
    head = f'sender {sender_name} did not choose within'
    return f'{head} {window_text}s for {receiver_name}'


def _bind_participants(
    proto: SessionType,
    bound_participants: Sequence[Participant],
) -> dict[str, Participant]:
    required = {role.name for role in participants(proto)}
    by_role: dict[str, Participant] = {}
    for peer in bound_participants:
        name = peer.role.name
        if name in by_role:
            raise ValueError(
                f'duplicate participant for role {name!r}: bind exactly '
                'one participant per role required by the protocol',
            )
        by_role[name] = peer

    error = _participant_binding_error(required, by_role)
    if error:
        raise ValueError(error)

    return by_role


class AgentRuntime:
    """Bind roles to peer participants and drive the global protocol."""

    def __init__(
        self,
        proto: SessionType | Fragment[SessionType],
        participants: Sequence[Participant],
        *,
        allowance: Allowance = DEFAULT_ALLOWANCE,
        tracer: Tracer = NULL_TRACER,
        journal: Journal = NULL_JOURNAL,
    ) -> None:
        """Bind *participants* to the roles required by *proto*.

        Args:
            proto: The choreography to execute. A still-open
                :class:`~agentsparty.protocol.language.core.Fragment` is closed at this
                boundary. Must be guarded (validated via
                :func:`agentsparty.protocol.assert_wellformed`).
            participants: One participant per role. Missing, duplicate or
                extra roles raise :exc:`ValueError`.
            allowance: What one :meth:`run` may spend in unfoldings and
                protocol steps. Replayed decisions from a journal do not
                consume the allowance. Defaults to
                :data:`~agentsparty.kernel.budget.DEFAULT_ALLOWANCE`.
            tracer: Observability sink for the session; defaults to a no-op.
            journal: Durable record of the alts made. Decisions already in
                it are replayed instead of being asked again; new ones are
                appended before they are delivered. Defaults to
                ``NULL_JOURNAL``, which records nothing and replays nothing.

        Raises:
            ValueError: if the protocol is ill-formed or the participants do
                not match the protocol roles.
            RecursionLimitError: if a :meth:`run` exhausts the unfolding
                allowance before the protocol reaches ``end``.
            StepLimitError: if a :meth:`run` exhausts the step allowance.
        """
        closed = ensure_session(proto)
        assert_wellformed(closed)
        self._proto = as_global(closed)
        self._participants = tuple(participants)
        self._allowance = allowance
        self._tracer = tracer
        self._journal = journal
        self._delivered: dict[Track, list[Envelope]] = {}
        self._by_role = _bind_participants(closed, self._participants)

    @property
    def proto(self) -> GlobalType:
        """The choreography this runtime executes."""
        return self._proto

    @property
    def participants(self) -> tuple[Participant, ...]:
        """The participants bound to the protocol roles, in binding order."""
        return self._participants

    @property
    def allowance(self) -> Allowance:
        """What one :meth:`run` may spend."""
        return self._allowance

    @property
    def tracer(self) -> Tracer:
        """The observability sink for this session."""
        return self._tracer

    @property
    def journal(self) -> Journal:
        """The durable record of the alts made."""
        return self._journal

    @property
    def trace(self) -> list[Envelope]:
        """Delivered envelopes in canonical order: root track, then branches.

        A linear extension of the causal order, chosen so that the value does
        not depend on how the scheduler interleaved independent branches. The
        wall-clock order is in the tracer, not here.
        """
        return [
            envelope for track in sorted(self._delivered) for envelope in self._delivered[track]
        ]

    async def run(self) -> list[Envelope]:
        """Execute the protocol and return the trace of delivered envelopes.

        Decisions already in the journal are replayed: the participant that
        made them is reminded via ``recall`` and no model is called. Everything
        after the journal's last step is asked live and recorded as it is made,
        so an interrupted session resumes by calling ``run()`` again.

        A session that ends anywhere other than ``end`` is rolled up: every
        bound participant is told once via ``cancel``, ``SessionCancelled`` is
        recorded, and the failure is re-raised unchanged. ``KeyboardInterrupt``
        and task cancellation are ``BaseException`` and deliberately not
        caught.

        Returns:
            One envelope per delivered message, in delivery order.
        """
        self._delivered.clear()
        script = self._journal.script()
        with new_scope(self._tracer).open(
            SessionStarted(
                self._proto,
                tuple(participants(self._proto)),
            ),
        ) as session:
            try:
                await self._step(
                    self._proto,
                    ROOT_TRACK,
                    NOTHING_SPENT,
                    session,
                    script,
                )
            except Exception as error:
                # cancellation is choreography, not the caller's business:
                await self._cancel(Cancelled.of(error), session)
                raise
            if len(self.trace) < script.length:
                raise JournalError(
                    f'journal records {script.length} decisions but the '
                    f'protocol delivered only {len(self.trace)} envelopes',
                )
            session.record(SessionFinished(len(self.trace)))
        return list(self.trace)

    def run_sync(self) -> list[Envelope]:
        """Run the protocol on a fresh event loop and return the delivery trace.

        Thin wrapper over :meth:`run` via :func:`asyncio.run`. Do not call
        from a thread that already has a running event loop — use ``await
        runtime.run()`` there instead.

        Returns:
            One envelope per delivered message, in delivery order.
        """
        # pre: no running loop in this thread (asyncio.run enforces it).
        return asyncio.run(self.run())

    def _get(self, role: Role) -> Participant:
        return self._by_role[role.name]

    async def _cancel(self, notice: Cancelled, scope: Scope) -> None:
        """Tell every bound participant that the session is rolled up.

        The cancellation of one endpoint is announced to everyone belonging to
        the session, in the order the participants were bound, so a replayed
        failure records the same trace.

        Args:
            notice: Why the session was rolled up.
            scope: The session scope, where the cancellation is recorded.
        """
        scope.record(SessionCancelled(notice))
        heard = await _tell_each(self._participants, notice, scope)
        post(
            expr=sorted(role.name for role in heard)
            == sorted(one.role.name for one in self._participants),
            message='every bound participant must hear the cancellation exactly once',
        )

    async def _step(
        self,
        node: GlobalType,
        track: Track,
        spent: Spent,
        scope: Scope,
        script: Script,
    ) -> None:
        while True:
            next_node, spent = await self._step_once(node, track, spent, scope, script)
            if next_node is None:
                return
            node = next_node

    async def _step_once(
        self,
        node: GlobalType,
        track: Track,
        spent: Spent,
        scope: Scope,
        script: Script,
    ) -> tuple[GlobalType | None, Spent]:
        match node:
            case SessionEnd():
                self._check_end(track, script)
                return None, spent
            case SessionRec(name=name):
                next_spent = self._unfolding(name, track, spent, script)
                scope.record(Unfolded(name, self._remaining_unfoldings(next_spent)))
                return cast(GlobalType, unfold(node)), next_spent
            case SessionVar(name=name):
                raise RuntimeError(
                    f'free recursion variable {name!r} reached the stepper; '
                    'root should be well-formed and steps preserve closedness',
                )
            case Parallel(branches=branches):
                scope.record(Forked(len(branches)))
                await self._run_branches(
                    cast(Sequence[GlobalType], branches),
                    track,
                    spent,
                    scope,
                    script,
                )
                return None, spent
            case Interaction(sender=sender, receiver=receiver, branches=branches):
                next_node, next_spent = await self._step_interaction(
                    sender,
                    receiver,
                    branches,
                    track,
                    spent,
                    scope,
                    script,
                )
                return cast(GlobalType, next_node), next_spent
            case _:  # pragma: no cover
                raise TypeError(f'unexpected global node: {node!r}')

    def _check_end(self, track: Track, script: Script) -> None:
        delivered = len(self._delivered.get(track, ()))
        expected = script.length_of(track)
        if delivered < expected:
            raise JournalError(
                f'journal records {expected} decisions on track {track.path} '
                f'but the protocol delivered only {delivered} envelopes there',
            )

    def _remaining_unfoldings(self, spent: Spent) -> int | None:
        if self._allowance.unfoldings is None:
            return None
        return self._allowance.unfoldings - spent.unfoldings

    async def _step_interaction(
        self,
        sender: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, SessionBranchCase],
        track: Track,
        spent: Spent,
        scope: Scope,
        script: Script,
    ) -> tuple[SessionType, Spent]:
        spent = self._stepping(track, spent, script)
        with scope.child().open(
            StepStarted(
                sender,
                receiver,
                tuple(branch.label for branch in branches.values()),
            ),
        ) as step:
            chosen = await self._choose(track, script, sender, receiver, branches, step)
            await self._deliver(track, sender, receiver, chosen, step)
        return chosen.branch.continuation, spent

    async def _deliver(
        self,
        track: Track,
        sender: Role,
        receiver: Role,
        chosen: Chosen[SessionBranchCase],
        step: Scope,
    ) -> None:
        envelope = Envelope(
            sender=sender,
            receiver=receiver,
            label=chosen.branch.label,
            payload=chosen.payload,
        )
        self._delivered.setdefault(track, []).append(envelope)
        await self._get(receiver).offer(envelope)
        step.record(Delivered(envelope))

    async def _run_branches(
        self,
        branches: Sequence[GlobalType],
        track: Track,
        spent: Spent,
        scope: Scope,
        script: Script,
    ) -> None:
        """Run every branch of a parallel node concurrently.

        Branches own disjoint roles and exchange no message, so any order of
        execution is a legal linearisation of the same trace. The journal
        cannot tell concurrent from sequential — that is the point of tracks.

        The allowance is handed to each branch unchanged: ``spent`` measures
        one causal path, and parallel branches are separate paths.
        """
        running = [
            asyncio.ensure_future(
                self._step(branch, track.branch(index), spent, scope, script),
            )
            for index, branch in enumerate(branches)
        ]
        await _join(running)

    def _replaying(self, track: Track, script: Script) -> bool:
        """Whether the next message on *track* still comes from *script*."""
        return len(self._delivered.get(track, ())) < script.length_of(track)

    def _unfolding(
        self,
        name: str,
        track: Track,
        spent: Spent,
        script: Script,
    ) -> Spent:
        """The spend after unfolding *name*.

        Replayed unfoldings are free: the journal is finite and already
        happened, so charging it would make a long recursive session
        unresumable. Only live unfoldings are charged.

        Args:
            name: The binder being unfolded.
            track: The track the unfolding sits on.
            spent: The spend before this unfolding.
            script: The decisions being replayed.

        Returns:
            The spend after this unfolding.

        Raises:
            RecursionLimitError: if a live unfolding exceeds the allowance.
        """
        if self._replaying(track, script):
            return spent
        next_spent = spent + ONE_UNFOLDING
        if not self._allowance.covers(next_spent):
            unfoldings = self._allowance.unfoldings
            raise RecursionLimitError(
                self._allowance_message(
                    'unfolding allowance exhausted before unfolding '
                    f'{name!r} (limit={unfoldings}); pass Allowance(unfoldings=None) '
                    'for unbounded execution',
                ),
            )
        return next_spent

    def _stepping(self, track: Track, spent: Spent, script: Script) -> Spent:
        """The spend after one protocol step, charged before the alt is made.

        Replayed steps are free, matching :meth:`_unfolding`.

        Args:
            track: The track the step sits on.
            spent: The spend before this step.
            script: The decisions being replayed.

        Returns:
            The spend after this step.

        Raises:
            StepLimitError: if a live step exceeds the allowance.
        """
        if self._replaying(track, script):
            return spent
        next_spent = spent + ONE_STEP
        if not self._allowance.covers(next_spent):
            steps = self._allowance.steps
            raise StepLimitError(
                self._allowance_message(
                    f'step allowance exhausted (limit={steps}); '
                    'pass Allowance(steps=None) for unbounded steps',
                ),
            )
        return next_spent

    def _idle_role_names(self) -> list[str]:
        """Roles that never sent or received in the envelopes delivered so far."""
        active = {envelope.sender.name for envelope in self.trace} | {
            envelope.receiver.name for envelope in self.trace
        }
        required = {role.name for role in participants(self._proto)}
        return sorted(required - active)

    def _allowance_message(self, head: str) -> str:
        """*head*, plus idle-role starvation diagnosis when any role was silent."""
        idle = self._idle_role_names()
        if not idle:
            return head
        named = _NAMES_SEPARATOR.join(idle)
        return (
            f'{head}\n'
            f'Roles that never sent or received in this session: {named}.\n'
            'This usually means a participant narrowed its alt and starved '
            'another role — not that the allowance is too small.'
        )

    async def _choose(
        self,
        track: Track,
        script: Script,
        sender: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, SessionBranchCase],
        scope: Scope,
    ) -> Chosen[SessionBranchCase]:
        """Take the next step from *script* when it is recorded, else ask *sender*.

        Args:
            track: The track this message belongs to.
            script: The decisions already recorded for this session.
            sender: The role choosing a branch.
            receiver: The role that will receive the message.
            branches: The labelled alternatives on offer.
            scope: The step's tracing scope.

        Returns:
            The chosen branch together with its payload.
        """
        delivered = self._delivered.get(track, ())
        step = StepIndex(track, len(delivered) + 1)
        if step.position > script.length_of(track):
            return await self._ask(step, sender, receiver, branches, scope)
        return await self._recall(script.at(step), sender, receiver, branches, scope)

    async def _ask(
        self,
        step: StepIndex,
        sender: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, SessionBranchCase],
        scope: Scope,
    ) -> Chosen[SessionBranchCase]:
        """Ask *sender* to choose, and record the alt before it is delivered.

        Args:
            step: The position the message will occupy.
            sender: The role choosing a branch.
            receiver: The role that will receive the message.
            branches: The labelled alternatives on offer.
            scope: The step's tracing scope.

        Returns:
            The chosen branch together with its payload.
        """
        chosen = await self._select(sender, receiver, branches)
        post(
            expr=chosen.branch.payload.decode(chosen.raw) == chosen.payload,
            message='select returned a payload that does not decode from its raw form',
        )
        scope.record(Selected(chosen.branch.label, chosen.payload))
        self._journal.append(
            Decision(
                step,
                sender,
                receiver,
                chosen.branch.label,
                chosen.branch.payload.name,
                chosen.raw,
            ),
        )
        return chosen

    async def _select(
        self,
        sender: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, SessionBranchCase],
    ) -> Chosen[SessionBranchCase]:
        """Ask *sender* to choose, enforcing the tightest branch deadline if any.

        Args:
            sender: The role choosing a branch.
            receiver: The role that will receive the message.
            branches: The labelled alternatives on offer.

        Returns:
            The chosen branch together with its payload.

        Raises:
            DeadlineExceeded: if the sender does not choose in time.
        """
        selecting = self._get(sender).select(receiver, branches)
        window = _select_window(branches)
        if window is None:
            return await selecting
        return await _select_within(selecting, window, sender, receiver)

    async def _recall(
        self,
        decision: Decision,
        sender: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, SessionBranchCase],
        scope: Scope,
    ) -> Chosen[SessionBranchCase]:
        """Rebuild a recorded alt and remind *sender* that it made it.

        Args:
            decision: The recorded alt for this step.
            sender: The role that made it.
            receiver: The role that received the message.
            branches: The labelled alternatives on offer.
            scope: The step's tracing scope.

        Returns:
            The recorded branch together with its decoded payload.

        Raises:
            JournalError: if the decision does not fit this protocol node.
        """
        branch = decision.branch_in(sender, receiver, branches)
        try:
            payload = branch.payload.decode(decision.raw)
        except PayloadError as exc:
            track_path = decision.step.track.path
            position = decision.step.position
            payload_name = branch.payload.name
            raise JournalError(
                f'step {track_path} #{position} raw does not decode under {payload_name}: {exc}',
            ) from exc
        scope.record(Recalled(branch.label, payload))
        await self._get(sender).recall(
            Envelope(
                sender=sender,
                receiver=receiver,
                label=branch.label,
                payload=payload,
            ),
        )
        return Chosen(branch=branch, payload=payload, raw=decision.raw)


async def _join(running: Sequence[asyncio.Future[None]]) -> None:
    """Await every branch; on the first failure cancel the rest and re-raise.

    A session that lost one branch is over, so the siblings are stopped
    before they spend anything else. The failure that ends the session is the
    one the caller sees; the roll-up that tells every participant is
    ``run``'s, unchanged.
    """
    done, pending = await asyncio.wait(running, return_when=asyncio.FIRST_EXCEPTION)
    failures = [error for task in done if (error := task.exception()) is not None]
    if not failures:
        return
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    raise failures[0]


def _select_window(
    branches: NonEmptyMap[Label, SessionBranchCase],
) -> Deadline | None:
    """The tightest positive wall-clock window among *branches*, if any."""
    windows = [branch.within for branch in branches.values() if branch.within is not None]
    if not windows:
        return None
    return min(windows, key=Deadline.total_seconds)


class Cast:
    """A partial section of projection: roles bound to factories over endpoints.

    The protocol is stated once. Each :meth:`play` extends the section for one
    role; :meth:`runtime` / :meth:`run` demand totality and name any unplayed
    roles. Immutable: :meth:`play` returns a new :class:`Cast`.
    """

    def __init__(
        self,
        proto: SessionType | Fragment[SessionType],
        _players: tuple[Participant, ...] = (),
    ) -> None:
        """Close *proto* if needed, validate it, and start an empty cast.

        Args:
            proto: The choreography (or fragment) every player will share.
            _players: Already-bound participants (internal; used by :meth:`play`).
        """
        closed = ensure_session(proto)
        assert_wellformed(closed)
        self._proto = as_global(closed)
        self._players = _players

    @property
    def proto(self) -> GlobalType:
        """The closed choreography this cast binds."""
        return self._proto

    def play(self, role: Role, casting: Casting) -> Cast:
        """Bind *role* by applying *casting* to its projected endpoint.

        Args:
            role: A role of :attr:`proto`.
            casting: Factory ``(role, endpoint) -> participant``.

        Returns:
            A new cast that also includes this player.

        Raises:
            ValueError: if *role* is not in the protocol or is already played.
        """
        required = {r.name for r in participants(self._proto)}
        if role.name not in required:
            required_names = _NAMES_SEPARATOR.join(sorted(required))
            raise ValueError(
                f'role {role.name!r} is not in the protocol; required: {required_names}',
            )
        if any(player.role.name == role.name for player in self._players):
            raise ValueError(f'role {role.name!r} is already cast')
        endpoint = project(self._proto, role)
        participant = casting(role, endpoint)
        return Cast(self._proto, (*self._players, participant))

    def runtime(
        self,
        *,
        allowance: Allowance = DEFAULT_ALLOWANCE,
        tracer: Tracer = NULL_TRACER,
        journal: Journal = NULL_JOURNAL,
    ) -> AgentRuntime:
        """Build an :class:`AgentRuntime` when every role is cast.

        Raises:
            ValueError: if any protocol role is still unplayed (named).
        """
        required = {r.name for r in participants(self._proto)}
        present = {player.role.name for player in self._players}
        missing = sorted(required - present)
        if missing:
            missing_names = _NAMES_SEPARATOR.join(missing)
            required_names = _NAMES_SEPARATOR.join(sorted(required))
            raise ValueError(
                f'missing participants for roles: {missing_names}. '
                f'The protocol requires: {required_names}',
            )
        return AgentRuntime(
            self._proto,
            self._players,
            allowance=allowance,
            tracer=tracer,
            journal=journal,
        )

    async def run(
        self,
        *,
        allowance: Allowance = DEFAULT_ALLOWANCE,
        tracer: Tracer = NULL_TRACER,
        journal: Journal = NULL_JOURNAL,
    ) -> list[Envelope]:
        """Totality then :meth:`AgentRuntime.run`."""
        return await self.runtime(
            allowance=allowance,
            tracer=tracer,
            journal=journal,
        ).run()

    def run_sync(
        self,
        *,
        allowance: Allowance = DEFAULT_ALLOWANCE,
        tracer: Tracer = NULL_TRACER,
        journal: Journal = NULL_JOURNAL,
    ) -> list[Envelope]:
        """Totality then :meth:`AgentRuntime.run_sync`."""
        return self.runtime(
            allowance=allowance,
            tracer=tracer,
            journal=journal,
        ).run_sync()


def _participant_binding_error(
    required: set[str],
    by_role: dict[str, Participant],
) -> str | None:
    missing = sorted(required - set(by_role))
    if missing:
        missing_names = _NAMES_SEPARATOR.join(missing)
        required_names = _NAMES_SEPARATOR.join(sorted(required))
        return (
            f'missing participants for roles: {missing_names}. '
            f'The protocol requires: {required_names}'
        )
    extra = sorted(set(by_role) - required)
    if extra:
        extra_names = _NAMES_SEPARATOR.join(extra)
        required_names = _NAMES_SEPARATOR.join(sorted(required))
        return (
            f'unexpected participants for roles: {extra_names}. '
            f'The protocol requires: {required_names}'
        )
    return None


__all__ = ['AgentRuntime', 'Cast', 'Casting']
