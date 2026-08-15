"""Characterizing tests for ``agentsparty.protocol.language.endpoint``.

Endpoint DSL correctness is a small set of laws: sugar identities (send/recv),
structure preservation (select/offer), and stop.  Projection duals live in
``test_common``.  ``_bodies`` / ``case`` / ``Label`` contracts live in
``test_core``.
"""

from __future__ import annotations

import inspect
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Case, Codec, Text, case
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointEnd,
    EndpointSelect,
    EndpointType,
    free_vars,
    offer,
    rec,
    recv,
    select,
    send,
    stop,
    unfold,
    var,
)
from tests.protocol import strategies


def test_stop_closes_to_endpoint_end() -> None:
    assert stop.close() == EndpointEnd()


@given(
    receiver=strategies.ROLE,
    label=st.sampled_from(strategies.LABEL_NAMES),
    codec=st.one_of(st.none(), strategies.CODE),
)
def test_send_is_single_case_select(
    receiver: Role,
    label: str,
    codec: Codec[Any] | None,
) -> None:
    """send(r, L, T) ≡ select(r, case(L, T)); default T is Text."""
    if codec is None:
        assert send(receiver, label).close() == select(receiver, case(label, Text)).close()
    else:
        assert send(receiver, label, codec).close() == select(receiver, case(label, codec)).close()


@given(
    sender=strategies.ROLE,
    label=st.sampled_from(strategies.LABEL_NAMES),
    codec=st.one_of(st.none(), strategies.CODE),
)
def test_recv_is_single_case_offer(
    sender: Role,
    label: str,
    codec: Codec[Any] | None,
) -> None:
    """recv(s, L, T) ≡ offer(s, case(L, T)); default T is Text."""
    if codec is None:
        assert recv(sender, label).close() == offer(sender, case(label, Text)).close()
    else:
        assert recv(sender, label, codec).close() == offer(sender, case(label, codec)).close()


@st.composite
def _endpoint_cases(
    draw: st.DrawFn,
) -> tuple[Role, tuple[Case[EndpointType], ...]]:
    """1-3 cases, some with a linear local body (send or stop)."""
    peer = draw(strategies.ROLE)
    count = draw(st.integers(1, 3))
    names, codecs = strategies._case_inputs(draw, count)
    cases: list[Case[EndpointType]] = []
    for name, codec in zip(names, codecs, strict=True):
        alternative: Case[EndpointType] = case(name, codec)
        if draw(st.booleans()):
            if draw(st.booleans()):
                body_peer = draw(strategies.ROLE)
                body_label = draw(st.sampled_from(strategies.LABEL_NAMES))
                body_codec = draw(strategies.CODE)
                alternative >>= send(body_peer, body_label, body_codec)
            else:
                alternative >>= stop
        cases.append(alternative)
    return peer, tuple(cases)


@given(inputs=_endpoint_cases())
def test_select_preserves_structure(
    inputs: tuple[Role, tuple[Case[EndpointType], ...]],
) -> None:
    """Filling a select preserves its receiver, cases, and continuation."""
    receiver, cases = inputs
    tail = send(receiver, 'tail', Text).close()
    proto = select(receiver, *cases).fill(tail)

    assert isinstance(proto, EndpointSelect)
    assert proto.receiver == receiver
    assert set(proto.branches) == {c.label for c in cases}

    strategies.assert_filled_branches(proto, cases, tail)


@given(inputs=_endpoint_cases())
def test_offer_preserves_structure(
    inputs: tuple[Role, tuple[Case[EndpointType], ...]],
) -> None:
    """Offer and select preserve the same branches with opposite direction."""
    sender, cases = inputs
    tail = send(sender, 'tail', Text).close()
    proto = offer(sender, *cases).fill(tail)
    dual = select(sender, *cases).fill(tail)

    assert isinstance(proto, EndpointBranch)
    assert isinstance(dual, EndpointSelect)
    assert proto.sender == sender
    assert proto.branches == dual.branches


def test_select_and_offer_require_a_first_case() -> None:
    """The first case is required by both constructor signatures."""
    assert inspect.signature(select).parameters['first'].default is inspect.Parameter.empty
    assert inspect.signature(offer).parameters['first'].default is inspect.Parameter.empty


def test_endpoint_rec_closes_and_unfolds() -> None:
    """A recursive endpoint type is closed; unfold substitutes the binder."""
    peer = strategies.A
    loop = rec(
        'loop',
        offer(peer, case('Again') >> var('loop'), case('Done')),
    ).close()
    assert free_vars(loop) == frozenset()
    opened = unfold(loop)
    assert free_vars(opened) == frozenset()
    assert isinstance(opened, EndpointBranch)
    again = opened.branches[case('Again').label]
    assert again.continuation == loop
