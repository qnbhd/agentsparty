"""Participant enumeration for the global session protocol carrier."""

from __future__ import annotations

from collections.abc import Iterator

from typing_extensions import assert_never

from agentsparty.kernel.role import Role
from agentsparty.protocol.session.types import (
    Interaction,
    Parallel,
    RecvFrom,
    SendTo,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
)

__all__ = ['participants']


def _walk(node: SessionType) -> Iterator[Interaction | SendTo | RecvFrom]:
    """Pre-order traversal, yielding every global prefix node."""
    stack = [node]
    while stack:
        current = stack.pop()
        yielded = _expand(current, stack)
        if yielded is not None:
            yield yielded


def _expand(
    current: SessionType,
    stack: list[SessionType],
) -> Interaction | SendTo | RecvFrom | None:
    """Push children of *current* onto *stack*; return a prefix if any."""
    match current:
        case SessionEnd() | SessionVar():
            return None
        case SessionRec(body=body):
            stack.append(body)
            return None
        case Parallel(branches=branches):
            stack.extend(reversed(branches))
            return None
        case (
            Interaction(branches=branches) | SendTo(branches=branches) | RecvFrom(branches=branches)
        ):
            continuations = (branch.continuation for branch in reversed(list(branches.values())))
            stack.extend(continuations)
            return current
        case _:  # pragma: no cover
            assert_never(current)


def participants(node: SessionType) -> list[Role]:
    """Every role mentioned by the protocol, in order of first appearance."""
    roles = (role for prefix in _walk(node) for role in (prefix.sender, prefix.receiver))
    return list(dict.fromkeys(roles))
