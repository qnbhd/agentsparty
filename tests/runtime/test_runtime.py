"""AgentRuntime binding, recursive loops, and assert_never path coverage."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.budget import DEFAULT_UNFOLDINGS, UNBOUNDED, Allowance
from agentsparty.kernel.errors import RecursionLimitError
from agentsparty.kernel.role import roles
from agentsparty.participant import Choice
from agentsparty.protocol import Label, Text, alt, case, msg, project, rec, var
from agentsparty.protocol.session import SessionRec, SessionType, SessionVar
from agentsparty.runtime import AgentRuntime
from tests._helpers import loop_protocol
from tests.conftest import Stub


async def test_simple_run() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b])
    trace = await rt.run()
    assert len(trace) == 1
    assert trace[0].payload == 'yo'
    assert b.received[0].payload == 'yo'


def test_unexpected_role() -> None:
    A, B, C = roles('A', 'B', 'C')
    proto = msg[A, B]('Hi').close()
    with pytest.raises(ValueError, match='unexpected'):
        AgentRuntime(
            proto,
            [
                Stub(A, project(proto, A)),
                Stub(B, project(proto, B)),
                Stub(C, project(proto, A)),
            ],
        )


def test_runtime_rejects_unguarded_at_init() -> None:
    with pytest.raises(ValueError, match='unguarded'):
        AgentRuntime(SessionRec('t', SessionVar('t')), [])


@given(i=st.integers(min_value=0, max_value=20))
async def test_scripted_retry_trace_labels(i: int) -> None:
    """Direct oracle: i loop alts then done yields [loop]*i + [done]."""
    A, B = roles('A', 'B')
    proto = loop_protocol()
    script = [Choice(Label('loop'), None) for _ in range(i)] + [
        Choice(Label('done'), None),
    ]
    a = Stub(A, project(proto, A), alts=script)
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b])
    trace = await rt.run()
    assert [envelope.label.name for envelope in trace] == ['loop'] * i + ['done']


async def test_deep_loop_completes_with_recursion_budget_none() -> None:
    """~500 iterations pin the iterative stepper with explicit unbounded opt-in."""
    A, B = roles('A', 'B')
    proto = loop_protocol()
    n = 500
    script = [Choice(Label('loop'), None) for _ in range(n)] + [
        Choice(Label('done'), None),
    ]
    a = Stub(A, project(proto, A), alts=script)
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], allowance=UNBOUNDED)
    trace = await rt.run()
    assert len(trace) == n + 1
    assert [envelope.label.name for envelope in trace] == ['loop'] * n + ['done']


@given(i=st.integers(min_value=0, max_value=20))
async def test_recursion_budget_exact_threshold(i: int) -> None:
    """Budget i+1 delivers [loop]*i+[done]; budget i fails after [loop]*i."""
    A, B = roles('A', 'B')
    proto = loop_protocol()
    script = [Choice(Label('loop'), None) for _ in range(i)] + [
        Choice(Label('done'), None),
    ]

    a = Stub(A, project(proto, A), alts=list(script))
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], allowance=Allowance(unfoldings=i + 1))
    trace = await rt.run()
    assert [envelope.label.name for envelope in trace] == ['loop'] * i + ['done']

    a2 = Stub(A, project(proto, A), alts=list(script))
    b2 = Stub(B, project(proto, B))
    rt2 = AgentRuntime(proto, [a2, b2], allowance=Allowance(unfoldings=i))
    with pytest.raises(RecursionLimitError):
        await rt2.run()
    assert [envelope.label.name for envelope in rt2.trace] == ['loop'] * i


async def test_default_recursion_budget_boundary() -> None:
    """The default budget stops the loop after exactly DEFAULT_UNFOLDINGS."""
    A, B = roles('A', 'B')
    proto = loop_protocol()
    script = [Choice(Label('loop'), None) for _ in range(DEFAULT_UNFOLDINGS)]
    a = Stub(A, project(proto, A), alts=script)
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b])
    with pytest.raises(RecursionLimitError):
        await rt.run()
    assert [envelope.label.name for envelope in rt.trace] == [
        'loop',
    ] * DEFAULT_UNFOLDINGS


def test_negative_recursion_budget_rejected() -> None:
    with pytest.raises(ValueError, match='unfoldings'):
        Allowance(unfoldings=-1)


async def test_nonrecursive_protocol_runs_with_zero_budget() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], allowance=Allowance(unfoldings=0))
    trace = await rt.run()
    assert len(trace) == 1
    assert trace[0].payload == 'yo'


def _two_loops_proto() -> SessionType:
    """Two sequential recursive binders; completing needs three unfolds."""
    A, B = roles('A', 'B')
    return (
        rec(
            't1',
            alt[A, B](case('l1') >> var('t1'), case('n1')),
        )
        >> rec(
            't2',
            alt[A, B](case('l2') >> var('t2'), case('n2')),
        )
    ).close()


async def test_shared_budget_across_binders() -> None:
    """Two binders draw from one shared budget, not N units each."""
    A, B = roles('A', 'B')
    proto = _two_loops_proto()
    script = [
        Choice(Label('l1'), None),
        Choice(Label('n1'), None),
        Choice(Label('n2'), None),
    ]

    a = Stub(A, project(proto, A), alts=list(script))
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], allowance=Allowance(unfoldings=3))
    trace = await rt.run()
    assert [envelope.label.name for envelope in trace] == ['l1', 'n1', 'n2']

    a2 = Stub(A, project(proto, A), alts=list(script))
    b2 = Stub(B, project(proto, B))
    rt2 = AgentRuntime(proto, [a2, b2], allowance=Allowance(unfoldings=2))
    with pytest.raises(RecursionLimitError):
        await rt2.run()
    assert [envelope.label.name for envelope in rt2.trace] == ['l1', 'n1']
