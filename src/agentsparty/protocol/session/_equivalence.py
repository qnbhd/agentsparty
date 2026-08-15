"""Session equality and the two merge flavours used by projection."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from functools import partial
from itertools import chain
from typing import Final, TypeAlias

from agentsparty._utils.verdict import FITS, Differs, Verdict, holds
from agentsparty.kernel.errors import ProjectionError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.protocol.language.core import Label, branches_map
from agentsparty.protocol.session._wellformed import epart, ipart
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

_NAMES_SEPARATOR: Final = ', '


def _merge_view(left: SessionType, right: SessionType) -> SessionType:
    """Projection merge: how a role outside a alt unifies its futures.

    External inputs may widen (full merge); everything else must agree
    pointwise. Combinations that cannot unify raise ProjectionError.
    """
    return _merge(left, right, send_arms=_pointwise_arms)


def _merge_interface(left: SessionType, right: SessionType) -> SessionType:
    """Interface merge: the interface of a component's futures.

    Both directions union their labels: an earlier internal alt widens the
    interface, so every branch the component may still take stays on offer.
    """
    return _merge(left, right, send_arms=_union_arms)


_Merge: TypeAlias = Callable[[SessionType, SessionType], SessionType]


def _merged_arm(a: SessionBranchCase, b: SessionBranchCase, merge: _Merge) -> SessionBranchCase:
    """One label present on both sides: same meta, merged continuations."""
    _require_same_meta(a, b)
    return replace(a, continuation=merge(a.continuation, b.continuation))


def _merge(
    left: SessionType,
    right: SessionType,
    send_arms: Callable[
        [Mapping[Label, SessionBranchCase], Mapping[Label, SessionBranchCase], _Merge],
        NonEmptyMap[Label, SessionBranchCase],
    ],
) -> SessionType:
    """Shared body of both merges; the flavours differ only on SendTo arms."""
    if holds(_same(left, right, ())):
        return left

    again = partial(_merge, send_arms=send_arms)

    match left, right:
        case (
            RecvFrom(sender=ls, receiver=lr, branches=lb),
            RecvFrom(sender=rs, receiver=rr, branches=rb),
        ) if ls == rs and lr == rr:
            return RecvFrom(ls, lr, _union_arms(lb, rb, again))
        case (
            SendTo(sender=ls, receiver=lr, branches=lb),
            SendTo(sender=rs, receiver=rr, branches=rb),
        ) if ls == rs and lr == rr:
            return SendTo(ls, lr, send_arms(lb, rb, again))
        case (
            Interaction(sender=ls, receiver=lr, branches=lb),
            Interaction(sender=rs, receiver=rr, branches=rb),
        ) if ls == rs and lr == rr:
            return Interaction(ls, lr, _pointwise_arms(lb, rb, again))
        case (SessionRec(name=ln, body=lb), SessionRec(name=rn, body=rb)) if ln == rn:
            return SessionRec(ln, again(lb, rb))
        case _:
            raise ProjectionError(_indistinguishable_branches_message(left, right))


def _union_arms(
    left: Mapping[Label, SessionBranchCase],
    right: Mapping[Label, SessionBranchCase],
    merge: _Merge,
) -> NonEmptyMap[Label, SessionBranchCase]:
    """Full merge of labelled arms: shared labels agree on meta, conts merge."""
    left_only = (left[k] for k in left.keys() - right.keys())
    right_only = (right[k] for k in right.keys() - left.keys())
    shared_labels = left.keys() & right.keys()
    shared = (_merged_arm(left[k], right[k], merge) for k in shared_labels)
    return branches_map(chain(left_only, right_only, shared))


def _pointwise_arms(
    left: Mapping[Label, SessionBranchCase],
    right: Mapping[Label, SessionBranchCase],
    merge: _Merge,
) -> NonEmptyMap[Label, SessionBranchCase]:
    """Pointwise merge: label sets must agree exactly."""
    if left.keys() != right.keys():
        raise _pointwise_error(left, right)

    merged = (_merged_arm(left[k], right[k], merge) for k in left)
    return branches_map(merged)


def _pointwise_error(
    left: Mapping[Label, SessionBranchCase],
    right: Mapping[Label, SessionBranchCase],
) -> ProjectionError:
    left_offers = _offer_labels(left, right)
    right_offers = _offer_labels(right, left)
    return ProjectionError(
        'a role outside a alt cannot tell the branches apart: '
        f'one branch offers labels [{left_offers}] '
        f'while another offers [{right_offers}]',
    )


def _offer_labels(
    primary: Mapping[Label, SessionBranchCase],
    secondary: Mapping[Label, SessionBranchCase],
) -> str:
    specific_labels = primary.keys() - secondary.keys()
    specific = sorted(str(label) for label in specific_labels)
    fallback = sorted(str(label) for label in primary)
    return _NAMES_SEPARATOR.join(specific or fallback)


def _require_same_meta(a: SessionBranchCase, b: SessionBranchCase) -> None:
    for field, left, right in (
        ('payloads', a.payload.name, b.payload.name),
        ('intents', a.intent, b.intent),
        ('deadlines', a.within, b.within),
    ):
        if left != right:
            raise ProjectionError(f'label {a.label} carries two {field} in a merge')


def _brief_view(node: SessionType) -> str:
    """One short clause describing what a projected branch requires."""
    match node:
        case SessionEnd():
            return 'do nothing (end)'
        case SessionVar(name=name):
            return f'loop at {name!r}'
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _brief_prefix(prefix)
        case SessionRec(name=name):
            return f'enter recursion {name!r}'
        case Parallel(branches=branches):
            return f'run {len(branches)} parallel branches'
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session node: {node!r}')


def _brief_prefix(prefix: Interaction | SendTo | RecvFrom) -> str:
    match prefix:
        case (
            Interaction(sender=s, receiver=r, branches=brs)
            | SendTo(
                sender=s,
                receiver=r,
                branches=brs,
            )
        ):
            labels = _NAMES_SEPARATOR.join(sorted(str(label) for label in brs))
            return f'send {labels} to {r.name} (as {s.name})'
        case RecvFrom(sender=s, receiver=r, branches=brs):
            labels = _NAMES_SEPARATOR.join(sorted(str(label) for label in brs))
            return f'receive {labels} from {s.name} (as {r.name})'
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session prefix: {prefix!r}')


def _indistinguishable_branches_message(left: SessionType, right: SessionType) -> str:
    """What / why / what-to-do for a failed outsider merge of two views."""
    left_roles = _role_names(left)
    right_roles = _role_names(right)
    named = sorted(set(left_roles) | set(right_roles))
    named_roles = _NAMES_SEPARATOR.join(repr(name) for name in named)
    if len(named) == 1:
        role_bit = f'role {named[0]!r}'
    elif named:
        role_bit = f'role(s) {named_roles}'
    else:
        role_bit = 'a role outside a alt'
    return (
        f'{role_bit} cannot tell the branches of a alt apart:\n'
        f'  on one branch it must {_brief_view(left)}, '
        f'on another it must {_brief_view(right)}.\n'
        'A role that behaves differently per branch must be told which branch '
        'was taken — add a message from a choosing party to this role inside '
        'each branch.'
    )


def _role_names(node: SessionType) -> list[str]:
    return sorted(role.name for role in ipart(node) | epart(node))


def _same(left: SessionType, right: SessionType, trail: tuple[str, ...]) -> Verdict:
    """Structural equality with the project's payload identity.

    Codecs compare by name, intents and deadlines literally, binders by name.
    """
    matched = _same_matched(left, right, trail)
    if matched is not None:
        return matched
    return Differs(trail, f'{_shape(left)} is not {_shape(right)}')


def _same_matched(
    left: SessionType,
    right: SessionType,
    trail: tuple[str, ...],
) -> Verdict | None:
    if _same_leaf(left, right):
        return FITS
    match left, right:
        case (SessionRec(name=ln, body=lb), SessionRec(name=rn, body=rb)) if ln == rn:
            return _same(lb, rb, (*trail, f'μ{ln}'))
        case (
            (Interaction() | SendTo() | RecvFrom()) as left_prefix,
            (Interaction() | SendTo() | RecvFrom()) as right_prefix,
        ):
            return _same_prefix(left_prefix, right_prefix, trail)
        case (Parallel(branches=lb), Parallel(branches=rb)) if len(lb) == len(rb):
            return _same_parallel(lb, rb, trail)
        case _:
            return None


def _same_leaf(left: SessionType, right: SessionType) -> bool:
    """Whether two end/var leaves are equal (ends always; vars by name)."""
    match left, right:
        case (SessionEnd(), SessionEnd()):
            return True
        case (SessionVar(name=ln), SessionVar(name=rn)):
            return ln == rn
        case _:
            return False


def _same_prefix(
    left: Interaction | SendTo | RecvFrom,
    right: Interaction | SendTo | RecvFrom,
    trail: tuple[str, ...],
) -> Verdict:
    match left, right:
        case (Interaction(), Interaction()):
            pass
        case (SendTo(), SendTo()):
            pass
        case (RecvFrom(), RecvFrom()):
            pass
        case _:
            return Differs(trail, f'{_shape(left)} is not {_shape(right)}')
    if left.sender != right.sender or left.receiver != right.receiver:
        return Differs(trail, f'{_shape(left)} is not {_shape(right)}')
    return _same_arms(left.branches, right.branches, (*trail, _shape(left)))


def _same_parallel(
    left: tuple[SessionType, ...],
    right: tuple[SessionType, ...],
    trail: tuple[str, ...],
) -> Verdict:
    for index, (a, b) in enumerate(zip(left, right, strict=True)):
        verdict = _same(a, b, (*trail, f'|{index}'))
        if not holds(verdict):
            return verdict
    return FITS


def _same_arms(
    left: Mapping[Label, SessionBranchCase],
    right: Mapping[Label, SessionBranchCase],
    trail: tuple[str, ...],
) -> Verdict:
    if left.keys() != right.keys():
        return _different_labels(left, right, trail)
    for label in sorted(left.keys()):
        arm_trail = (*trail, str(label))
        verdict = _same_arm(left[label], right[label], arm_trail)
        if not holds(verdict):
            return verdict
    return FITS


def _same_arm(left: SessionBranchCase, right: SessionBranchCase, trail: tuple[str, ...]) -> Verdict:
    if left.payload.name != right.payload.name:
        return _different_payload(left, right, trail)
    if left.intent != right.intent:
        return Differs(trail, 'intents differ')
    if left.within != right.within:
        return Differs(trail, 'deadlines differ')
    return _same(left.continuation, right.continuation, trail)


def _different_labels(
    left: Mapping[Label, SessionBranchCase],
    right: Mapping[Label, SessionBranchCase],
    trail: tuple[str, ...],
) -> Verdict:
    different = left.keys() ^ right.keys()
    names = _NAMES_SEPARATOR.join(sorted(str(label) for label in different))
    return Differs(trail, f'labels differ: {names}')


def _different_payload(
    left: SessionBranchCase,
    right: SessionBranchCase,
    trail: tuple[str, ...],
) -> Verdict:
    left_name = left.payload.name
    right_name = right.payload.name
    return Differs(trail, f'payload is {left_name}, not {right_name}')


def _shape(node: SessionType) -> str:
    match node:
        case SessionEnd():
            return 'end'
        case SessionVar(name=name):
            return f'var {name}'
        case SessionRec(name=name):
            return f'rec {name}'
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _shape_prefix(prefix)
        case Parallel():
            return 'par'
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session node: {node!r}')


def _shape_prefix(prefix: Interaction | SendTo | RecvFrom) -> str:
    match prefix:
        case Interaction(sender=sender, receiver=receiver):
            return f'{sender.name}->{receiver.name}'
        case SendTo(sender=sender, receiver=receiver):
            return f'{sender.name}!{receiver.name}'
        case RecvFrom(sender=sender, receiver=receiver):
            return f'{sender.name}?{receiver.name}'
        case _:  # pragma: no cover
            raise TypeError(f'unexpected session prefix: {prefix!r}')


def equal_session(left: SessionType, right: SessionType) -> bool:
    """Whether *left* and *right* are equal under the project's payload identity.

    Args:
        left: A session type.
        right: Another session type.

    Returns:
        ``True`` when structure, roles, labels, codec names, intents and
        deadlines agree.
    """
    return holds(_same(left, right, ()))
