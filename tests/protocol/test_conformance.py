"""Laws for process-oriented local subtyping and the association boundary.

L1-L6 are properties; L7-L10 are examples that have no clean algebraic form.
L4 and L5 each carry both poles so an always-True relation cannot pass.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.errors import ConformanceError, ProjectionError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role, roles
from agentsparty.machine import Machine
from agentsparty.participant import Choice
from agentsparty.protocol import (
    Integer,
    Text,
    alt,
    associate,
    case,
    list_of,
    msg,
    project,
    rec,
    subtype,
    var,
)
from agentsparty.protocol.language.core import Label
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointBranchCase,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    free_vars,
    offer,
    recv,
    unfold,
)
from agentsparty.protocol.language.endpoint import rec as endpoint_rec
from agentsparty.protocol.language.endpoint import var as endpoint_var
from agentsparty.protocol.session import SessionType
from tests.protocol import strategies

A, B, C = roles('A', 'B', 'C')


def _small_protocols() -> list[SessionType]:
    p1 = msg[A, B]('Hi').close()
    p2 = msg[A, B]('Hi', Integer).close()
    p3 = alt[A, B](case('Ok'), case('No', Text) >> msg[B, A]('Ack')).close()
    p4 = (msg[A, B]('X') >> msg[B, C]('Y') >> msg[C, A]('Z')).close()
    p5 = rec('t', alt[A, B](case('ping') >> var('t'), case('done'))).close()
    return [p1, p2, p3, p4, p5]


_PROTOS = _small_protocols()
_ENDPOINTS: list[EndpointType] = []
for _p in _PROTOS:
    for _r in (A, B, C):
        with suppress(ProjectionError):
            _ENDPOINTS.append(project(_p, _r))


def _map_plus(
    base: Mapping[Label, EndpointBranchCase],
    name: str,
) -> NonEmptyMap[Label, EndpointBranchCase]:
    """Copy *base* and add one fresh end-continuation arm."""
    fresh = Label(name)
    data = dict(base)
    data[fresh] = EndpointBranchCase(fresh, Text, EndpointEnd())
    return NonEmptyMap.of_mapping(data)


def _map_minus(
    base: Mapping[Label, EndpointBranchCase],
) -> NonEmptyMap[Label, EndpointBranchCase] | None:
    """Copy *base* without one root label, or None if only one remains."""
    if len(base) < 2:
        return None
    drop = min(base.keys())
    data = {key: value for key, value in base.items() if key != drop}
    return NonEmptyMap.of_mapping(data)


def _with_extra_branch_label(node: EndpointBranch, name: str) -> EndpointBranch:
    """External alt that accepts one extra label at the root."""
    return EndpointBranch(node.sender, _map_plus(node.branches, name))


def _without_one_branch_label(node: EndpointBranch) -> EndpointBranch | None:
    """External alt that drops one root label, or None if only one remains."""
    reduced = _map_minus(node.branches)
    if reduced is None:
        return None
    return EndpointBranch(node.sender, reduced)


def _with_extra_select_label(node: EndpointSelect, name: str) -> EndpointSelect:
    """Internal alt that may send one extra label at the root."""
    return EndpointSelect(node.receiver, _map_plus(node.branches, name))


def _without_one_select_label(node: EndpointSelect) -> EndpointSelect | None:
    """Internal alt that drops one root label, or None if only one remains."""
    reduced = _map_minus(node.branches)
    if reduced is None:
        return None
    return EndpointSelect(node.receiver, reduced)


@given(triple=strategies.projected_endpoints())
def test_l1_reflexive(triple: tuple[SessionType, Role, EndpointType]) -> None:
    """subtype(t, t) for any closed projection."""
    _, _, local = triple
    assert free_vars(local) == frozenset()
    assert subtype(local, local)


@given(
    st.sampled_from(_ENDPOINTS),
    st.sampled_from(_ENDPOINTS),
    st.sampled_from(_ENDPOINTS),
)
def test_l2_transitive(a: EndpointType, b: EndpointType, c: EndpointType) -> None:
    """a ≤ b ∧ b ≤ c ⟹ a ≤ c on the fixed local set."""
    if subtype(a, b) and subtype(b, c):
        assert subtype(a, c)


@given(triple=strategies.projected_endpoints())
def test_l3_association_identity(
    triple: tuple[SessionType, Role, EndpointType],
) -> None:
    """associate(projection, G, r) and associate(None, G, r) equal the projection."""
    proto, role, projected = triple
    assert associate(projected, proto, role) == projected
    assert associate(None, proto, role) == projected


@given(triple=strategies.projected_endpoints())
def test_l4_branch_widen_is_subtype(
    triple: tuple[SessionType, Role, EndpointType],
) -> None:
    """Adding a fresh external label yields a subtype; removing one does not."""
    _, _, local = triple
    if not isinstance(local, EndpointBranch):
        return
    wider = _with_extra_branch_label(local, '__extra__')
    assert subtype(wider, local)
    assert not subtype(local, wider)
    narrower = _without_one_branch_label(local)
    if narrower is not None:
        assert not subtype(narrower, local)
        assert subtype(local, narrower)


@given(triple=strategies.projected_endpoints())
def test_l5_select_narrow_is_subtype(
    triple: tuple[SessionType, Role, EndpointType],
) -> None:
    """Dropping an internal label yields a subtype; adding one does not."""
    _, _, local = triple
    if not isinstance(local, EndpointSelect):
        return
    wider = _with_extra_select_label(local, '__extra__')
    assert not subtype(wider, local)
    assert subtype(local, wider)
    narrower = _without_one_select_label(local)
    if narrower is not None:
        assert subtype(narrower, local)
        assert not subtype(local, narrower)


@given(triple=strategies.projected_endpoints())
def test_l6_unfold_equivalent(
    triple: tuple[SessionType, Role, EndpointType],
) -> None:
    """subtype(unfold(t), t) and subtype(t, unfold(t)) for recursive locals."""
    _, _, local = triple
    if not isinstance(local, EndpointRec):
        return
    opened = unfold(local)
    assert subtype(opened, local)
    assert subtype(local, opened)


def test_l7_peer_is_fixed() -> None:
    """Same labels, different sender ⇒ not a subtype."""
    from_a = offer(A, case('Hi', Text)).close()
    from_b = offer(B, case('Hi', Text)).close()
    assert not subtype(from_a, from_b)
    assert not subtype(from_b, from_a)


def test_l8_payload_by_name() -> None:
    """Distinct list_of(Text) objects agree by name; Text vs Integer do not."""
    left = recv(A, 'Items', list_of(Text)).close()
    right = recv(A, 'Items', list_of(Text)).close()
    assert left != right  # codec identity is not structural
    assert subtype(left, right)
    assert subtype(right, left)
    text = recv(A, 'N', Text).close()
    integer = recv(A, 'N', Integer).close()
    assert not subtype(text, integer)
    assert not subtype(integer, text)


def test_l9_terminates_on_multi_unfold() -> None:
    """subtype(t, unfold(unfold(t))) finishes and holds for a recursive t."""
    loop = endpoint_rec(
        't',
        offer(A, case('Again') >> endpoint_var('t'), case('Done')),
    ).close()
    assert isinstance(loop, EndpointRec)
    twice = unfold(unfold(loop))
    assert subtype(loop, twice)
    assert subtype(twice, loop)


def test_l10_conformance_error_names_missing_label() -> None:
    """Machine with a truncated receive raises ConformanceError naming the label."""
    from agentsparty.machine import View

    proto = alt[A, B](case('Ok', Text), case('No', Text)).close()
    # B's projection is EndpointBranch(A, {Ok, No}); declare only Ok.
    truncated = recv(A, 'Ok', Text).close()

    def decide(_view: View) -> Choice:
        return Choice(Label('Ok'), 'x')

    with pytest.raises(ConformanceError, match='No') as caught:
        Machine(B, proto, decide, declares=truncated)
    message = str(caught.value)
    assert 'B' in message
    assert 'No' in message
