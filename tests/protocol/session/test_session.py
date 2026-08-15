"""Session nodes, operators, and laws L1-L6 (plan 0007)."""

from __future__ import annotations

from typing import cast

import pytest
from hypothesis import assume, given

from agentsparty.kernel.errors import ProjectionError
from agentsparty.kernel.role import Role, roles
from agentsparty.protocol import (
    Text,
    alt,
    case,
    list_of,
    msg,
    owning,
    project_onto,
    render,
)
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.protocol.session import (
    Interaction,
    SendTo,
    SessionEnd,
    SessionType,
    SingleSubject,
    as_endpoint,
    as_global,
    as_session,
    assert_wellformed,
    epart,
    equal_session,
    free_vars,
    ipart,
    localise,
    unfold,
)
from agentsparty.protocol.session._equivalence import _merge_view
from tests.protocol import strategies
from tests.protocol.fixtures import strategy_component

# Company roles from research/03.md Ex. 3.5
d, ad, s, w, f1, f2 = roles('d', 'ad', 's', 'w', 'f1', 'f2')


def test_ipart_epart_company_h_str() -> None:
    h = strategy_component(d, ad, s, f1)
    assert ipart(h) == frozenset({d, ad})
    assert epart(h) == frozenset({s, f1})


def test_wellformed_rejects_role_in_both_parts() -> None:
    """A SendTo that later treats the external peer as internal is ill-formed."""
    A, B = roles('A', 'B')
    from agentsparty.protocol.language.core import Label, branches_map
    from agentsparty.protocol.session import SessionBranchCase

    bad = SendTo(
        A,
        B,
        branches_map(
            [
                SessionBranchCase(
                    Label('x'),
                    Text,
                    Interaction(
                        B,
                        A,
                        branches_map([SessionBranchCase(Label('y'), Text, SessionEnd())]),
                    ),
                ),
            ],
        ),
    )
    with pytest.raises(ValueError, match='internal and external'):
        assert_wellformed(bad)


def test_as_global_rejects_component() -> None:
    with pytest.raises(ValueError, match='compose'):
        as_global(strategy_component(d, ad, s, f1))


def test_as_global_accepts_closed_choreography() -> None:
    A, B = roles('A', 'B')
    assert as_global(msg[A, B]('Hi', Text).close()) == msg[A, B]('Hi', Text).close()


def test_render_send_recv_notation() -> None:
    Planner, Retriever, Writer = roles('Planner', 'Retriever', 'Writer')
    component = owning(Retriever).defining(
        msg[Planner, Retriever]('Query', Text) >> msg[Retriever, Writer]('Passages', list_of(Text)),
    )
    text = render(component)
    assert 'Planner?Retriever : Query(str)' in text
    assert 'Retriever!Writer : Passages(list[str])' in text


def test_free_vars_and_unfold_on_session_with_interface() -> None:
    h = strategy_component(d, ad, s, f1)
    assert free_vars(h) == frozenset()
    # unfold is a no-op on non-Rec roots
    assert unfold(h) is h or equal_session(unfold(h), h)


@given(data=strategies.role_subsets())
def test_l1_projection_functoriality(
    data: tuple[SessionType, frozenset[Role], frozenset[Role]],
) -> None:
    proto, e1, e2 = data
    try:
        mid = project_onto(proto, e1)
        left = project_onto(mid, e2)
        right = project_onto(proto, e2)
    except ProjectionError:
        assume(condition=False)
    assert equal_session(left, right)


@given(data=strategies.role_subsets())
def test_l2_ipart_of_projection_subseteq_focus(
    data: tuple[SessionType, frozenset[Role], frozenset[Role]],
) -> None:
    proto, e1, _e2 = data
    try:
        projected = project_onto(proto, e1)
    except ProjectionError:
        assume(condition=False)
    assert ipart(projected) <= e1
    # singleton focus → as_endpoint is total
    if len(e1) == 1:
        (role,) = e1
        as_endpoint(cast(SingleSubject, project_onto(proto, frozenset({role}))))


@given(triple=strategies.projected_endpoints())
def test_l4_as_endpoint_as_session_roundtrip(
    triple: tuple[SessionType, Role, EndpointType],
) -> None:
    proto, subject, local = triple
    assert as_endpoint(cast(SingleSubject, as_session(subject, local))) == local
    view = project_onto(proto, frozenset({subject}))
    assert equal_session(
        as_session(subject, as_endpoint(cast(SingleSubject, view))),
        view,
    )


def test_l5_localiser_widens_send_merge_view_refuses() -> None:
    """loc (p→q:{ℓ₁.p!r;ℓ₃, ℓ₂.p!r;ℓ₄}) == p!r;{ℓ₃, ℓ₄}; ⊔ on the sends raises."""
    p, q, r = roles('p', 'q', 'r')
    # internal alt then different external labels
    node = owning(p, q).defining(
        alt[p, q](
            case('l1') >> msg[p, r]('l3'),
            case('l2') >> msg[p, r]('l4'),
        ),
    )
    interface = localise(node)
    assert isinstance(interface, SendTo)
    assert interface.sender == p
    assert interface.receiver == r
    from agentsparty.protocol.language.core import Label

    assert set(interface.branches.keys()) == {Label('l3'), Label('l4')}
    # The two SendTo futures under an observer merge (⊔) must refuse different labels
    left = owning(p).defining(msg[p, r]('l3'))
    right = owning(p).defining(msg[p, r]('l4'))
    with pytest.raises(ProjectionError):
        _merge_view(left, right)


def test_l6_localise_idempotent_on_components() -> None:
    Planner, Retriever, Ranker, Writer = roles(
        'Planner',
        'Retriever',
        'Ranker',
        'Writer',
    )
    components = [
        strategy_component(d, ad, s, f1),
        owning(Retriever, Ranker).defining(
            msg[Planner, Retriever]('Query', Text)
            >> msg[Retriever, Ranker]('Candidates', list_of(Text))
            >> msg[Retriever, Writer]('Passages', list_of(Text)),
        ),
    ]
    for h in components:
        once = localise(h)
        assert equal_session(localise(once), once)


@given(p=strategies.linear_protocols())
def test_l6_localise_idempotent_on_globals(p: SessionType) -> None:
    # pure global → localise drops everything to end (or merges to end)
    once = localise(p)
    assert equal_session(localise(once), once)
