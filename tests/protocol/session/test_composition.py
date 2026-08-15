"""Composition, Equation C, and laws L7-L9 (plan 0007)."""

from __future__ import annotations

import pytest

from agentsparty.kernel.errors import CompositionError
from agentsparty.kernel.role import roles
from agentsparty.protocol import (
    Integer,
    Nothing,
    Text,
    alt,
    case,
    compose,
    list_of,
    localise,
    msg,
    owning,
    project_onto,
    rec,
    stop,
    var,
)
from agentsparty.protocol.session import (
    as_global,
    assert_compatible,
    equal_session,
    ipart,
)
from tests.protocol.fixtures import strategy_component

d, ad, s, w, f1, f2 = roles('d', 'ad', 's', 'w', 'f1', 'f2')
Planner, Retriever, Ranker, Writer, Checker = roles(
    'Planner',
    'Retriever',
    'Ranker',
    'Writer',
    'Checker',
)


def _parallel_h1(p, q, r):
    return owning(p, q).defining(
        msg[p, r]('ell', Text)
        >> rec(
            'X',
            alt[p, q](
                case('ell1', Text) >> var('X'),
                case('ell2', Nothing) >> stop,
            ),
        ),
    )


def _parallel_h2(p, r, s):
    return owning(r, s).defining(
        msg[p, r]('ell', Text)
        >> rec(
            'Y',
            alt[r, s](
                case('ell3', Text) >> var('Y'),
                case('ell4', Nothing) >> stop,
            ),
        ),
    )


def _h_sales():
    return owning(s, w).defining(
        msg[d, s]('prod', Integer)
        >> rec(
            'X',
            alt[f1, s](
                case('price', Integer) >> msg[s, w]('publish', Integer),
                case('wait', Nothing) >> msg[s, w]('wait', Nothing) >> var('X'),
            ),
        ),
    )


def _h_fin():
    return owning(f1, f2).defining(
        msg[d, f1]('prod', Integer)
        >> msg[f1, f2]('prod', Integer)
        >> rec(
            'X',
            alt[f2, f1](
                case('price', Integer) >> msg[f1, d]('ok', Nothing) >> msg[f1, s]('price', Integer),
                case('wait', Nothing)
                >> msg[f1, d]('wait', Nothing)
                >> msg[f1, s]('wait', Nothing)
                >> var('X'),
            ),
        ),
    )


def _g_dagger():
    """Compatibility type G† (paper §2 / Ex. 4.5)."""
    return (
        msg[d, s]('prod', Integer)
        >> msg[d, f1]('prod', Integer)
        >> rec(
            'X',
            alt[f1, d](
                case('ok', Nothing) >> msg[f1, s]('price', Integer),
                case('wait', Nothing) >> msg[f1, s]('wait', Nothing) >> var('X'),
            ),
        )
    ).close()


def _search():
    return owning(Retriever, Ranker).defining(
        msg[Planner, Retriever]('Query', Text)
        >> msg[Retriever, Ranker]('Candidates', list_of(Text))
        >> msg[Ranker, Retriever]('Ranked', list_of(Text))
        >> msg[Retriever, Writer]('Passages', list_of(Text)),
    )


def _answer():
    return owning(Writer, Checker).defining(
        msg[Retriever, Writer]('Passages', list_of(Text))
        >> msg[Writer, Checker]('Draft', Text)
        >> msg[Checker, Writer]('Verdict', Text)
        >> msg[Writer, Planner]('Answer', Text),
    )


def _contract():
    return (
        msg[Planner, Retriever]('Query', Text)
        >> msg[Retriever, Writer]('Passages', list_of(Text))
        >> msg[Writer, Planner]('Answer', Text)
    ).close()


def test_compatible_h_str_against_g_dagger() -> None:
    """Ex. 4.5: loc H_str == G† ↾ {d, ad}."""
    h = strategy_component(d, ad, s, f1)
    g = _g_dagger()
    assert equal_session(localise(h), project_onto(g, frozenset({d, ad})))
    assert_compatible(g, h)


def test_incompatible_component_raises_with_trail() -> None:
    """Broken search: renamed exit label → CompositionError with path."""
    broken = owning(Retriever, Ranker).defining(
        msg[Planner, Retriever]('Query', Text)
        >> msg[Retriever, Ranker]('Candidates', list_of(Text))
        >> msg[Ranker, Retriever]('Ranked', list_of(Text))
        >> msg[Retriever, Writer]('WRONG', list_of(Text)),
    )
    with pytest.raises(CompositionError, match='incompatible') as exc:
        assert_compatible(_contract(), broken)
    assert 'Passages' in str(exc.value) or 'WRONG' in str(exc.value) or 'labels' in str(exc.value)


def test_l7_l8_search_answer_compose() -> None:
    search, answer, contract = _search(), _answer(), _contract()
    composed = compose(contract, [search, answer])
    as_global(composed)
    # Thm. 4.7: projection onto component roles recovers the component
    assert equal_session(project_onto(composed, ipart(search)), search)
    assert equal_session(project_onto(composed, ipart(answer)), answer)
    # Cor. 4.10 per role (payload identity is codec *name*, not object ==)
    for role in ipart(search):
        assert equal_session(
            project_onto(composed, frozenset({role})),
            project_onto(search, frozenset({role})),
        )
    for role in ipart(answer):
        assert equal_session(
            project_onto(composed, frozenset({role})),
            project_onto(answer, frozenset({role})),
        )
    # Planner served by the contract (Cor. 5.1)
    assert equal_session(
        project_onto(composed, frozenset({Planner})),
        project_onto(contract, frozenset({Planner})),
    )


def test_l7_company_compose() -> None:
    h_str = strategy_component(d, ad, s, f1)
    h_sales = _h_sales()
    h_fin = _h_fin()
    g_dagger = _g_dagger()
    composed = compose(g_dagger, [h_str, h_sales, h_fin])
    as_global(composed)
    assert equal_session(project_onto(composed, frozenset({d, ad})), h_str)
    assert equal_session(project_onto(composed, frozenset({s, w})), h_sales)
    assert equal_session(project_onto(composed, frozenset({f1, f2})), h_fin)
    for role in (d, ad):
        assert equal_session(
            project_onto(composed, frozenset({role})),
            project_onto(h_str, frozenset({role})),
        )
    for role in (s, w):
        assert equal_session(
            project_onto(composed, frozenset({role})),
            project_onto(h_sales, frozenset({role})),
        )
    for role in (f1, f2):
        assert equal_session(
            project_onto(composed, frozenset({role})),
            project_onto(h_fin, frozenset({role})),
        )


def test_l9a_incompatible_component_composition_error() -> None:
    broken = owning(Retriever).defining(
        msg[Planner, Retriever]('Query', Text) >> msg[Retriever, Writer]('WRONG', list_of(Text)),
    )
    with pytest.raises(CompositionError):
        compose(_contract(), [broken, _answer()])


def test_l9b_closed_mu_contract_no_shared_roles_parallel() -> None:
    """Two closed recursive remainders compose via parallel (Fig. 5 / §5.1)."""
    p, q, r, s = roles('p', 'q', 'r', 's')
    h1 = _parallel_h1(p, q, r)
    h2 = _parallel_h2(p, r, s)
    contract = msg[p, r]('ell', Text).close()
    composed = compose(contract, [h1, h2])
    from agentsparty.protocol import render

    assert 'par {' in render(composed)


def test_l9c_as_global_on_component() -> None:
    with pytest.raises(ValueError, match='compose'):
        as_global(_search())


def test_ex_4_2_build_back_one() -> None:
    """B¹(p→q:ℓ₀. s→p:ℓ₂. end)(s→r:ℓ₁. s!p;ℓ₂. end) == p→q:ℓ₀. s→r:ℓ₁. s→p:ℓ₂. end."""
    p, q, r, s_role = roles('p', 'q', 'r', 's')
    contract = (msg[p, q]('l0') >> msg[s_role, p]('l2')).close()
    component = owning(s_role, r).defining(
        msg[s_role, r]('l1') >> msg[s_role, p]('l2'),
    )
    # component's interface is s!p;l2 — contract ↾ {s,r} should match
    # For Ex. 4.2, focus = {s, r}; contract projection onto {s,r}:
    # p→q not touching focus → merge cont = s→p:l2 → becomes s?p? wait
    # s is sender of s→p so becomes s!p. And p,q not in focus for first msg.
    # Actually first msg p→q: both not in {s,r} → skip → cont s→p → s in focus, p not
    # → SendTo(s,p). localise(component) = s!p after dropping s→r.
    expected = (msg[p, q]('l0') >> msg[s_role, r]('l1') >> msg[s_role, p]('l2')).close()
    composed = compose(contract, [component])
    assert equal_session(composed, expected)


def test_compose_empty_components_is_contract() -> None:
    contract = _contract()
    assert equal_session(compose(contract, []), contract)


def test_g_par_paper_vector() -> None:
    """G_par from research/03.md §5.1 — compose introduces parallel."""
    p, q, r, s = roles('p', 'q', 'r', 's')
    # H¹_par = p!r;l. μX.p→q:{l₁.X, l₂.end}
    h1 = _parallel_h1(p, q, r)
    # H²_par = p?r;l. μY.r→s:{l₃.Y, l₄.end}
    h2 = _parallel_h2(p, r, s)
    # G†_par = p→r:l.end
    contract = msg[p, r]('ell', Text).close()

    assert_compatible(contract, h1)
    assert_compatible(contract, h2)
    g_par = compose(contract, [h1, h2])
    from agentsparty.protocol import render

    text = render(g_par)
    assert 'par {' in text
    # Thm. 4.4 / Cor. 4.10 through parallel
    assert equal_session(
        project_onto(g_par, frozenset({q})),
        project_onto(h1, frozenset({q})),
    )
    assert equal_session(
        project_onto(g_par, frozenset({s})),
        project_onto(h2, frozenset({s})),
    )


def test_loc_rec_totalisation() -> None:
    """Closed loop with no external interface localises to end."""
    p, q, r = roles('p', 'q', 'r')
    h1 = _parallel_h1(p, q, r)
    # loc H¹_par = p!r;l.end
    interface = localise(h1)
    expected = owning(p).defining(msg[p, r]('ell', Text))
    assert equal_session(interface, expected)
