"""Endpoint-only subtyping: when one endpoint safely replaces another."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias

from typing_extensions import assert_never

from agentsparty._utils.assertions import pre
from agentsparty._utils.verdict import FITS, Differs, Fits, Verdict, holds
from agentsparty.kernel.errors import ConformanceError
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Label
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointBranchCase,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    free_vars,
    unfold,
)

_Assumed: TypeAlias = 'tuple[tuple[EndpointType, EndpointType], ...]'


def subtype(sub: EndpointType, sup: EndpointType) -> bool:
    """Whether a participant typed by *sub* may be used where *sup* is required.

    An external alt is contravariant — a subtype **accepts more** labels —
    and an internal alt is covariant — a subtype **sends fewer**. The peer
    is fixed: a subtype may not change whom it talks to.

    Payload sorts carry no subtyping of their own, so two branches agree when
    their codecs share a *name* — the same identity a journalled
    :class:`~agentsparty.journal.types.Decision` records, and the only one that
    survives ``list_of(Text) != list_of(Text)``.

    The relation unfolds recursion and treats a pair already seen as valid;
    both arguments must be closed.

    Args:
        sub: The endpoint type on offer.
        sup: The endpoint type required.

    Returns:
        Whether ``sub ≤ sup``.

    Examples:
        >>> from agentsparty.protocol import Text, case
        >>> from agentsparty.protocol.language.endpoint import offer, recv
        >>> from agentsparty.kernel.role import roles
        >>> Lead, Auditor = roles('Lead', 'Auditor')
        >>> tolerant = offer(Lead, case('Sign', Text), case('Paused')).close()
        >>> subtype(tolerant, recv(Lead, 'Sign', Text).close())
        True
        >>> subtype(recv(Lead, 'Sign', Text).close(), tolerant)
        False
    """
    pre(expr=not free_vars(sub), message='the offered endpoint type has free recursion variables')
    pre(expr=not free_vars(sup), message='the required endpoint type has free recursion variables')
    return holds(_relate(sub, sup, (), ()))


def _relate(
    sub: EndpointType,
    sup: EndpointType,
    trail: tuple[str, ...],
    assumed: _Assumed,
) -> Verdict:
    """``sub ≤ sup``, treating a pair already assumed as valid."""
    if (sub, sup) in assumed:
        return FITS
    return _compare(sub, sup, trail, assumed)


def _compare(
    sub: EndpointType,
    sup: EndpointType,
    trail: tuple[str, ...],
    assumed: _Assumed,
) -> Verdict:
    match sub, sup:
        # Unfold either side, remembering the pair that led here.
        case (EndpointRec(), _) | (_, EndpointRec()):
            return _relate_unfolded(sub, sup, trail, assumed)
        # Both sides have ended.
        case (EndpointEnd(), EndpointEnd()):
            return FITS
        # External alt, contravariant.
        case (
            EndpointBranch(sender=mine, branches=ours),
            EndpointBranch(sender=theirs, branches=needed),
        ) if mine == theirs:
            return _accepts(mine, ours, needed, trail, assumed)
        # Internal alt, covariant.
        case (
            EndpointSelect(receiver=mine, branches=ours),
            EndpointSelect(receiver=theirs, branches=needed),
        ) if mine == theirs:
            return _sends(mine, ours, needed, trail, assumed)
        case _:
            return Differs(trail, f'{_shape(sub)} cannot stand for {_shape(sup)}')


def _relate_unfolded(
    sub: EndpointType,
    sup: EndpointType,
    trail: tuple[str, ...],
    assumed: _Assumed,
) -> Verdict:
    remembered = (*assumed, (sub, sup))
    match sub:
        case EndpointRec():
            return _relate(unfold(sub), sup, trail, remembered)
        case _:
            return _relate(sub, unfold(sup), trail, remembered)


def _accepts(
    sender: Role,
    ours: Mapping[Label, EndpointBranchCase],
    needed: Mapping[Label, EndpointBranchCase],
    trail: tuple[str, ...],
    assumed: _Assumed,
) -> Verdict:
    """An external alt may accept more labels, never fewer."""
    unmet = needed.keys() - ours.keys()
    if unmet:
        return Differs(trail, f'{_names(unmet)} from {sender.name} is not accepted')
    return _pointwise(ours, needed, (*trail, f'?{sender.name}'), assumed)


def _sends(
    receiver: Role,
    ours: Mapping[Label, EndpointBranchCase],
    allowed: Mapping[Label, EndpointBranchCase],
    trail: tuple[str, ...],
    assumed: _Assumed,
) -> Verdict:
    """An internal alt may send fewer labels, never more."""
    extra = ours.keys() - allowed.keys()
    if extra:
        return Differs(trail, f'{_names(extra)} is not on offer to {receiver.name}')
    return _pointwise(ours, allowed, (*trail, f'!{receiver.name}'), assumed)


def _pointwise(
    ours: Mapping[Label, EndpointBranchCase],
    theirs: Mapping[Label, EndpointBranchCase],
    trail: tuple[str, ...],
    assumed: _Assumed,
) -> Verdict:
    """Relate the labels both sides carry; the first failure is the verdict."""
    shared = sorted(ours.keys() & theirs.keys())
    verdicts = (
        _arm(
            ours[label],
            theirs[label],
            trail,
            assumed,
        )
        for label in shared
    )
    return next((verdict for verdict in verdicts if not holds(verdict)), FITS)


def _arm(
    ours: EndpointBranchCase,
    theirs: EndpointBranchCase,
    trail: tuple[str, ...],
    assumed: _Assumed,
) -> Verdict:
    """One label present on both sides: same sort, related continuations."""
    here = (*trail, str(ours.label))
    if ours.payload.name != theirs.payload.name:
        ours_payload = ours.payload.name
        theirs_payload = theirs.payload.name
        return Differs(here, f'payload is {ours_payload}, not {theirs_payload}')
    return _relate(ours.continuation, theirs.continuation, here, assumed)


def _names(labels: set[Label]) -> str:
    return ', '.join(sorted(str(label) for label in labels))


def _shape(node: EndpointType) -> str:
    match node:
        case EndpointEnd():
            return 'end'
        case EndpointBranch(sender=sender):
            return f'an external alt from {sender.name}'
        case EndpointSelect(receiver=receiver):
            return f'an internal alt to {receiver.name}'
        case EndpointRec():
            return 'a loop'
        case _:
            return 'a recursion variable'


def _refuse(verdict: Verdict, role: Role) -> None:
    """Turn a failed verdict into the error a participant's constructor raises."""
    match verdict:
        case Fits():
            return
        case Differs(trail=trail, reason=reason):
            where = ' / '.join(trail) if trail else 'the root'
            raise ConformanceError(
                f'{role.name} declares a endpoint type that does not fit its role: '
                f'at {where}, {reason}',
            )
        case _:  # pragma: no cover
            assert_never(verdict)
