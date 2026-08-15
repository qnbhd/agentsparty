"""Characterizing tests for ``agentsparty.protocol.session``.

Correctness is a small set of laws — not a pile of scenarios.
Fragment monoid lives in ``test_core``; projection lives in ``test_common``.
``_bodies`` / ``case`` / ``Label`` contracts live in ``test_core``.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.role import Role, roles
from agentsparty.protocol.language.core import Case, Codec, Text, case
from agentsparty.protocol.session import (
    Interaction,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
    alt,
    assert_wellformed,
    free_vars,
    msg,
    rec,
    stop,
    unfold,
    var,
)
from tests.protocol import strategies


def test_alt_rejects_self_talk() -> None:
    """sender == receiver is not a well-formed interaction."""
    A, _ = roles('A', 'B')
    with pytest.raises(ValueError, match='cannot talk to itself'):
        alt[A, A](case('ping'))


def test_alt_requires_a_first_case() -> None:
    """The first case is required by the subscripted syntax."""
    A, B = roles('A', 'B')
    with pytest.raises(TypeError):
        alt[A, B]()


def test_stop_closes_to_global_end() -> None:
    assert stop.close() == SessionEnd()


@given(
    pair=strategies.role_pair(),
    label=st.sampled_from(strategies.LABEL_NAMES),
    codec=st.one_of(st.none(), strategies.CODE),
)
def test_msg_is_single_case_alt(
    pair: tuple[Role, Role],
    label: str,
    codec: Codec[Any] | None,
) -> None:
    """msg[s, r]( L, T) ≡ alt[s, r]( case(L, T)); default T is Text."""
    sender, receiver = pair
    if codec is None:
        assert (
            msg[sender, receiver](label).close() == alt[sender, receiver](case(label, Text)).close()
        )
    else:
        assert (
            msg[sender, receiver](label, codec).close()
            == alt[sender, receiver](case(label, codec)).close()
        )


@st.composite
def _alt_inputs(
    draw: st.DrawFn,
) -> tuple[Role, Role, list[Case[SessionType]]]:
    """Distinct roles + 1-3 cases, some with a linear body."""
    sender, receiver = draw(strategies.role_pair())
    count = draw(st.integers(1, 3))
    names, codecs = strategies._case_inputs(draw, count)
    cases: list[Case[SessionType]] = []
    for name, codec in zip(names, codecs, strict=True):
        alternative: Case[SessionType] = case(name, codec)
        if draw(st.booleans()):
            # body is a closed-able global fragment (msg or stop)
            if draw(st.booleans()):
                body_pair = draw(strategies.role_pair())
                body_label = draw(st.sampled_from(strategies.LABEL_NAMES))
                body_codec = draw(strategies.CODE)
                alternative >>= msg[body_pair[0], body_pair[1]](
                    body_label,
                    body_codec,
                )
            else:
                alternative >>= stop
        cases.append(alternative)
    return sender, receiver, cases


@given(inputs=_alt_inputs())
def test_alt_preserves_structure(
    inputs: tuple[Role, Role, list[Case[SessionType]]],
) -> None:
    """Filling a alt preserves its roles, cases, and continuation.

    For each arm, continuation is body.fill(tail) if body else tail.
    """
    sender, receiver, cases = inputs
    tail = msg[receiver, sender]('tail', Text).close()
    proto = alt[sender, receiver](*cases).fill(tail)

    assert isinstance(proto, Interaction)
    assert proto.sender == sender
    assert proto.receiver == receiver
    assert set(proto.branches) == {c.label for c in cases}

    strategies.assert_filled_branches(proto, cases, tail)


def test_var_absorbs_sequential_tail() -> None:
    """Law 1: var(n) is left-zero for sequencing after it."""
    A, B = roles('A', 'B')
    assert (var('t') >> msg[A, B]('x')).close() == SessionVar('t')


def test_rec_exit_path_sees_sequential_rest() -> None:
    """Law 2: rec(n, body) >> rest fills body's sequential hole on exit paths."""
    from agentsparty.protocol.language.core import Label

    A, B = roles('A', 'B')
    rest = msg[B, A]('bye')
    proto = (
        rec(
            't',
            alt[A, B](
                case('loop') >> var('t'),
                case('done'),
            ),
        )
        >> rest
    ).close()
    assert isinstance(proto, SessionRec)
    assert proto.name == 't'
    body = proto.body
    assert isinstance(body, Interaction)
    assert body.branches[Label('done')].continuation == rest.close()
    assert body.branches[Label('loop')].continuation == SessionVar('t')


def test_rec_unguarded_raises_at_close() -> None:
    with pytest.raises(ValueError, match='unguarded'):
        rec('t', var('t')).close()


def test_rec_capture_guard_rejects_free_var_in_tail() -> None:
    A, B = roles('A', 'B')
    with pytest.raises(ValueError, match='captured'):
        (rec('t', msg[A, B]('x')) >> var('t')).close()


def test_assert_wellformed_rejects_unguarded_raw() -> None:
    with pytest.raises(ValueError, match='unguarded'):
        assert_wellformed(SessionRec('t', SessionVar('t')))


def test_assert_wellformed_rejects_open() -> None:
    with pytest.raises(ValueError, match='free recursion variable'):
        assert_wellformed(SessionVar('t'))


def test_assert_wellformed_accepts_guarded_ping_pong() -> None:
    A, B = roles('A', 'B')
    proto = rec(
        't',
        alt[A, B](case('ping') >> var('t'), case('done')),
    ).close()
    assert_wellformed(proto)
    assert free_vars(proto) == frozenset()


def test_assert_wellformed_accepts_shadowing() -> None:
    """Nested binders may shadow: μt. μt. A→B:ping().t is guarded and closed."""
    A, B = roles('A', 'B')
    inner = rec('t', msg[A, B]('ping') >> var('t'))
    outer = rec('t', inner).close()
    assert_wellformed(outer)


def test_unfold_substitutes_only_free_occurrences() -> None:
    """Shadowing-aware: inner binder of the same name is left untouched."""
    from agentsparty.protocol.language.core import Label, Nothing, branches_map
    from agentsparty.protocol.session import SessionBranchCase

    A, B = roles('A', 'B')
    inner = SessionRec(
        't',
        Interaction(
            A,
            B,
            branches_map([SessionBranchCase(Label('inner'), Nothing, SessionVar('t'))]),
        ),
    )
    outer = SessionRec(
        't',
        Interaction(
            A,
            B,
            branches_map(
                [
                    SessionBranchCase(Label('back'), Nothing, SessionVar('t')),
                    SessionBranchCase(Label('nest'), Nothing, inner),
                ],
            ),
        ),
    )
    assert_wellformed(outer)
    stepped = unfold(outer)
    assert isinstance(stepped, Interaction)
    assert stepped.branches[Label('back')].continuation == outer
    nested = stepped.branches[Label('nest')].continuation
    assert nested == inner
    assert isinstance(nested, SessionRec)
    assert isinstance(nested.body, Interaction)
    assert nested.body.branches[Label('inner')].continuation == SessionVar('t')
