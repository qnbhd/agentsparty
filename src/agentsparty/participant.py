"""The participant contract: every executor bound to a role."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from typing_extensions import assert_never

from agentsparty.kernel.errors import SelectionError, fault
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import BranchCodec, Case, Chosen, Label, RawValue, _as_label
from agentsparty.protocol.language.endpoint import EndpointType

B = TypeVar('B', bound=BranchCodec)


def chosen_branch(offered: NonEmptyMap[Label, B], label: Label) -> B:
    """Return *label*'s branch, or report one uniform selection failure."""
    try:
        return offered[label]
    except KeyError:
        names = ', '.join(str(branch.label) for branch in offered.values())
        raise SelectionError(f'chosen label {label} not on offer: {names}') from None


@dataclass(frozen=True, slots=True)
class Choice:
    """Scripted intent: label plus still-raw payload (decoded at the boundary)."""

    label: Label
    payload: RawValue = None


def says(message: str | Label | Case[object], payload: RawValue = None) -> Choice:
    """A scripted or machine alt named by *message*.

    Accepts a :class:`~agentsparty.protocol.language.core.Case` so a declared message is
    reused without restating its label string. ``Case.__call__`` is not used
    for this — :class:`Choice` lives here, :class:`Case` in the protocol.

    Args:
        message: A branch label or a declared :class:`Case`.
        payload: The still-raw payload for the alt.

    Returns:
        A :class:`Choice` ready for a script or :class:`~agentsparty.machine.Machine`.
    """
    match message:
        case Case() as declared:
            return Choice(declared.label, payload)
        case Label() as label:
            return Choice(label, payload)
        case str() as text:
            return Choice(_as_label(text), payload)
        case _:
            assert_never(message)


@dataclass(frozen=True, slots=True)
class Envelope:
    """A delivered protocol message from sender to receiver."""

    sender: Role
    receiver: Role
    label: Label
    payload: object = None


@dataclass(frozen=True, slots=True)
class Cancelled:
    """Why a session was rolled up before it reached ``end``.

    Carries the failure as it was written down, not the live exception: a
    participant cannot inspect an exception (its class is not a value this
    project reads), so the only thing it could do with one is print it.
    The caller of :meth:`~agentsparty.runtime.AgentRuntime.run` still receives the
    exception itself — a cancellation notifies, it does not swallow.
    """

    reason: str

    @classmethod
    def of(cls, error: Exception) -> Cancelled:
        """The notice for a session that ended in *error*.

        This is the boundary where an unknown exception becomes a domain value;
        everything downstream — participants, signals, sinks — receives a
        notice that needs no further inspection.

        Args:
            error: The failure that ended the session.

        Returns:
            The notice to broadcast to every participant.
        """
        return cls(fault(error))


class Participant(Protocol):
    """Executor bound to a protocol role: Agent or Human."""

    @property
    def role(self) -> Role:
        """The role this participant plays."""
        ...

    @property
    def endpoint_contract(self) -> EndpointType:
        """The endpoint protocol derived for this participant's role."""
        ...

    async def select(
        self,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Pick one of *branches* and return the decoded alt for *receiver*.

        Args:
            receiver: The role that will receive the chosen message.
            branches: The labelled alts offered to this participant; never
                empty — a protocol interaction always declares at least one
                branch, so the guarantee lives in the type.

        Returns:
            The chosen branch together with its decoded payload.
        """
        ...

    async def offer(self, envelope: Envelope) -> None:
        """Deliver *envelope* to this participant.

        Args:
            envelope: The protocol message being delivered.
        """
        ...

    async def recall(self, envelope: Envelope) -> None:
        """Restore *envelope* as a message this participant sent earlier.

        The dual of :meth:`offer`, called when a session resumes from a
        journal: the alt was authored by an earlier process and must not be
        authored again. Implementations restore what the participant knows, in
        the form the runtime informs it of — not the original wording.

        Args:
            envelope: The protocol message this participant sent earlier.
        """
        ...

    async def cancel(self, notice: Cancelled) -> None:
        """Take note that the session is over and will not go on here.

        Called once on every bound participant when a session ends anywhere
        other than ``end``. Nothing will be asked of this participant again in
        this session, so this is where it releases what it holds and returns to
        the state it was constructed in — which makes cancelling twice the same
        as cancelling once, and a cancelled participant reusable.

        It must not raise. The failure that rolled the session up is the one
        the caller has to see; a participant that raises here is recorded as
        failed and the broadcast goes on without it.

        Args:
            notice: Why the session was rolled up.
        """
        ...


__all__ = [
    'Cancelled',
    'Choice',
    'Envelope',
    'Participant',
    'says',
]
