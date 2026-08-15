"""Toolboxes: participants that answer requests instead of authoring intent.

A toolbox binds a family of tools to a role whose projected endpoint protocol is a
*service*: it never speaks first, and it answers every request it accepts, at
once, to the role that asked. The protocol owns the request schema; a tool
declares the codec it was written against so binding can reject a tool wired to
the wrong branch.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any, Generic, TypeAlias, TypeVar

from typing_extensions import assert_never

from agentsparty._utils.assertions import post, pre
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.participant import Cancelled, Choice, Envelope, Participant, chosen_branch
from agentsparty.protocol import SessionType, associate
from agentsparty.protocol.language.core import (
    BranchCodec,
    Case,
    Chosen,
    Codec,
    Label,
    RawValue,
    _as_label,
)
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointBranchCase,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    EndpointVar,
)
from agentsparty.tracing.scope import current
from agentsparty.tracing.signals import ToolAnswered, ToolCalled

T = TypeVar('T')
B = TypeVar('B', bound=BranchCodec)


@dataclass(frozen=True, slots=True)
class Tool(Generic[T]):
    """One request a toolbox answers, and the effect that answers it.

    The protocol declares the argument's schema; :attr:`request` is the codec
    the handler was written against, so a tool wired to the wrong branch is
    rejected when the toolbox is built rather than when the session runs.

    ``answer`` receives the decoded request and nothing else — not the
    conversation, not the role that asked, not the runtime. A decision that
    needs the history belongs in a :class:`~agentsparty.machine.Machine`.
    """

    label: Label
    request: Codec[T]
    answer: Callable[[T], Awaitable[Choice]]


def tool(
    label: str | Label,
    request: Codec[T],
    answer: Callable[[T], Awaitable[Choice]],
) -> Tool[T]:
    """Build a :class:`Tool` for a label and its request codec."""
    return Tool(_as_label(label), request, answer)


def tool_for(
    declared: Case[Any],
    answer: Callable[[Any], Awaitable[Choice]],
) -> Tool[Any]:
    """Build a :class:`Tool` from a case that already declares its codec."""
    return Tool(declared.label, declared.payload, answer)


def reply(label: str | Label | Case[Any], payload: RawValue = None) -> Choice:
    """The answer a tool returns: the reply branch it picks and its raw payload.

    The payload stays raw here and is decoded at the boundary, so
    ``branch.payload.decode(raw) == payload`` holds by construction and a
    journalled session replays the same value.

    Args:
        label: The reply branch the protocol offers for this request, or a
            :class:`~agentsparty.protocol.language.core.Case` that names it.
        payload: The raw form of the answer; ``None`` for a reply that carries
            no value.

    Returns:
        The tool's alt among the reply branches.
    """
    match label:
        case Case() as declared:
            return Choice(declared.label, payload)
        case _:
            return Choice(_as_label(label), payload)


def _requests(node: EndpointType) -> dict[Label, Codec[Any]]:
    """The request each tool must answer, keyed by label.

    Walks a projected endpoint type and rejects anything that is not a *service*:
    a type that never speaks first and answers every request it accepts, right
    away, to the role that asked. Accepting only this shape is what makes the
    outstanding-request slot in :class:`Toolbox` provably single-valued.

    Args:
        node: The toolbox role's projected endpoint protocol.

    Returns:
        One entry per request label, holding the codec its argument decodes
        under.

    Raises:
        ValueError: if *node* is not a service type, or if one label appears
            twice carrying different payload codecs.
    """
    found: dict[Label, Codec[Any]] = {}
    _collect(node, found)
    if not found:
        raise ValueError('a toolbox must answer at least one request')
    return found


def _collect(node: EndpointType, found: dict[Label, Codec[Any]]) -> None:
    """Add every request reachable from *node* to *found*.

    Args:
        node: The endpoint protocol position being walked.
        found: The table being built; mutated in place.

    Raises:
        ValueError: if *node* is not a service type.
    """
    match node:
        case EndpointEnd() | EndpointVar():
            return
        case EndpointRec(body=body):
            _collect(body, found)
        case EndpointSelect(receiver=receiver):
            raise ValueError(
                f'a toolbox only answers, but this one speaks first to {receiver.name}',
            )
        case EndpointBranch(sender=sender, branches=branches):
            for request in branches.values():
                _remember(request, found)
                _collect_replies(request, sender, found)
        case _:  # pragma: no cover
            assert_never(node)


def _remember(request: EndpointBranchCase, found: dict[Label, Codec[Any]]) -> None:
    """Record *request*'s codec, rejecting a label used with two payloads.

    One label is served by one tool, so the same label reached by two paths has
    to carry the same argument.

    Args:
        request: The request branch being recorded.
        found: The table being built; mutated in place.

    Raises:
        ValueError: if *request*'s label already carries another codec.
    """
    seen = found.get(request.label)
    if seen is not None and seen.name != request.payload.name:
        request_name = request.payload.name
        raise ValueError(
            f'request {request.label} appears with two payloads: {seen.name} and {request_name}',
        )
    found[request.label] = request.payload


def _collect_replies(
    request: EndpointBranchCase,
    asker: Role,
    found: dict[Label, Codec[Any]],
) -> None:
    """Require *request* to be answered to *asker*, then walk past the answer.

    The answer must follow the request immediately: a recursion binder written
    between them is rejected, because the binder belongs outside the request.

    Args:
        request: The request branch whose continuation is being checked.
        asker: The role that sent *request* and must receive the answer.
        found: The table being built; mutated in place.

    Raises:
        ValueError: if *request* is not answered to *asker* right away.
    """
    match request.continuation:
        case EndpointSelect(receiver=receiver, branches=replies) if receiver == asker:
            for answer in replies.values():
                _collect(answer.continuation, found)
        case _:
            raise ValueError(
                f'request {request.label} is not answered to {asker.name} right after it arrives',
            )


@dataclass(frozen=True, slots=True)
class _Idle:
    """No request is waiting to be answered."""


@dataclass(frozen=True, slots=True)
class _Pending:
    """The request a toolbox owes an answer to."""

    label: Label
    payload: object


_Awaiting: TypeAlias = _Idle | _Pending
_IDLE: _Awaiting = _Idle()


def _outstanding(awaiting: _Awaiting, subject: Role) -> _Pending:
    """The request waiting for an answer.

    The empty case is unreachable for a toolbox built by :class:`Toolbox`: its
    projection was accepted by :func:`_requests`, so every answer it is asked
    for follows a request it was just given.

    Args:
        awaiting: The toolbox's slot.
        subject: The toolbox's own role, for the failure message.

    Returns:
        The request to answer.
    """
    match awaiting:
        case _Pending() as pending:
            return pending
        case _Idle():
            raise AssertionError(f'{subject.name} was asked to answer nothing')
        case _:  # pragma: no cover
            assert_never(awaiting)


def _match_tools(
    requests: Mapping[Label, Codec[Any]],
    tools: Iterable[Tool[Any]],
    subject: Role,
) -> NonEmptyMap[Label, Tool[Any]]:
    """Pair every request the protocol declares with the tool that answers it.

    Codecs are compared by name, the same way a journal checks a recorded
    decision: a ``Codec`` holds a function, so two structurally equal codecs
    are not equal values.

    Args:
        requests: What the projected endpoint type asks for.
        tools: The tools offered for those requests.
        subject: The toolbox's own role, for the failure messages.

    Returns:
        One tool per request label.

    Raises:
        ValueError: if a request has no tool, a tool answers nothing, two tools
            share a label, or a tool was written against another codec.
    """
    catalogue = NonEmptyMap.check_pairs((one.label, one) for one in tools)
    if catalogue is None:
        raise ValueError(f'toolbox {subject.name} was given no tools')
    _require_tool_labels(requests, catalogue, subject)
    _require_tool_codecs(requests, catalogue, subject)
    return catalogue


def _require_tool_labels(
    requests: Mapping[Label, Codec[Any]],
    catalogue: NonEmptyMap[Label, Tool[Any]],
    subject: Role,
) -> None:
    checks = (
        (requests.keys() - catalogue.keys(), 'has no tool for'),
        (catalogue.keys() - requests.keys(), 'is never asked for'),
    )
    for labels, complaint in checks:
        if labels:
            names = ', '.join(sorted(str(lbl) for lbl in labels))
            raise ValueError(f'toolbox {subject.name} {complaint}: {names}')


def _require_tool_codecs(
    requests: Mapping[Label, Codec[Any]],
    catalogue: NonEmptyMap[Label, Tool[Any]],
    subject: Role,
) -> None:
    mismatched = tuple(
        (label, requests[label], catalogue[label])
        for label in requests
        if requests[label].name != catalogue[label].request.name
    )
    if not mismatched:
        return

    # fmt: off
    wrong = sorted(
        f'{lbl} carries {req}, tool reads {tool}'
        for (lbl, req, tool) in mismatched
    )
    # fmt: on

    wrong_names = '; '.join(wrong)
    raise ValueError(
        f'toolbox {subject.name} is wired to the wrong payloads: {wrong_names}',
    )


class Toolbox:
    """Participant that answers requests: one tool per label, dispatched.

    The fourth kind of participant, beside ``Agent`` (a model authors),
    ``Human`` (a person authors) and ``Machine`` (a function of the whole
    history computes). A toolbox is a function of the *request*: it keeps
    nothing between requests and never reads the conversation. That is what
    lets a tool be tested in one line, and what lets a resumed session skip the
    effect instead of repeating it.
    """

    def __init__(
        self,
        role: Role,
        proto: SessionType,
        tools: Iterable[Tool[Any]],
        declares: EndpointType | None = None,
    ) -> None:
        """Bind *role* to *proto* and answer its requests with *tools*.

        Args:
            role: The role this toolbox plays. Its projection must be a
                service: never speaks first, answers every request it accepts
                right away, to the role that asked.
            proto: The choreography; projected locally on construction.
            tools: Exactly one tool per request the projection declares.
            declares: The endpoint type this participant claims to follow. It must
                be a subtype of the projection of *proto* on *role*: it
                may accept more labels than the choreography sends it, and send
                fewer than the choreography allows. Defaults to the projection
                itself.

        Raises:
            ValueError: if the projection is not a service, if the tools do not
                cover its requests exactly, or if a tool was written against a
                different payload codec than the protocol declares.
            ConformanceError: if *declares* is not a subtype of the projection.
        """
        self.role = role
        self.endpoint_contract: EndpointType = associate(declares, proto, role)
        self._tools = _match_tools(_requests(self.endpoint_contract), tools, role)
        self._awaiting: _Awaiting = _IDLE

    @classmethod
    def at(
        cls,
        role: Role,
        endpoint: EndpointType,
        tools: Iterable[Tool[Any]],
    ) -> Toolbox:
        """Bind *role* under a ready *endpoint* (cast entry).

        Args:
            role: The role this toolbox plays.
            endpoint: The projected endpoint for *role* (must be a service).
            tools: Exactly one tool per request the endpoint declares.
        """
        box = object.__new__(cls)
        box.role = role
        box.endpoint_contract = endpoint
        box._tools = _match_tools(_requests(endpoint), tools, role)
        box._awaiting = _IDLE
        return box

    async def select(
        self,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Answer the outstanding request and go back to waiting.

        Args:
            receiver: The role that asked; it receives the answer.
            branches: The replies the protocol offers for this request.

        Returns:
            The chosen reply together with its decoded payload.

        Raises:
            SelectionError: if the tool names a reply that is not on offer.
        """
        offered = branches
        # take the request off the slot, so one request is answered once:
        pending = _outstanding(self._awaiting, self.role)
        self._awaiting = _IDLE
        # run the tool under its own span:
        answer = await self._answered(pending)
        # decode at the boundary, so `decode(raw) == payload` holds by construction:
        branch = chosen_branch(offered, answer.label)
        post(expr=self._awaiting == _IDLE, message='a toolbox must owe nothing after answering')
        return Chosen(
            branch=branch,
            payload=branch.payload.decode(answer.payload),
            raw=answer.payload,
        )

    async def offer(self, envelope: Envelope) -> None:
        """Take *envelope* as the request to answer next.

        Args:
            envelope: The protocol message being delivered.
        """
        role_name = self.role.name
        label = envelope.label
        pre(
            expr=self._awaiting == _IDLE,
            message=f'{role_name} was given {label} with an answer still owed',
        )
        self._awaiting = _Pending(envelope.label, envelope.payload)

    async def recall(self, envelope: Envelope) -> None:
        """Drop the request *envelope* answered; the tool is not run again.

        A replayed session takes the answer from the journal, so the effect
        that produced it happens exactly once — in the run that recorded it.

        Args:
            envelope: The answer this toolbox sent earlier.
        """
        self._awaiting = _IDLE

    async def cancel(self, notice: Cancelled) -> None:
        """Drop the request nobody will answer now.

        A toolbox holds no resources of its own — a tool that owns a connection
        owns it outside the protocol — so the whole of its state is the request
        in its slot, and ``Tool`` has no ``cancel`` to call.

        Args:
            notice: Why the session was rolled up.
        """
        self._awaiting = _IDLE
        post(expr=self._awaiting == _IDLE, message='a cancelled toolbox must owe nothing')

    async def _answered(self, pending: _Pending) -> Choice:
        """Run the tool for *pending*, recording a span around the effect.

        Args:
            pending: The request to answer.

        Returns:
            The tool's alt among the reply branches.
        """
        with current().child().open(ToolCalled(pending.label)) as call:
            answer = await self._tools[pending.label].answer(pending.payload)
            call.record(ToolAnswered(answer.label))
            return answer


def _bind_service(
    tools: tuple[Tool[Any], ...],
    role: Role,
    endpoint: EndpointType,
) -> Participant:
    return Toolbox.at(role, endpoint, tools)


def service(
    *tools: Tool[Any],
) -> Callable[[Role, EndpointType], Participant]:
    """Casting factory: bind *tools* when a service role is played.

    Returns a ``(role, endpoint) -> Toolbox`` for :meth:`~agentsparty.runtime.Cast.play`.

    Args:
        *tools: Exactly one tool per request the role's endpoint declares.
    """
    return partial(_bind_service, tools)


__all__ = ['Tool', 'Toolbox', 'reply', 'service', 'tool', 'tool_for']
