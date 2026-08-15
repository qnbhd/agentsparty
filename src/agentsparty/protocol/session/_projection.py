"""Generalised projection and localisation of session types."""

from __future__ import annotations

from collections.abc import Mapping
from functools import reduce
from typing import cast

from agentsparty._utils.assertions import pre
from agentsparty.protocol.session._bridge import EndpointType, as_endpoint
from agentsparty.protocol.session._equivalence import (
    ProjectionError,
    _brief_view,
    _merge_interface,
    _merge_view,
)
from agentsparty.protocol.session._participants import participants
from agentsparty.protocol.session._recursion import _is_guarded, _map_branches, free_vars
from agentsparty.protocol.session._syntax import _parallel
from agentsparty.protocol.session._wellformed import (
    assert_wellformed,
    ensure_session,
    epart,
    ipart,
)
from agentsparty.protocol.session.types import (
    Fragment,
    Interaction,
    Label,
    Parallel,
    RecvFrom,
    Role,
    SendTo,
    SessionBranchCase,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
    SingleSubject,
)


def _outsider_merge(
    branches: Mapping[Label, SessionBranchCase],
    focus: frozenset[Role],
    sender: Role,
    receiver: Role,
) -> SessionType:
    """Merge projected continuations of a alt that *focus* does not see.

    Builds a diagnostic that names the focus role, the alt parties, and
    every branch label when the merge is undefined.
    """
    conts = [branch.continuation for branch in branches.values()]
    try:
        return reduce(_merge_view, conts)
    except ProjectionError as exc:
        raise _outsider_error(exc, branches, focus, sender, receiver) from None


def _outsider_error(
    exc: ProjectionError,
    branches: Mapping[Label, SessionBranchCase],
    focus: frozenset[Role],
    sender: Role,
    receiver: Role,
) -> ProjectionError:
    if _is_meta_error(exc):
        return exc
    role = _focus_name(focus)
    ordered = _ordered_branches(branches)
    details = ', '.join(
        f'on {str(label)!r} it must {_brief_view(branch.continuation)}' for label, branch in ordered
    )
    return ProjectionError(
        f'role {role!r} cannot tell the branches of the alt '
        f'{sender.name} -> {receiver.name} apart:\n'
        f'  {details}.\n'
        'A role that behaves differently per branch must be told which '
        'branch was taken — add a message from '
        f'{sender.name} (or {receiver.name}) to {role} inside each branch.',
    )


def _is_meta_error(exc: ProjectionError) -> bool:
    detail = str(exc)
    return any(bit in detail for bit in ('two payloads', 'two intents', 'two deadlines'))


def project_onto(node: SessionType, focus: frozenset[Role]) -> SessionType:
    """Generalised projection of *node* onto the roles in *focus*.

    Precondition: *focus* contains no external participant of *node* —
    projection is defined onto internal roles only.

    Args:
        node: A closed, guarded session type.
        focus: The set of roles to retain as internal.

    Returns:
        The session type as seen by *focus*.

    Raises:
        ValueError: if *node* is ill-formed.
        AssertionError: if *focus* intersects ``epart(node)``.
        ProjectionError: if merge is undefined for an observer of a alt.
    """
    assert_wellformed(node)
    pre(expr=not (focus & epart(node)), message='projection is defined onto internal roles only')
    return _restrict(node, focus)


def _project_open(node: SessionType, focus: frozenset[Role]) -> SessionType:
    """Projection without the closedness check — used inside build-back."""
    pre(expr=not (focus & epart(node)), message='projection is defined onto internal roles only')
    return _restrict(node, focus)


def _restrict(node: SessionType, focus: frozenset[Role]) -> SessionType:
    match node:
        case SessionEnd() | SessionVar():
            return node
        case SessionRec(name=name, body=body):
            return _restrict_rec(name, body, focus)
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _restrict_prefix(prefix, focus)
        case Parallel(branches=branches):
            return _restrict_parallel(branches, focus)
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session node: {node!r}')


def _restrict_rec(name: str, body: SessionType, focus: frozenset[Role]) -> SessionType:
    if not (focus & (ipart(body) | epart(body))):
        return SessionEnd()
    projected = _restrict(body, focus)
    return SessionRec(name, projected) if _is_guarded(name, projected) else SessionEnd()


def _restrict_prefix(
    prefix: Interaction | SendTo | RecvFrom,
    focus: frozenset[Role],
) -> SessionType:
    match prefix:
        case Interaction(sender=s, receiver=r, branches=brs):
            return _restrict_msg(s, r, brs, focus)
        case SendTo(sender=s, receiver=r, branches=brs):
            return _restrict_send(s, r, brs, focus)
        case RecvFrom(sender=s, receiver=r, branches=brs):
            return _restrict_recv(s, r, brs, focus)
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session prefix: {prefix!r}')


def _restrict_parallel(
    branches: tuple[SessionType, ...],
    focus: frozenset[Role],
) -> SessionType:
    """A focus inside one parallel branch sees that branch alone.

    Raises:
        ProjectionError: if *focus* spans two branches — they have no common
            order, so there is nothing to project onto.
    """
    branch_parties = tuple(ipart(branch) | epart(branch) for branch in branches)
    owning = [
        branch for branch, parties in zip(branches, branch_parties, strict=True) if focus & parties
    ]
    if not owning:
        return SessionEnd()
    if len(owning) == 1:
        return _restrict(owning[0], focus)
    names = _parallel_overlap_names(owning, focus)
    raise ProjectionError(
        f'role(s) {names} spans two parallel branches and have no projection: '
        'the branches have no common order — keep each role inside one branch',
    )


def _parallel_overlap_names(owning: list[SessionType], focus: frozenset[Role]) -> str:
    spanned: set[Role] = set()
    for node in owning:
        spanned |= focus & (ipart(node) | epart(node))
    spanned_names = ', '.join(sorted(role.name for role in spanned))
    focus_names = ', '.join(sorted(role.name for role in focus))
    return spanned_names or focus_names


def _focus_name(focus: frozenset[Role]) -> str:
    if not focus:
        return 'observer'
    return next(iter(sorted(focus, key=lambda one: one.name))).name


def _ordered_branches(
    branches: Mapping[Label, SessionBranchCase],
) -> list[tuple[Label, SessionBranchCase]]:
    return sorted(branches.items(), key=lambda item: str(item[0]))


def _restrict_msg(
    sender: Role,
    receiver: Role,
    branches: Mapping[Label, SessionBranchCase],
    focus: frozenset[Role],
) -> SessionType:
    # both internal → keep Interaction; sender only → SendTo; receiver only → RecvFrom
    conts = _map_branches(branches, lambda cont: _restrict(cont, focus))
    if sender in focus and receiver in focus:
        return Interaction(sender, receiver, conts)
    if sender in focus and receiver not in focus:
        return SendTo(sender, receiver, conts)
    if sender not in focus and receiver in focus:
        return RecvFrom(sender, receiver, conts)
    return _outsider_merge(conts, focus, sender, receiver)


def _restrict_send(
    sender: Role,
    receiver: Role,
    branches: Mapping[Label, SessionBranchCase],
    focus: frozenset[Role],
) -> SessionType:
    conts = _map_branches(branches, lambda cont: _restrict(cont, focus))
    if sender in focus and receiver not in focus:
        return SendTo(sender, receiver, conts)
    if sender not in focus and receiver not in focus:
        return _outsider_merge(conts, focus, sender, receiver)
    raise ProjectionError(
        'projection is defined onto internal roles only '
        f'(cannot project SendTo onto external {receiver.name})',
    )


def _restrict_recv(
    sender: Role,
    receiver: Role,
    branches: Mapping[Label, SessionBranchCase],
    focus: frozenset[Role],
) -> SessionType:
    conts = _map_branches(branches, lambda cont: _restrict(cont, focus))
    if sender not in focus and receiver in focus:
        return RecvFrom(sender, receiver, conts)
    if sender not in focus and receiver not in focus:
        return _outsider_merge(conts, focus, sender, receiver)
    raise ProjectionError(
        'projection is defined onto internal roles only '
        f'(cannot project RecvFrom onto external {sender.name})',
    )


def localise(node: SessionType) -> SessionType:
    """Interface of a component: keep ``p!q``/``p?q``, drop ``p→q``.

    What a teammate may rely on — and the only thing compatibility reads.

    Args:
        node: A closed, guarded session type (typically a component).

    Returns:
        The external interface of *node*.
    """
    assert_wellformed(node)
    return _localise(node)


def _localise_open(node: SessionType) -> SessionType:
    """The localise step without the closedness check — used inside build-back."""
    return _localise(node)


def _localise(node: SessionType) -> SessionType:
    match node:
        case SessionEnd() | SessionVar():
            return node
        case SessionRec(name=name, body=body):
            return _localise_rec(node, name, body)
        case Interaction(branches=branches):
            return reduce(
                _merge_interface,
                (_localise(branch.continuation) for branch in branches.values()),
            )
        case SendTo() | RecvFrom() as prefix:
            return _localise_prefix(prefix)
        case Parallel(branches=branches):
            # Distribute over parallel branches.
            return _parallel([_localise(branch) for branch in branches])
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session node: {node!r}')


def _localise_rec(node: SessionRec, name: str, body: SessionType) -> SessionType:
    if not free_vars(node) and not epart(body):
        return SessionEnd()
    projected = _localise(body)
    return SessionRec(name, projected) if _is_guarded(name, projected) else SessionEnd()


def _localise_prefix(prefix: SendTo | RecvFrom) -> SessionType:
    match prefix:
        case SendTo(sender=sender, receiver=receiver, branches=branches):
            return SendTo(sender, receiver, _map_branches(branches, _localise))
        case RecvFrom(sender=sender, receiver=receiver, branches=branches):
            return RecvFrom(sender, receiver, _map_branches(branches, _localise))
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session prefix: {prefix!r}')


def project(node: SessionType | Fragment[SessionType], subj: Role) -> EndpointType:
    """Derive the endpoint protocol *subj* has to follow.

    Validates well-formedness of *node* once at the root, then projects.
    Implemented as the singleton special case of :func:`project_onto`. An open
    :class:`~agentsparty.protocol.language.core.Fragment` is closed at this boundary.

    Args:
        node: A closed, guarded session type (choreography or a component),
            or a fragment that will be closed first.
        subj: The role whose endpoint view is required.

    Raises:
        ValueError: if *node* is open or unguarded.
        ProjectionError: if merge is undefined for an observer of a alt.
    """
    projected = project_onto(ensure_session(node), frozenset((subj,)))
    return as_endpoint(cast(SingleSubject, projected))


def project_all(
    node: SessionType | Fragment[SessionType],
) -> list[tuple[Role, EndpointType]]:
    """Project *node* for every participant, in order of first appearance.

    An open :class:`~agentsparty.protocol.language.core.Fragment` is closed at this boundary.

    Args:
        node: The session type to project, or a fragment that will be closed.

    Returns:
        Pairs of ``(role, endpoint protocol)``, one per participant.
    """
    closed = ensure_session(node)
    return [(subject, project(closed, subject)) for subject in participants(closed)]
