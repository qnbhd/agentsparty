"""Computed participant: a alt that is a function of what has been seen."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Protocol, TypeAlias, TypeVar

from typing_extensions import Unpack

from agentsparty._utils.assertions import post
from agentsparty.kernel.nonempty import NonEmptyMap, ne_tuple
from agentsparty.kernel.role import Role
from agentsparty.participant import (
    Cancelled,
    Choice,
    Envelope,
    Participant,
    chosen_branch,
)
from agentsparty.protocol import EndpointType, SessionType, associate
from agentsparty.protocol.language.core import BranchCodec, Chosen, Label

B = TypeVar('B', bound=BranchCodec)
# Inline Unpack form: the subscripted string alias ``NonEmptyTuple[Label]``
# cannot be resolved by ``typing.get_type_hints`` on Python 3.10.
_OfferedLabels: TypeAlias = tuple[Label, Unpack[tuple[Label, ...]]]


@dataclass(frozen=True, slots=True)
class View:
    """Everything a machine is allowed to base a alt on.

    Deliberately not the machine itself: ``decide`` takes a view and returns a
    alt, so it is a pure function that a test calls in one line, without a
    session, a runtime or an event loop.
    """

    seen: tuple[Envelope, ...]
    receiver: Role
    offered: _OfferedLabels


class Decide(Protocol):
    """How a machine picks: from what it has seen and what is on offer."""

    def __call__(self, view: View, /) -> Choice:
        """Return a label and raw payload for *view*."""
        ...


class Machine:
    """Participant whose alts are computed rather than authored.

    The third kind of participant, beside ``Agent`` (a model authors) and
    ``Human`` (a person authors). Its memory is the messages it has taken part
    in, in order — messages it received and messages it sent, so that a live
    run and a replayed run leave it in the same state.
    """

    def __init__(
        self,
        role: Role,
        proto: SessionType,
        decide: Decide,
        declares: EndpointType | None = None,
    ) -> None:
        """Bind *role* to *proto* and drive it with *decide*.

        Args:
            role: The role this machine plays.
            proto: The choreography; projected locally on construction.
            decide: The pure function that picks a branch and its raw payload.
            declares: An optional endpoint contract; defaults to the projection.

        Raises:
            ConformanceError: if *declares* is not a subtype of the projection.
        """
        self.role = role
        self.endpoint_contract: EndpointType = associate(declares, proto, role)
        self._decide = decide
        self._seen: list[Envelope] = []

    @classmethod
    def at(cls, role: Role, endpoint: EndpointType, decide: Decide) -> Machine:
        """Bind *role* under a ready *endpoint* (cast entry).

        Args:
            role: The role this machine plays.
            endpoint: The projected endpoint for *role*.
            decide: The pure function that picks a branch and its raw payload.
        """
        machine = object.__new__(cls)
        machine.role = role
        machine.endpoint_contract = endpoint
        machine._decide = decide
        machine._seen = []
        return machine

    @property
    def seen(self) -> tuple[Envelope, ...]:
        """The messages this machine took part in, in order."""
        return tuple(self._seen)

    async def select(
        self,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Compute a alt and remember it as a message this machine sent.

        Args:
            receiver: The role that will receive the chosen message.
            branches: The labelled alts offered here.

        Returns:
            The chosen branch together with its decoded payload.

        Raises:
            SelectionError: if ``decide`` names a label that is not on offer.
        """
        offered = branches
        # ask the decision function:
        labels = ne_tuple(*sorted(offered))
        alt = self._decide(View(self.seen, receiver, labels))
        # decode at the boundary, so `decode(raw) == payload` holds by construction:
        branch = chosen_branch(offered, alt.label)
        payload = branch.payload.decode(alt.payload)
        # remember what we sent, exactly as `recall` would on replay:
        self._seen.append(Envelope(self.role, receiver, alt.label, payload))
        return Chosen(branch=branch, payload=payload, raw=alt.payload)

    async def offer(self, envelope: Envelope) -> None:
        """Remember *envelope* as a message this machine received.

        Args:
            envelope: The protocol message being delivered.
        """
        self._seen.append(envelope)

    async def recall(self, envelope: Envelope) -> None:
        """Remember *envelope* as a message this machine sent earlier.

        Args:
            envelope: The protocol message this machine sent earlier.
        """
        self._seen.append(envelope)

    async def cancel(self, notice: Cancelled) -> None:
        """Forget the session: a cancelled machine has seen nothing.

        Args:
            notice: Why the session was rolled up.
        """
        self._seen.clear()
        post(expr=not self.seen, message='a cancelled machine must remember nothing')


def _bind_machine(decide: Decide, role: Role, endpoint: EndpointType) -> Participant:
    return Machine.at(role, endpoint, decide)


def machine(decide: Decide) -> Callable[[Role, EndpointType], Participant]:
    """Casting factory: bind *decide* when a role is played.

    Returns a ``(role, endpoint) -> Machine`` for :meth:`~agentsparty.runtime.Cast.play`.

    Args:
        decide: The pure function that picks a branch and its raw payload.
    """
    return partial(_bind_machine, decide)


__all__ = ['Decide', 'Machine', 'View', 'machine']
