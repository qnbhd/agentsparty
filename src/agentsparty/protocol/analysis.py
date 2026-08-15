"""Static analysis of projected endpoint protocols and their duties."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from typing_extensions import assert_never

from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Label
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointBranchCase,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    EndpointVar,
)

__all__ = [
    'Duty',
    'duties',
]


@dataclass(frozen=True, slots=True)
class Duty:
    """One message a role is charged with authoring: to whom, what, and why.

    The industry's ``Task`` record, derived rather than authored: agentsparty writes
    the choreography and reads the task list off it, instead of writing the
    task list and inferring the choreography. ``payload`` is the codec *name*,
    the same identity a :class:`~agentsparty.journal.types.Decision` records.
    """

    receiver: Role
    label: Label
    payload: str
    intent: str


def duties(node: EndpointType) -> tuple[Duty, ...]:
    """Everything *node* may be asked to author, in order of first appearance.

    Reads only the internal alts (:class:`~agentsparty.protocol.language.endpoint.EndpointSelect`):
    what the role receives is not a duty. Repeats are collapsed, so a message
    a recursive protocol asks for on every turn is listed once.

    Args:
        node: A projected endpoint protocol, e.g. ``project(proto, Architect)``.

    Returns:
        One entry per distinct message this role authors.
    """
    return tuple(dict.fromkeys(_duties(node)))


def _duties(node: EndpointType) -> Iterator[Duty]:
    """Every duty reachable from *node*, in pre-order, repeats included."""
    match node:
        case EndpointEnd() | EndpointVar():
            return
        case EndpointRec(body=body):
            yield from _duties(body)
        case EndpointBranch(branches=branches):
            yield from _branch_duties(branches)
        case EndpointSelect(receiver=receiver, branches=branches):
            yield from _select_duties(receiver, branches)
        case _:  # pragma: no cover
            assert_never(node)


def _branch_duties(branches: Mapping[Label, EndpointBranchCase]) -> Iterator[Duty]:
    for branch in branches.values():
        yield from _duties(branch.continuation)


def _select_duties(
    receiver: Role,
    branches: Mapping[Label, EndpointBranchCase],
) -> Iterator[Duty]:
    for branch in branches.values():
        yield Duty(receiver, branch.label, branch.payload.name, branch.intent)
        yield from _duties(branch.continuation)
