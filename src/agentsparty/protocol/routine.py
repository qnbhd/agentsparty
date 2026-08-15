"""Role-parameterised choreographies: ``Routine`` and the ``do`` call."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Final, TypeAlias

from typing_extensions import Unpack, assert_never

from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Fragment, Label, branches_map
from agentsparty.protocol.session import free_vars, par, participants
from agentsparty.protocol.session.types import (
    Interaction,
    Parallel,
    RecvFrom,
    SendTo,
    SessionBranchCase,
    SessionEnd,
    SessionFragment,
    SessionRec,
    SessionType,
    SessionVar,
)

# Non-empty parameter list: at least one role.
_RoutineParams: TypeAlias = tuple[Role, Unpack[tuple[Role, ...]]]

_HOLE = '\x00hole'
"""Marker filling a routine's tail while its own roles are renamed.

No protocol can bind this name: ``rec`` binders come from user text, and the
name carries a NUL. See :func:`do` for why the marker is needed at all.
"""

__all__ = ['Routine', 'do']

_NAMES_SEPARATOR: Final = ', '


def _map_routine_branches(
    branches: Mapping[Label, SessionBranchCase],
    transform: Callable[[SessionType], SessionType],
) -> NonEmptyMap[Label, SessionBranchCase]:
    """Rebuild routine branches with *transform* on each continuation."""
    return branches_map(
        replace(branch, continuation=transform(branch.continuation)) for branch in branches.values()
    )


def _substitute(node: SessionType, name: str, replacement: SessionType) -> SessionType:
    """Substitute *replacement* for a free routine variable."""
    atomic = _substitute_atomic(node, name, replacement)
    if atomic is not None:
        return atomic
    match node:
        case Interaction() | SendTo() | RecvFrom():
            return replace(
                node,
                branches=_map_routine_branches(
                    node.branches,
                    lambda cont: _substitute(cont, name, replacement),
                ),
            )
        case SessionRec(name=binder, body=body):
            return _substitute_rec(node, binder, body, name, replacement)
        case Parallel():
            # Routine parallel branches are closed, so nothing is substituted.
            return node
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session node: {node!r}')


def _substitute_atomic(
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


def _substitute_rec(
    node: SessionRec,
    binder: str,
    body: SessionType,
    name: str,
    replacement: SessionType,
) -> SessionType:
    if binder == name:
        return node
    return SessionRec(binder, _substitute(body, name, replacement))


def _parallel_routine(branches: tuple[SessionType, ...]) -> SessionType:
    """Rebuild renamed branches through the public parallel constructor."""
    fragments = tuple(Fragment.halt(branch) for branch in branches)
    first, second, *rest = fragments
    return par(first, second, *rest).close()


def _check_role_usage(name: str, declared: set[Role], mentioned: set[Role]) -> None:
    hidden = sorted(role.name for role in mentioned - declared)
    if hidden:
        hidden_names = _NAMES_SEPARATOR.join(hidden)
        raise ValueError(
            f'routine {name!r} mentions roles that are not parameters: {hidden_names}',
        )
    unused = sorted(role.name for role in declared - mentioned)
    if unused:
        unused_names = _NAMES_SEPARATOR.join(unused)
        raise ValueError(f'routine {name!r} never uses: {unused_names}')


def _check_free_vars(name: str, skeleton: SessionType) -> None:
    loose = sorted(free_vars(skeleton) - {_HOLE})
    if loose:
        loose_names = _NAMES_SEPARATOR.join(loose)
        raise ValueError(
            f'routine {name!r} has free recursion variables: {loose_names}',
        )


def _rename(node: SessionType, binding: Mapping[Role, Role]) -> SessionType:
    """Replace every role in *node* according to *binding*.

    Recursion-variable names are left alone: they belong to the body, not to
    the roles. Roles missing from *binding* pass through unchanged.

    Args:
        node: The protocol to rewrite.
        binding: Formal-to-actual role mapping.

    Returns:
        The protocol with its roles rewritten.
    """
    match node:
        case SessionEnd() | SessionVar():
            return node
        case SessionRec(name=name, body=body):
            return SessionRec(name, _rename(body, binding))
        case Interaction() | SendTo() | RecvFrom():
            return replace(
                node,
                sender=binding.get(node.sender, node.sender),
                receiver=binding.get(node.receiver, node.receiver),
                branches=_map_routine_branches(
                    node.branches,
                    lambda cont: _rename(cont, binding),
                ),
            )
        case Parallel(branches=branches):
            # Rename changes sort keys; rebuild through the normaliser.
            return _parallel_routine(tuple(_rename(branch, binding) for branch in branches))
        case _:  # pragma: no cover
            assert_never(node)


@dataclass(frozen=True, slots=True)
class Routine:
    """A choreography written against formal roles, reusable under any binding.

    A routine declares its whole interface: every role its body mentions is a
    parameter, and its recursion is closed. Nothing leaks into the protocol
    that calls it except the roles the caller itself names.
    """

    name: str
    # Inline Unpack form: the subscripted string alias ``NonEmptyTuple[Role]``
    # cannot be resolved by ``typing.get_type_hints`` on Python 3.10.
    params: _RoutineParams
    body: SessionFragment

    def __post_init__(self) -> None:
        """Reject a routine whose interface does not match its body.

        Raises:
            ValueError: if a parameter repeats, if the body mentions a role
                that is not a parameter, if a parameter never appears, or if
                the body has a free recursion variable.
        """
        declared = set(self.params)
        if len(declared) != len(self.params):
            raise ValueError(f'routine {self.name!r} repeats a role parameter')
        skeleton = self.body.fill(SessionVar(_HOLE))
        mentioned = set(participants(skeleton))
        _check_role_usage(self.name, declared, mentioned)
        _check_free_vars(self.name, skeleton)


def do(routine: Routine, *actuals: Role) -> SessionFragment:
    """Call *routine* with *actuals* bound to its parameters, in order.

    The result splices into any position: the routine's own roles are renamed,
    the caller's continuation is not. ``do`` adds no node to the protocol —
    what comes out is an ordinary choreography, so projection, the journal and
    replay need to know nothing about routines.

    Args:
        routine: The choreography to call.
        *actuals: One role per parameter, in declaration order.

    Returns:
        A fragment equal to the routine's body under the binding.

    Raises:
        ValueError: if the number of roles does not match, or two parameters
            would be bound to the same role. Aliasing is rejected because it
            would build an interaction from a role to itself, which
            ``assert_wellformed`` does not catch.
    """
    if len(actuals) != len(routine.params):
        raise ValueError(
            f'routine {routine.name!r} takes {len(routine.params)} roles, got {len(actuals)}',
        )
    if len(set(actuals)) != len(actuals):
        names = _NAMES_SEPARATOR.join(role.name for role in actuals)
        raise ValueError(
            f'routine {routine.name!r} was called with the same role twice '
            f'({names}); distinct parameters need distinct roles',
        )
    binding = dict(zip(routine.params, actuals, strict=True))
    # Rename the body while its tail is still a marker, then graft the real
    # continuation in: `Fragment._fill` is a closure, so the body cannot be
    # rewritten in place, and rewriting `body.fill(tail)` would rename the
    # caller's roles too.
    skeleton = _rename(routine.body.fill(SessionVar(_HOLE)), binding)
    return Fragment(lambda tail: _substitute(skeleton, _HOLE, tail), SessionEnd())
