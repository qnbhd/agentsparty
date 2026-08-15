"""Compatibility checking and composition of components under a contract."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from functools import partial, reduce

from agentsparty._utils import assertions, verdict
from agentsparty.kernel.errors import CompositionError
from agentsparty.protocol.session._equivalence import _same, _shape
from agentsparty.protocol.session._projection import (
    _localise_open,
    _project_open,
    localise,
    project_onto,
)
from agentsparty.protocol.session._recursion import _map_branches, free_vars
from agentsparty.protocol.session._syntax import _parallel, branches_map
from agentsparty.protocol.session._wellformed import epart, ipart
from agentsparty.protocol.session.types import (
    Interaction,
    Parallel,
    RecvFrom,
    Role,
    SendTo,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
    _Prefix,
)


def assert_compatible(contract: SessionType, component: SessionType) -> None:
    """Check that *component* fits the part of *contract* it plays.

    The contract, restricted to the component's internal roles, must equal the
    component's interface.

    Raises:
        CompositionError: with the path to the first disagreement.
    """
    expected = project_onto(contract, ipart(component))
    offered = localise(component)
    _refuse_composition(_same(expected, offered, ()), component)


def compose(contract: SessionType, components: Sequence[SessionType]) -> SessionType:
    """Build the one protocol the whole system follows.

    Each component must fit its part of *contract*; internal role sets must
    be pairwise disjoint. Roles of *contract* not owned by any component are
    served by the contract itself, so an orchestrator's protocol may double
    as the contract. When *contract* is global, the result is global and
    ready for the runtime.

    Args:
        contract: The inter-component compatibility type.
        components: Subprotocols with disjoint internal role sets.

    Returns:
        The composed session protocol (global when *contract* and all interfaces absorb).

    Raises:
        CompositionError: if a component does not fit the contract or
            build-back is undefined.
        AssertionError: if internal role sets overlap.
    """
    assertions.pre(expr=_disjoint(components), message='components must own disjoint role sets')

    composed = reduce(_build_one, components, contract)
    component_interfaces = [ipart(component) for component in components]
    all_interfaces = set().union(*component_interfaces)
    remaining = set(epart(composed)) & all_interfaces
    assertions.post(
        expr=not remaining,
        message='composition must absorb every interface it was given',
    )
    return composed


def _build_one(contract: SessionType, component: SessionType) -> SessionType:
    assert_compatible(contract, component)
    return _build_back(contract, component, ipart(component))


def _disjoint(components: Sequence[SessionType]) -> bool:
    seen: set[Role] = set()
    for component in components:
        roles = ipart(component)
        if seen & roles:
            return False
        seen |= roles
    return True


def _refuse_composition(result: verdict.Verdict, component: SessionType) -> None:
    match result:
        case verdict.Fits():
            return
        case verdict.Differs(trail=trail, reason=reason):
            where = ' / '.join(trail) if trail else 'the root'
            internal_roles = ipart(component)
            internal_names = sorted(r.name for r in internal_roles)
            internals = ', '.join(internal_names) or '∅'
            raise CompositionError(
                f'component with internal roles {{{internals}}} is incompatible '
                f'with the contract: at {where}, {reason}',
            )
        case _:  # pragma: no cover
            raise TypeError(f'unexpected composition verdict: {result!r}')


def _build_back(
    contract: SessionType,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    built = _build_back_matched(contract, component, focus)
    if built is not None:
        return built
    return _composition_error(contract, component)


def _build_back_matched(
    contract: SessionType,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType | None:
    match contract:
        case SessionEnd() | SessionVar():
            return component
        case Parallel(branches=branches):
            return _build_into_branch(branches, component, focus)
        case SessionRec() as recursion:
            return _build_back_recursion(recursion, component, focus)
        case (SendTo() | RecvFrom() | Interaction()) as prefix:
            return _build_back_prefix(prefix, component, focus)
        case _:
            return None


def _build_back_prefix(
    prefix: Interaction | SendTo | RecvFrom,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    match prefix:
        case Interaction() as interaction:
            return _build_back_interaction(interaction, component, focus)
        case _:
            return _build_back_external_prefix(prefix, component, focus)


def _build_back_recursion(
    contract: SessionRec,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    contract_is_external = not (ipart(contract) & focus)
    contract_is_closed = not free_vars(contract)
    component_is_closed = not free_vars(component)
    if contract_is_external and contract_is_closed and component_is_closed:
        # No shared roles and no open ends left — the contract's tail and the
        # component have no common future.
        return _parallel([contract, component])
    match component:
        case Interaction() as inter if _touches(inter, focus) or not (ipart(contract) & focus):
            # Component's internal prefix first: push the contract under it.
            return replace(
                inter,
                branches=_map_branches(
                    inter.branches,
                    partial(_build_back, contract, focus=focus),
                ),
            )
        case SessionRec(name=contract_name, body=contract_body) if ipart(contract) & focus:
            if contract.name != contract_name:
                raise CompositionError(
                    f'recursion binders differ: contract μ{contract.name}, '
                    f'component μ{contract_name}',
                )
            return SessionRec(
                contract.name,
                _build_back(contract.body, contract_body, focus),
            )
        case _:
            return _composition_error(contract, component)


def _build_back_external_prefix(
    contract: SendTo | RecvFrom,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    match component:
        case (SendTo() | RecvFrom()) as prefix if _matching_prefix(contract, prefix):
            return _zip_prefix(type(contract), contract, prefix, focus)
        case Interaction() as inter if _prefix_touches(contract, focus):
            return _unmerge_contract_under(inter, contract, focus)
        case _ if not _prefix_touches(contract, focus):
            return _unmerge_component_under(contract, component, focus)
        case _:
            return _composition_error(contract, component)


def _build_back_interaction(
    contract: Interaction,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    match component:
        case (SendTo() | RecvFrom()) as prefix if _same_roles(contract, prefix):
            return _zip_prefix(Interaction, contract, prefix, focus)
        case Interaction() as inter if _touches(contract, focus):
            return _unmerge_contract_under(inter, contract, focus)
        case _ if not _touches(contract, focus):
            return _unmerge_component_under(contract, component, focus)
        case _:
            return _composition_error(contract, component)


def _matching_prefix(left: SendTo | RecvFrom, right: SendTo | RecvFrom) -> bool:
    match left, right:
        case (SendTo(), SendTo()) | (RecvFrom(), RecvFrom()):
            return _same_roles(left, right)
        case _:
            return False


def _same_roles(left: _Prefix, right: _Prefix) -> bool:
    return left.sender == right.sender and left.receiver == right.receiver


def _touches(prefix: Interaction, focus: frozenset[Role]) -> bool:
    return prefix.sender in focus or prefix.receiver in focus


def _prefix_touches(prefix: SendTo | RecvFrom, focus: frozenset[Role]) -> bool:
    match prefix:
        case SendTo(sender=sender):
            return sender in focus
        case RecvFrom(receiver=receiver):
            return receiver in focus


def _composition_error(contract: SessionType, component: SessionType) -> SessionType:
    raise CompositionError(
        f'build-back is undefined for {_shape(contract)} against {_shape(component)}',
    )


def _build_into_branch(
    branches: tuple[SessionType, ...],
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    """Build the component into the parallel branch that owns its roles.

    At most one branch can own the component's roles; the others have no
    interaction with it and are carried over untouched.

    Raises:
        CompositionError: if the component's roles span two branches.
    """
    owning = _owning_branches(branches, focus)
    if len(owning) > 1:
        raise CompositionError(
            'component roles span two parallel branches of the contract; '
            'there is no unique branch to build into',
        )
    # Exactly one owner, or none: recurse into the owner, or into the first
    # branch when the component shares no roles with any (introduces a nested
    # parallel there).
    target = owning[0] if owning else 0
    rebuilt = [
        _build_back(branch, component, focus) if index == target else branch
        for index, branch in enumerate(branches)
    ]
    return _parallel(rebuilt)


def _owning_branches(
    branches: tuple[SessionType, ...],
    focus: frozenset[Role],
) -> list[int]:
    branch_roles = tuple(ipart(branch) for branch in branches)
    return [index for index, roles in enumerate(branch_roles) if roles & focus]


def _zip_prefix(
    kind: type[Interaction] | type[SendTo] | type[RecvFrom],
    contract: _Prefix,
    component: _Prefix,
    focus: frozenset[Role],
) -> SessionType:
    if contract.branches.keys() != component.branches.keys():
        raise CompositionError(f'interface labels differ under {_shape(contract)}')
    return kind(
        contract.sender,
        contract.receiver,
        branches_map(
            replace(
                branch,
                continuation=_build_back(
                    branch.continuation,
                    component.branches[label].continuation,
                    focus,
                ),
            )
            for label, branch in contract.branches.items()
        ),
    )


def _unmerge_contract_under(
    inter: Interaction,
    contract: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    transform = partial(_unmerge_contract_continuation, contract=contract, focus=focus)
    return replace(inter, branches=_map_branches(inter.branches, transform))


def _unmerge_contract_continuation(
    cont: SessionType,
    contract: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    interface = _localise_open(cont)
    fitted = _fit(contract, interface, seen=partial(_contract_touches, focus=focus))
    assertions.safe_assert(
        expr=verdict.holds(_same(_project_open(fitted, focus), interface, ())),
        message='unmerge must restore compatibility on the contract side',
    )
    return _build_back(fitted, cont, focus)


def _contract_touches(node: SessionType, focus: frozenset[Role]) -> bool:
    match node:
        case Interaction(sender=sender, receiver=receiver):
            return sender in focus or receiver in focus
        case SendTo(sender=sender):
            return sender in focus
        case RecvFrom(receiver=receiver):
            return receiver in focus
        case _:
            return False


def _unmerge_component_under(
    prefix: _Prefix,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    transform = partial(
        _unmerge_component_continuation,
        component=component,
        focus=focus,
    )
    return replace(prefix, branches=_map_branches(prefix.branches, transform))


def _unmerge_component_continuation(
    cont: SessionType,
    component: SessionType,
    focus: frozenset[Role],
) -> SessionType:
    interface = _project_open(cont, focus)
    fitted = _fit(component, interface, seen=_is_external_prefix)
    assertions.safe_assert(
        expr=verdict.holds(_same(_localise_open(fitted), interface, ())),
        message='unmerge must restore compatibility on the component side',
    )
    return _build_back(cont, fitted, focus)


def _is_external_prefix(node: SessionType) -> bool:
    match node:
        case SendTo() | RecvFrom():
            return True
        case _:
            return False


def _fit(
    general: SessionType,
    view: SessionType,
    seen: Callable[[SessionType], bool],
) -> SessionType:
    """Prune *general* to the branch shapes of *view*.

    *seen* says which prefix nodes of *general* survive into the merged view
    the *view* was taken from: for the contract side (unmL) — nodes touching
    the component's roles; for the component side (unmP) — interface nodes.
    Unseen prefixes are kept whole and recursed with the same *view*.
    Recursion and leaves match by structure, not by *seen*.

    Raises:
        CompositionError: when *view* cannot be carved out of *general* —
            the honest boundary of this implementation.
    """
    fitted = _fit_matched(general, view, seen)
    if fitted is not None:
        return fitted
    return _fit_error(general, view)  # pragma: no cover


def _fit_matched(
    general: SessionType,
    view: SessionType,
    seen: Callable[[SessionType], bool],
) -> SessionType | None:
    match general:
        case SessionEnd() | SessionVar():
            return _fit_leaf(general, view)
        case SessionRec(name=name, body=body):
            return _fit_rec(name, body, view, seen)
        case Parallel():
            return _fit_parallel(general, view)
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _fit_prefix_or_unseen(prefix, view, seen)
        case _:  # pragma: no cover
            return None


def _fit_leaf(general: SessionType, view: SessionType) -> SessionType:
    match general:
        case SessionEnd():
            return _fit_end(view)
        case SessionVar() as variable:
            return _fit_var(variable, view)
        case _:  # pragma: no cover
            return _fit_error(general, view)


def _fit_parallel(general: SessionType, view: SessionType) -> SessionType:
    if verdict.holds(_same(general, view, ())):
        return general
    return _fit_error(general, view)


def _fit_end(view: SessionType) -> SessionType:
    match view:
        case SessionEnd():
            return SessionEnd()
        case _:
            return _fit_error(SessionEnd(), view)


def _fit_var(general: SessionVar, view: SessionType) -> SessionType:
    match view:
        case SessionVar(name=name) if general.name == name:
            return general
        case _:
            return _fit_error(general, view)


def _fit_rec(
    name: str,
    body: SessionType,
    view: SessionType,
    seen: Callable[[SessionType], bool],
) -> SessionType:
    match view:
        case SessionRec(name=view_name, body=view_body) if name == view_name:
            return SessionRec(name, _fit(body, view_body, seen))
        case SessionEnd():
            return SessionEnd()
        case _:
            return _fit_error(SessionRec(name, body), view)


def _fit_prefix_or_unseen(
    prefix: Interaction | SendTo | RecvFrom,
    view: SessionType,
    seen: Callable[[SessionType], bool],
) -> SessionType:
    if not seen(prefix):
        return replace(
            prefix,
            branches=_map_branches(
                prefix.branches,
                partial(_fit_unseen_continuation, view=view, seen=seen),
            ),
        )
    return _fit_prefix(prefix, view, prefix, seen)


def _fit_prefix(
    general: Interaction | SendTo | RecvFrom,
    view: SessionType,
    original: SessionType,
    seen: Callable[[SessionType], bool],
) -> SessionType:
    match view:
        case (Interaction() | SendTo() | RecvFrom()) as target if _fit_compatible(
            general,
            target,
        ):
            missing = target.branches.keys() - general.branches.keys()
            if missing:
                names = ', '.join(sorted(str(label) for label in missing))
                raise CompositionError(
                    f'view carries labels absent from general: {names}',
                )
            return replace(
                general,
                branches=branches_map(
                    replace(
                        general.branches[label],
                        continuation=_fit(
                            general.branches[label].continuation,
                            target.branches[label].continuation,
                            seen,
                        ),
                    )
                    for label in target.branches
                ),
            )
        case _:
            return _fit_error(original, view)


def _fit_compatible(
    general: Interaction | SendTo | RecvFrom,
    view: Interaction | SendTo | RecvFrom,
) -> bool:
    match general, view:
        case (Interaction(), Interaction()):
            return _same_roles(general, view)
        case (SendTo(), SendTo()) | (RecvFrom(), RecvFrom()):
            return _same_roles(general, view)
        case (Interaction(), SendTo() | RecvFrom()):
            return _same_roles(general, view)
        case _:
            return False


def _fit_error(general: SessionType, view: SessionType) -> SessionType:
    raise CompositionError(f'cannot fit {_shape(view)} out of {_shape(general)}')


def _fit_unseen_continuation(
    continuation: SessionType,
    view: SessionType,
    seen: Callable[[SessionType], bool],
) -> SessionType:
    local_view = _fit(view, _localise_open(continuation), seen=_always_seen)
    return _fit(continuation, local_view, seen)


def _always_seen(_node: SessionType) -> bool:
    return True
