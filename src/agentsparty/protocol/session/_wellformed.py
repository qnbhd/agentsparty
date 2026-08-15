"""Well-formedness: closed, guarded, and role-partitioned session protocols."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import cast

from typing_extensions import assert_never

from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Fragment, Label
from agentsparty.protocol.session._recursion import _is_guarded, _map_branches
from agentsparty.protocol.session.types import (
    GlobalType,
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


def ensure_session(node: SessionType | Fragment[SessionType]) -> SessionType:
    """Close a :class:`Fragment` at a library boundary; pass a closed type through.

    Boundaries that historically required a sealed session protocol
    (``AgentRuntime``, ``Cast``, ``render``, ``project``, ``project_all``)
    call this so the user need not write ``.close()`` by hand. The operation
    is total: :meth:`Fragment.close` fills the hole with the fragment's own
    end.

    Args:
        node: A closed session protocol, or a still-open fragment of one.

    Returns:
        A closed :class:`SessionType`.
    """
    match node:
        case Fragment() as fragment:
            return cast(SessionType, fragment.close())
        case _:
            return node


def assert_wellformed(node: SessionType) -> None:
    """Reject open, unguarded, or ill-partitioned session protocols.

    Checks closedness (no free recursion variables), guardedness of every
    binder, and that internal and external role sets do not overlap. Raises
    :exc:`ValueError` on failure.

    Args:
        node: The session protocol to validate.

    Raises:
        ValueError: if *node* is open, unguarded, or mixes internal and
            external roles on the same participant.
    """
    _walk(node, frozenset())
    shared = ipart(node) & epart(node)
    if shared:
        _raise_shared_roles(shared)


def _walk(current: SessionType, bound: frozenset[str]) -> None:
    if _walk_atomic(current, bound):
        return
    match current:
        case (
            Interaction(branches=branches) | SendTo(branches=branches) | RecvFrom(branches=branches)
        ):
            _walk_interaction(branches, bound)
        case SessionRec(name=name, body=body):
            _walk_recursion(name, body, bound)
        case Parallel(branches=branches):
            _walk_parallel(branches)
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session node: {current!r}')


def _walk_atomic(current: SessionType, bound: frozenset[str]) -> bool:
    match current:
        case SessionEnd():
            return True
        case SessionVar(name=name):
            _check_bound(name, bound)
            return True
        case Fragment():
            raise TypeError(
                'expected a closed SessionType, got a Fragment.\n'
                'A protocol built with msg/alt/par is still open — '
                'seal it with .close():\n'
                '    proto = (msg[A, B]( "X", Text) >> '
                'msg[B, A]( "Y", Text)).close()',
            )
        case _:
            return False


def _check_bound(name: str, bound: frozenset[str]) -> None:
    if name not in bound:
        raise ValueError(f'free recursion variable {name!r}')


def _walk_interaction(
    branches: Mapping[Label, SessionBranchCase],
    bound: frozenset[str],
) -> None:
    for branch in branches.values():
        _walk(branch.continuation, bound)


def _walk_recursion(name: str, body: SessionType, bound: frozenset[str]) -> None:
    if not _is_guarded(name, body):
        raise ValueError(f'unguarded recursion variable {name!r}')
    _walk(body, bound | {name})


def _walk_parallel(branches: Sequence[SessionType]) -> None:
    # ``_parallel`` already rejects open branches; this boundary only checks
    # the independent role partition.
    for branch in branches:
        _walk(branch, frozenset())
    _assert_disjoint_roles(branches)


def _raise_shared_roles(shared: frozenset[Role]) -> None:
    names = ', '.join(sorted(role.name for role in shared))
    raise ValueError(
        f'roles appear as both internal and external participants: {names}',
    )


def as_global(node: SessionType) -> GlobalType:
    """Narrow *node* to a global protocol after checking its interface.

    The runtime interprets closed choreographies only: a ``SendTo`` or
    ``RecvFrom`` node means the protocol is a component; ``compose`` it
    with the rest of the system first.

    Args:
        node: A well-formed session protocol.

    Returns:
        The same node, carried as a global protocol.

    Raises:
        ValueError: if *node* contains an external interface node.
    """
    if epart(node):
        raise ValueError(
            'protocol still has an external interface; compose it with the '
            'rest of the system first (as_global)',
        )
    return cast(GlobalType, node)


def ipart(node: SessionType) -> frozenset[Role]:
    """Internal participants of *node*.

    Args:
        node: A session protocol tree.

    Returns:
        Roles that act as subjects of internal interactions or of external
        send/receive prefixes.
    """
    match node:
        case SessionEnd() | SessionVar():
            return frozenset()
        case SessionRec(body=body):
            return ipart(body)
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _ipart_prefix(prefix)
        case Parallel(branches=branches):
            return frozenset().union(*(ipart(branch) for branch in branches))
        case _:  # pragma: no cover
            assert_never(node)


def _ipart_prefix(prefix: Interaction | SendTo | RecvFrom) -> frozenset[Role]:
    match prefix:
        case Interaction(sender=sender, receiver=receiver, branches=branches):
            return frozenset((sender, receiver)) | _parts(branches, ipart)
        case SendTo(sender=sender, branches=branches):
            return frozenset((sender,)) | _parts(branches, ipart)
        case RecvFrom(receiver=receiver, branches=branches):
            return frozenset((receiver,)) | _parts(branches, ipart)
        case _:  # pragma: no cover
            assert_never(prefix)


def epart(node: SessionType) -> frozenset[Role]:
    """External participants of *node*.

    Args:
        node: A session protocol tree.

    Returns:
        Roles that appear only as the peer of an external interface prefix.
    """
    match node:
        case SessionEnd() | SessionVar():
            return frozenset()
        case SessionRec(body=body):
            return epart(body)
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _epart_prefix(prefix)
        case Parallel(branches=branches):
            return frozenset().union(*(epart(branch) for branch in branches))
        case _:  # pragma: no cover
            assert_never(node)


def _epart_prefix(prefix: Interaction | SendTo | RecvFrom) -> frozenset[Role]:
    match prefix:
        case Interaction(branches=branches):
            return _parts(branches, epart)
        case SendTo(receiver=receiver, branches=branches):
            return frozenset((receiver,)) | _parts(branches, epart)
        case RecvFrom(sender=sender, branches=branches):
            return frozenset((sender,)) | _parts(branches, epart)
        case _:  # pragma: no cover
            assert_never(prefix)


def _parts(
    branches: Mapping[Label, SessionBranchCase],
    of: Callable[[SessionType], frozenset[Role]],
) -> frozenset[Role]:
    continuations = (of(branch.continuation) for branch in branches.values())
    return frozenset().union(*continuations)


def _assert_disjoint_roles(branches: Sequence[SessionType]) -> None:
    """Raise if two branches share a role (ipart U epart)."""
    seen: dict[Role, int] = {}
    for index, branch in enumerate(branches):
        for role in ipart(branch) | epart(branch):
            other = seen.get(role)
            if other is not None:
                raise ValueError(
                    f'parallel branches {other} and {index} both mention '
                    f'role {role.name}; branches must own disjoint roles',
                )
            seen[role] = index


def _resolve_boundary(node: SessionType, owns: frozenset[Role]) -> SessionType:
    """Reclassify every prefix in *node* so that ``ipart(result) == owns``.

    The input tag is ignored — ``owns`` is the single source of truth for
    which roles are internal.  Continuations are rebuilt through
    :func:`_map_branches`.

    Args:
        node: A closed session protocol tree.
        owns: The roles the component owns; every other mentioned role is
            external.

    Returns:
        *node* with every ``Interaction``/``SendTo``/``RecvFrom`` re-tagged
        according to *owns*.

    Raises:
        ValueError: if a prefix mentions two roles and neither is in *owns*.
    """
    match node:
        case SessionEnd() | SessionVar():
            return node
        case SessionRec(name=name, body=body):
            return SessionRec(name, _resolve_boundary(body, owns))
        case Parallel(branches=branches):
            resolved = tuple(_resolve_boundary(b, owns) for b in branches)
            # Parallel guarantees ≥2 branches; unpacking satisfies _ParallelBranches.
            first, second, *rest = resolved
            return Parallel((first, second, *rest))
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _resolve_prefix(prefix, owns)
        case Fragment():
            raise TypeError(
                'expected a closed SessionType, got a Fragment. '
                'Seal it with .close() before passing to defining().',
            )


def _resolve_prefix(
    prefix: Interaction | SendTo | RecvFrom,
    owns: frozenset[Role],
) -> Interaction | SendTo | RecvFrom:
    s, r, brs = prefix.sender, prefix.receiver, prefix.branches
    conts = _map_branches(brs, lambda c: _resolve_boundary(c, owns))
    if s in owns and r in owns:
        return Interaction(s, r, conts)
    if s in owns and r not in owns:
        return SendTo(s, r, conts)
    if s not in owns and r in owns:
        return RecvFrom(s, r, conts)
    owned_names = ', '.join(sorted(role.name for role in owns))
    raise ValueError(
        f'Neither {s.name} nor {r.name} is owned by this component (owns: {owned_names})',
    )


def _assert_interface(resolved: SessionType, owns: frozenset[Role]) -> None:
    """Raise if any role in *owns* does not participate in *resolved*."""
    unused = owns - ipart(resolved)
    if unused:
        names = ', '.join(sorted(role.name for role in unused))
        raise ValueError(
            f'Role(s) declared in owns but not present in the component: {names}',
        )
