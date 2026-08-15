"""Human-driven participants and the IO seams that drive them."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any, Final, Protocol, TypeVar, cast

from agentsparty.kernel.console import Console, StreamConsole
from agentsparty.kernel.errors import PayloadError, SelectionError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.participant import (
    Cancelled,
    Choice,
    Envelope,
    Participant,
    chosen_branch,
)
from agentsparty.protocol import EndpointType, SessionType, associate
from agentsparty.protocol.language.core import (
    BranchCodec,
    Chosen,
    Label,
    RawValue,
)

B = TypeVar('B', bound=BranchCodec)


class HumanIo(Protocol):
    """IO seam for a human participant: how alts and messages are shown."""

    async def choose(
        self,
        subject: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Let the human pick one of *branches* to send to *receiver*.

        Args:
            subject: The human's own role.
            receiver: The role that will receive the chosen message.
            branches: The labelled alts offered to the human; never empty
                — a protocol interaction always declares at least one branch.

        Returns:
            The chosen branch together with its decoded payload.
        """
        ...

    async def notify(self, subject: Role, envelope: Envelope) -> None:
        """Present *envelope* to the human playing *subject*.

        Args:
            subject: The human's own role.
            envelope: The protocol message being delivered.
        """
        ...

    async def recall(self, subject: Role, envelope: Envelope) -> None:
        """Remind the human playing *subject* of a message they sent earlier.

        Args:
            subject: The human's own role.
            envelope: The protocol message they sent earlier.
        """
        ...

    async def cancel(self, subject: Role, notice: Cancelled) -> None:
        """Tell the human playing *subject* that the session is over.

        Args:
            subject: The human's own role.
            notice: Why the session was rolled up.
        """
        ...


_MENU_HINT: Final = 'Enter label (or number), then payload if required.'


def _entry(position: int, branch: BranchCodec) -> list[str]:
    """One menu line, plus an intent line when the branch states one."""
    payload_name = branch.payload.name
    lines = [f'  {position}. {branch.label}  (payload: {payload_name})']
    if branch.intent:
        lines.append(f'       {branch.intent}')
    return lines


@dataclass(frozen=True, slots=True)
class _Menu:
    """The branch alts offered to a human, in stable display order."""

    offered: NonEmptyMap[Label, BranchCodec]
    ordered: tuple[BranchCodec, ...]

    @classmethod
    def of(cls, branches: NonEmptyMap[Label, B]) -> _Menu:
        by_label = sorted(branches.values(), key=lambda branch: branch.label)
        return _Menu(cast(NonEmptyMap[Label, BranchCodec], branches), tuple(by_label))

    def render(self, who: str, receiver: Role) -> str:
        lines = [f'[{who}] select a message to send to {receiver.name}:']
        for position, branch in enumerate(self.ordered, start=1):
            lines.extend(_entry(position, branch))
        lines.append(_MENU_HINT)
        return '\n'.join(lines)

    def resolve(self, line: str) -> BranchCodec:
        raw = line.strip()
        if raw.isdigit():
            return self._at(int(raw))
        return chosen_branch(self.offered, Label(raw))

    def _at(self, position: int) -> BranchCodec:
        if 1 <= position <= len(self.ordered):
            return self.ordered[position - 1]
        raise SelectionError(f'alt {position} out of range 1..{len(self.ordered)}')

    def _names(self) -> str:
        return ', '.join(str(branch.label) for branch in self.ordered)


def _payload_prompt(branch: BranchCodec) -> str | None:
    if not branch.payload.carries_value:
        return None
    payload_name = branch.payload.name
    return f'> payload ({payload_name}): '


def _chosen_of(branch: B, raw: RawValue) -> Chosen[B]:
    return Chosen(branch=branch, payload=branch.payload.decode(raw), raw=raw)


def _render_envelope(who: str, envelope: Envelope) -> str:
    sender = envelope.sender.name
    header = f'[{who}] received {envelope.label} from {sender}'
    if envelope.payload is None:
        return header
    body = str(envelope.payload).splitlines() or ['']
    return '\n'.join([header, *(f'  {line}' for line in body)])


def _render_sent(who: str, envelope: Envelope) -> str:
    receiver = envelope.receiver.name
    header = f'[{who}] sent {envelope.label} to {receiver}'
    if envelope.payload is None:
        return header
    body = str(envelope.payload).splitlines() or ['']
    return '\n'.join([header, *(f'  {line}' for line in body)])


class CliHumanIo:
    """Interactive Human IO over a Console; role is an argument, not state."""

    def __init__(self, console: Console | None = None) -> None:
        """Create an interactive IO over *console* (defaults to process stdio).

        Args:
            console: The console to prompt on; ``StreamConsole`` when omitted.
        """
        self._console: Console = StreamConsole() if console is None else console

    async def choose(
        self,
        subject: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Prompt the human for a branch and payload over the console.

        Args:
            subject: The human's own role.
            receiver: The role that will receive the chosen message.
            branches: The labelled alts offered to the human.

        Returns:
            The chosen branch together with its decoded payload.
        """
        menu = _Menu.of(branches)
        self._console.show(menu.render(subject.name, receiver))
        while True:
            chosen, error = await self._attempt_or_error(menu)
            if chosen is not None:
                return chosen
            self._console.show(f'error: {error}')

    async def notify(self, subject: Role, envelope: Envelope) -> None:
        """Print *envelope* to the console.

        Args:
            subject: The human's own role.
            envelope: The protocol message being delivered.
        """
        self._console.show(_render_envelope(subject.name, envelope))

    async def recall(self, subject: Role, envelope: Envelope) -> None:
        """Print a message this human sent in an earlier process.

        Args:
            subject: The human's own role.
            envelope: The protocol message they sent earlier.
        """
        self._console.show(_render_sent(subject.name, envelope))

    async def cancel(self, subject: Role, notice: Cancelled) -> None:
        """Print that the session ended, and why.

        Args:
            subject: The human's own role.
            notice: Why the session was rolled up.
        """
        self._console.show(f'[{subject.name}] session ended: {notice.reason}')

    async def _attempt_or_error(
        self,
        menu: _Menu,
    ) -> tuple[Chosen[Any] | None, str | None]:
        try:
            return await self._attempt(menu), None
        except (SelectionError, PayloadError) as exc:
            return None, str(exc)

    async def _attempt(self, menu: _Menu) -> Chosen[Any]:
        branch = menu.resolve(await self._console.ask('> label: '))
        prompt = _payload_prompt(branch)
        raw: RawValue = None if prompt is None else await self._console.ask(prompt)
        return _chosen_of(branch, raw)


class ScriptedHumanIo:
    """Predetermined alts for tests and non-interactive demos."""

    def __init__(self, alts: Sequence[Choice]) -> None:
        """Preload *alts*, consumed in order.

        Args:
            alts: The scripted alts to return one at a time.
        """
        self._alts = list(alts)
        self.notifications: list[Envelope] = []
        self.recollections: list[Envelope] = []
        self.cancellations: list[Cancelled] = []

    async def choose(
        self,
        subject: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Return the next scripted alt, or raise when exhausted.

        Args:
            subject: The human's own role.
            receiver: The role that will receive the chosen message.
            branches: The labelled alts offered to the human.

        Returns:
            The scripted alt decoded against the offered branches.
        """
        offered = branches
        if not self._alts:
            labels = ', '.join(str(b.label) for b in offered.values())
            raise SelectionError(
                f'ScriptedHumanIo exhausted; still need a alt for '
                f'{receiver.name} (offered: {labels})',
            )
        alt = self._alts.pop(0)
        branch = chosen_branch(offered, alt.label)
        return Chosen(
            branch=branch,
            payload=branch.payload.decode(alt.payload),
            raw=alt.payload,
        )

    async def notify(self, subject: Role, envelope: Envelope) -> None:
        """Append *envelope* to the ``notifications`` list.

        Args:
            subject: The human's own role.
            envelope: The protocol message being delivered.
        """
        self.notifications.append(envelope)

    async def recall(self, subject: Role, envelope: Envelope) -> None:
        """Append *envelope* to the ``recollections`` list.

        Args:
            subject: The human's own role.
            envelope: The protocol message they sent earlier.
        """
        self.recollections.append(envelope)

    async def cancel(self, subject: Role, notice: Cancelled) -> None:
        """Append *notice* to the ``cancellations`` list.

        Args:
            subject: The human's own role.
            notice: Why the session was rolled up.
        """
        self.cancellations.append(notice)


class Human:
    """Peer participant driven by HumanIo (CLI or scripted)."""

    def __init__(
        self,
        role: Role,
        proto: SessionType,
        io: HumanIo,
        declares: EndpointType | None = None,
    ) -> None:
        """Bind *role* to *proto* and drive it through *io*.

        Args:
            role: The role this human plays in the protocol.
            proto: The choreography; projected locally on construction.
            io: Where alts and messages are presented to the human.
            declares: An optional endpoint contract; defaults to the projection.

        Raises:
            ConformanceError: if *declares* is not a subtype of the projection.
        """
        self.role = role
        self.endpoint_contract: EndpointType = associate(declares, proto, role)
        self._io = io

    @classmethod
    def at(cls, role: Role, endpoint: EndpointType, io: HumanIo) -> Human:
        """Bind *role* under a ready *endpoint* (cast entry).

        Args:
            role: The role this human plays.
            endpoint: The projected endpoint for *role*.
            io: Where alts and messages are presented.
        """
        human = object.__new__(cls)
        human.role = role
        human.endpoint_contract = endpoint
        human._io = io
        return human

    async def select(
        self,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Delegate the alt to the underlying :class:`HumanIo`.

        Args:
            receiver: The role that will receive the chosen message.
            branches: The labelled alts offered to the human.

        Returns:
            The chosen branch together with its decoded payload.
        """
        return await self._io.choose(self.role, receiver, branches)

    async def offer(self, envelope: Envelope) -> None:
        """Delegate the notification to the underlying :class:`HumanIo`.

        Args:
            envelope: The protocol message being delivered.
        """
        await self._io.notify(self.role, envelope)

    async def recall(self, envelope: Envelope) -> None:
        """Delegate the reminder to the underlying :class:`HumanIo`.

        Args:
            envelope: The protocol message this human sent earlier.
        """
        await self._io.recall(self.role, envelope)

    async def cancel(self, notice: Cancelled) -> None:
        """Delegate the notice to the underlying :class:`HumanIo`.

        Args:
            notice: Why the session was rolled up.
        """
        await self._io.cancel(self.role, notice)


def script(*answers: Choice) -> ScriptedHumanIo:
    """A scripted IO seam from ordered :class:`~agentsparty.participant.Choice` values.

    Args:
        *answers: Choices the human will make, in order.
    """
    return ScriptedHumanIo(list(answers))


def _bind_human(io: HumanIo, role: Role, endpoint: EndpointType) -> Participant:
    return Human.at(role, endpoint, io)


def human(io: HumanIo) -> Callable[[Role, EndpointType], Participant]:
    """Casting factory: bind *io* when a role is played.

    Returns a ``(role, endpoint) -> Human`` for :meth:`~agentsparty.runtime.Cast.play`.

    Args:
        io: Where alts and messages are presented to the human.
    """
    return partial(_bind_human, io)


__all__ = [
    'CliHumanIo',
    'Human',
    'HumanIo',
    'ScriptedHumanIo',
    'human',
    'script',
]
