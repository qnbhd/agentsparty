"""Spent monoid, Allowance covers, step/unfolding limits."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.journal.memory import MemoryJournal
from agentsparty.kernel.budget import (
    NOTHING_SPENT,
    UNBOUNDED,
    Allowance,
    Spent,
)
from agentsparty.kernel.errors import StepLimitError
from agentsparty.kernel.role import roles
from agentsparty.participant import Choice
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.runtime import AgentRuntime
from tests.conftest import Stub


@st.composite
def spends(draw: st.DrawFn) -> Spent:
    return Spent(
        unfoldings=draw(st.integers(0, 20)),
        steps=draw(st.integers(0, 20)),
    )


@given(a=spends(), b=spends(), c=spends())
def test_spent_is_a_commutative_monoid(a: Spent, b: Spent, c: Spent) -> None:
    assert a + b == b + a
    assert (a + b) + c == a + (b + c)
    assert a + NOTHING_SPENT == a


@given(
    a=spends(),
    b=spends(),
    unfoldings=st.one_of(st.none(), st.integers(0, 40)),
    steps=st.one_of(st.none(), st.integers(0, 40)),
)
def test_covers_is_monotone(
    a: Spent,
    b: Spent,
    unfoldings: int | None,
    steps: int | None,
) -> None:
    allowance = Allowance(unfoldings=unfoldings, steps=steps)
    if allowance.covers(a + b):
        assert allowance.covers(a)


@given(s=spends())
def test_unbounded_covers_everything(s: Spent) -> None:
    assert UNBOUNDED.covers(s)


def test_negative_allowance_is_rejected() -> None:
    with pytest.raises(ValueError, match='unfoldings'):
        Allowance(unfoldings=-1)
    with pytest.raises(ValueError, match='steps'):
        Allowance(steps=-1)


async def test_step_allowance_stops_a_run() -> None:
    """A 3-step protocol with Allowance(steps=2) raises StepLimitError."""
    A, B = roles('A', 'B')
    proto = (msg[A, B]('One', Text) >> msg[B, A]('Two', Text) >> msg[A, B]('Three', Text)).close()
    a = Stub(
        A,
        project(proto, A),
        alts=[Choice(Label('One'), '1'), Choice(Label('Three'), '3')],
    )
    b = Stub(B, project(proto, B), alts=[Choice(Label('Two'), '2')])
    rt = AgentRuntime(proto, [a, b], allowance=Allowance(steps=2))
    with pytest.raises(StepLimitError):
        await rt.run()
    assert len(rt.trace) == 2


async def test_replayed_steps_are_free() -> None:
    """A journal with 3 decisions finishes under Allowance(steps=0)."""
    A, B = roles('A', 'B')
    proto = (msg[A, B]('One', Text) >> msg[B, A]('Two', Text) >> msg[A, B]('Three', Text)).close()
    journal = MemoryJournal()
    a = Stub(
        A,
        project(proto, A),
        alts=[Choice(Label('One'), '1'), Choice(Label('Three'), '3')],
    )
    b = Stub(B, project(proto, B), alts=[Choice(Label('Two'), '2')])
    await AgentRuntime(proto, [a, b], journal=journal).run()
    assert journal.script().length == 3

    a2 = Stub(A, project(proto, A))
    b2 = Stub(B, project(proto, B))
    rt = AgentRuntime(
        proto,
        [a2, b2],
        journal=MemoryJournal(journal.script().decisions),
        allowance=Allowance(steps=0),
    )
    trace = await rt.run()
    assert len(trace) == 3
