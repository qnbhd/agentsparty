"""What a participant remembers of a session, and what a model is shown of it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agentsparty._utils.assertions import require_positive
from agentsparty.kernel.role import Role
from agentsparty.llm.types import Message
from agentsparty.participant import Envelope


class Brief(Protocol):
    """A participant's memory of a session: a fold over the envelopes it saw.

    ``remember`` is the state transition and ``messages`` its state-only
    observation. Both must be pure functions of the envelopes folded in. An
    implementation that reads anything else — a clock, a model, the wording a
    model happened to use — makes a resumed session show its model a different
    conversation than the recording session did, and the guarantee that a
    resumed session is faithful no longer holds.

    A brief is persistent: ``remember`` returns a new brief and never mutates.
    """

    def remember(self, envelope: Envelope) -> Brief:
        """The brief that has also taken part in *envelope*.

        Args:
            envelope: A message this participant sent or received.
        """
        ...

    def messages(self) -> tuple[Message, ...]:
        """The conversation to send a model, oldest first."""
        ...


def line(subject: Role, envelope: Envelope) -> Message:
    """Render *envelope* from *subject*'s side of the exchange.

    A message this participant sent is rendered as ``assistant``; anything else
    as ``user``. The rendering is the same on a live run and on a replay — that
    equality is what makes a resumed session faithful.

    Args:
        subject: The role whose side is being rendered.
        envelope: The message to render.
    """
    payload = '' if envelope.payload is None else f' payload={envelope.payload!r}'
    sender = envelope.sender.name
    receiver = envelope.receiver.name
    if envelope.sender == subject:
        return Message(
            role='assistant',
            content=f'Sent {envelope.label} to {receiver}.{payload}',
        )
    return Message(
        role='user',
        content=(f'Received {envelope.label} from {sender} to {receiver}.{payload}'),
    )


@dataclass(frozen=True, slots=True)
class Transcript:
    """Brief that remembers every envelope; the default."""

    subject: Role
    turns: tuple[Envelope, ...] = ()

    def remember(self, envelope: Envelope) -> Brief:
        """The transcript with *envelope* appended.

        Args:
            envelope: A message this participant sent or received.
        """
        return Transcript(self.subject, (*self.turns, envelope))

    def messages(self) -> tuple[Message, ...]:
        """Every remembered envelope, rendered oldest first."""
        return tuple(line(self.subject, envelope) for envelope in self.turns)


@dataclass(frozen=True, slots=True)
class Recent:
    """Brief that keeps only the last :attr:`keep` envelopes.

    The bounded-context policy: what the industry spends a summarisation
    middleware on, without the model call that makes replay diverge. To keep
    information from before the window, send it through the protocol — see
    the ``Scribe`` pattern in the documentation's agent-system guide.
    """

    subject: Role
    keep: int
    turns: tuple[Envelope, ...] = ()

    def __post_init__(self) -> None:
        """Reject a window that cannot hold a turn.

        Raises:
            ValueError: if :attr:`keep` is below one.
        """
        require_positive('a brief window', self.keep)

    def remember(self, envelope: Envelope) -> Brief:
        """The brief with *envelope* appended and the window re-applied.

        Args:
            envelope: A message this participant sent or received.
        """
        kept = (*self.turns, envelope)[-self.keep :]
        return Recent(self.subject, self.keep, kept)

    def messages(self) -> tuple[Message, ...]:
        """The envelopes still inside the window, rendered oldest first."""
        return tuple(line(self.subject, envelope) for envelope in self.turns)


__all__ = ['Brief', 'Recent', 'Transcript', 'line']
