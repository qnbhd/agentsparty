"""Static termination: whether a session protocol may or must reach ``end``."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from typing_extensions import assert_never

from agentsparty.protocol.session._wellformed import assert_wellformed
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


def may_terminate(node: SessionType) -> bool:
    """Whether some finite path of *node* reaches ``end``.

    Walks the closed type treating each bound recursion variable as a
    back-edge (a cycle). Equivalent to reachability of ``end`` on the finite
    state graph of a well-formed session protocol.

    Args:
        node: A closed, guarded session protocol.

    Returns:
        ``True`` if at least one path ends; ``False`` for a pure loop with no
        exit (a daemon protocol).

    Raises:
        ValueError: if *node* is open or unguarded.
    """
    assert_wellformed(node)
    return _may_end(node)


def must_terminate(node: SessionType) -> bool:
    """Whether every path of *node* reaches ``end`` in finitely many steps.

    Dual of :func:`may_terminate`: ``True`` only when there is no cycle and no
    path that fails to reach ``end``. A recursive protocol with an exit branch
    may terminate without being obliged to.

    Args:
        node: A closed, guarded session protocol.

    Returns:
        ``True`` if every path ends; ``False`` if some path loops or cannot
        finish.

    Raises:
        ValueError: if *node* is open or unguarded.
    """
    assert_wellformed(node)
    return _must_end(node)


def _may_end(node: SessionType) -> bool:
    """Whether *node* has a path to ``end`` (vars are non-terminating edges)."""
    return _ends(node, any)


def _must_end(node: SessionType) -> bool:
    """Whether every path of *node* reaches ``end`` (vars are loops)."""
    return _ends(node, all)


def _ends(node: SessionType, over_branches: Callable[[Iterable[bool]], bool]) -> bool:
    """Termination walk; *over_branches* quantifies a prefix's branches."""
    match node:
        case SessionEnd():
            return True
        case SessionVar():
            return False
        case SessionRec(body=body):
            return _ends(body, over_branches)
        case (
            Interaction(branches=branches) | SendTo(branches=branches) | RecvFrom(branches=branches)
        ):
            return over_branches(
                _ends(branch.continuation, over_branches) for branch in branches.values()
            )
        case Parallel(branches=branches):
            # Parallel ends only when every branch ends — in both flavours.
            return all(_ends(branch, over_branches) for branch in branches)
        case _:  # pragma: no cover
            assert_never(node)
