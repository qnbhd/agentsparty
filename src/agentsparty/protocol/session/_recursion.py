"""Guarded μ-recursion over the session protocol carrier."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

from typing_extensions import assert_never

from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.protocol.language.core import Label, branches_map
from agentsparty.protocol.session.types import (
    Interaction,
    Parallel,
    RecvFrom,
    SendTo,
    SessionBranchCase,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
)


def free_vars(node: SessionType) -> frozenset[str]:
    """Names of free recursion variables in *node*.

    Args:
        node: A session protocol tree (possibly open).

    Returns:
        The set of recursion-variable names not bound by an enclosing ``μ``.
    """
    match node:
        case SessionEnd() | Parallel():
            # Parallel branches are closed by construction (see ``_parallel``).
            return frozenset()
        case SessionVar(name=name):
            return frozenset((name,))
        case (
            Interaction(branches=branches) | SendTo(branches=branches) | RecvFrom(branches=branches)
        ):
            return frozenset().union(
                *(free_vars(branch.continuation) for branch in branches.values()),
            )
        case SessionRec(name=name, body=body):
            return free_vars(body) - {name}
        case _:  # pragma: no cover
            assert_never(node)


def _is_guarded(name: str, node: SessionType) -> bool:
    """Whether every free occurrence of *name* in *node* sits under a prefix."""
    match node:
        case SessionEnd() | Interaction() | SendTo() | RecvFrom() | Parallel():
            # A free var cannot cross into a parallel branch (closed by
            # construction), so every occurrence of *name* is guarded.
            return True
        case SessionVar(name=var_name):
            return var_name != name
        case SessionRec(name=binder, body=body):
            return True if binder == name else _is_guarded(name, body)
        case _:  # pragma: no cover
            assert_never(node)


def _subst(node: SessionType, name: str, replacement: SessionType) -> SessionType:
    """Substitute *replacement* for free occurrences of *name* (shadowing-aware)."""
    atomic = _subst_atomic(node, name, replacement)
    if atomic is not None:
        return atomic
    match node:
        case Interaction() | SendTo() | RecvFrom():
            return replace(
                node,
                branches=_map_branches(
                    node.branches,
                    lambda cont: _subst(cont, name, replacement),
                ),
            )
        case SessionRec(name=binder, body=body):
            return _subst_rec(node, binder, body, name, replacement)
        case Parallel():
            # Branches are closed — nothing free to substitute.
            return node
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session node: {node!r}')


def _subst_atomic(
    node: SessionType,
    name: str,
    replacement: SessionType,
) -> SessionType | None:
    match node:
        case SessionEnd():
            return node
        case SessionVar(name=var_name):
            return replacement if var_name == name else node
        case _:
            return None


def _subst_rec(
    node: SessionRec,
    binder: str,
    body: SessionType,
    name: str,
    replacement: SessionType,
) -> SessionType:
    if binder == name:
        return node
    return SessionRec(binder, _subst(body, name, replacement))


def _map_branches(
    branches: Mapping[Label, SessionBranchCase],
    transform: Callable[[SessionType], SessionType],
) -> NonEmptyMap[Label, SessionBranchCase]:
    """Rebuild *branches* with *transform* applied to every continuation."""
    return branches_map(
        replace(branch, continuation=transform(branch.continuation)) for branch in branches.values()
    )


def unfold(node: SessionType) -> SessionType:
    """Unfold one recursion step, replacing the binder with the recursion itself.

    No-op unless *node* is a ``Rec``. Requires a closed argument: the runtime
    root is checked by :func:`assert_wellformed`, and each unfold preserves
    closedness. Open terms are not capture-avoiding; do not call ``unfold`` on
    open protocols.

    Args:
        node: A closed session protocol.

    Returns:
        The body of *node* with free occurrences of the binder replaced by
        *node* itself, or *node* unchanged when it is not a ``Rec``.
    """
    match node:
        case SessionRec(name=name, body=body):
            return _subst(body, name, node)
        case _:
            return node
