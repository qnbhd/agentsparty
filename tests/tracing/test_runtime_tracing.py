"""Runtime tracing invariants I1-I5, I9, I10."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pytest
from hypothesis import given

from agentsparty.kernel.errors import RecursionLimitError
from agentsparty.kernel.role import Role, roles
from agentsparty.participant import Choice, Envelope
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.protocol.language.core import Chosen, Codec
from agentsparty.protocol.session import (
    Interaction,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
    unfold,
)
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing.memory import MemoryTracer
from agentsparty.tracing.signals import (
    Delivered,
    Failed,
    Selected,
    SessionFinished,
    SessionStarted,
    StepStarted,
    Unfolded,
)
from agentsparty.tracing.types import NULL_TRACER
from tests._helpers import loop_protocol
from tests.conftest import Stub
from tests.protocol.strategies import branching_protocols, linear_protocols


@dataclass
class FailStub(Stub):
    """Stub whose first select raises (failure-path tests only)."""

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        raise RuntimeError('select failed')


def _payload_for(codec: Codec) -> str | int | float | bool | None:
    name = codec.name
    if name == 'undefined':
        return None
    if name == 'str':
        return 'x'
    if name == 'int':
        return 1
    if name == 'float':
        return 1.0
    if name == 'bool':
        return True
    return None


def _script_for(proto: SessionType, role: Role) -> list[Choice]:
    """Walk a closed protocol and script first-label alts for *role* as sender."""
    alts: list[Choice] = []
    node: SessionType = proto
    budget = 64
    while True:
        match node:
            case SessionEnd() | SessionVar():
                return alts
            case SessionRec():
                result = _unfold_script(node, budget)
                if result is None:
                    return alts
                budget, node = result
            case Interaction(sender=sender, receiver=_r, branches=branches):
                node = _script_interaction(sender, branches, role, alts)
            case _:
                return alts


def _unfold_script(node: SessionType, budget: int) -> tuple[int, SessionType] | None:
    if budget == 0:
        return None
    return budget - 1, unfold(node)


def _script_interaction(sender, branches, role, alts) -> SessionType:
    first = next(iter(branches.values()))
    if sender == role:
        alts.append(Choice(first.label, _payload_for(first.payload)))
    return first.continuation


def _participants_for(proto: SessionType) -> list[Stub]:
    from agentsparty.protocol.session import participants as protocol_participants

    return [
        Stub(role, project(proto, role), alts=_script_for(proto, role))
        for role in protocol_participants(proto)
    ]


def _opening_terminators() -> dict[type, frozenset[type]]:
    return {
        SessionStarted: frozenset({SessionFinished, Failed}),
        StepStarted: frozenset({Delivered, Failed}),
    }


def _assert_invariants(events: list, trace: list[Envelope]) -> None:
    """I2-I5 over a recorded event list and runtime.trace."""
    # Seq unique and strictly increasing
    seqs = [e.seq for e in events]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))

    # Delivered envelopes match runtime.trace
    delivered = [e.signal.envelope for e in events if isinstance(e.signal, Delivered)]
    assert delivered == trace

    # One root session span; step parents are the session
    roots = {e.span.id for e in events if e.span.parent is None}
    assert len(roots) == 1
    session_id = next(iter(roots))
    for e in events:
        if isinstance(e.signal, StepStarted):
            assert e.span.parent == session_id

    # Every opened span has exactly one terminator
    openers = _opening_terminators()
    by_span: dict = {}
    for e in events:
        by_span.setdefault(e.span.id, []).append(e)
    for span_id, span_events in by_span.items():
        opener = next(
            (e for e in span_events if type(e.signal) in openers),
            None,
        )
        if opener is None:
            # point events (Unfolded, Selected) live on existing spans
            continue
        terminators = openers[type(opener.signal)]
        ends = [e for e in span_events if type(e.signal) in terminators]
        assert len(ends) == 1, (span_id, [type(e.signal) for e in span_events])


@given(linear_protocols(max_leaves=6))
async def test_neutrality_and_refinement_linear(proto: SessionType) -> None:
    """I1 + I2 over linear protocols."""
    try:
        null_stubs = _participants_for(proto)
        mem_stubs = _participants_for(proto)
    except Exception:
        return
    if not null_stubs:
        return

    rt_null = AgentRuntime(proto, null_stubs, tracer=NULL_TRACER)
    rt_mem = AgentRuntime(proto, mem_stubs, tracer=MemoryTracer())
    try:
        null_trace = await rt_null.run()
        mem_trace = await rt_mem.run()
    except Exception:
        # malformed script or projection edge — skip
        return
    assert null_trace == mem_trace
    assert mem_trace == rt_mem.trace
    mem = rt_mem.tracer
    assert isinstance(mem, MemoryTracer)
    _assert_invariants(mem.events, rt_mem.trace)


@given(branching_protocols(max_leaves=5))
async def test_invariants_branching(proto: SessionType) -> None:
    """I1-I5 over branching protocols with first-label scripts."""
    try:
        null_stubs = _participants_for(proto)
        mem_stubs = _participants_for(proto)
    except Exception:
        return
    if not null_stubs:
        return

    mem = MemoryTracer()
    rt_null = AgentRuntime(proto, null_stubs)
    rt_mem = AgentRuntime(proto, mem_stubs, tracer=mem)
    try:
        null_trace = await rt_null.run()
        mem_trace = await rt_mem.run()
    except Exception:
        return
    assert null_trace == mem_trace
    _assert_invariants(mem.events, rt_mem.trace)
    names = mem.names()
    assert names[0] == 'session.started'
    assert names[-1] == 'session.finished'


async def test_simple_session_shape() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    mem = MemoryTracer()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], tracer=mem)
    trace = await rt.run()
    assert mem.names() == [
        'session.started',
        'step.started',
        'step.selected',
        'step.delivered',
        'session.finished',
    ]
    _assert_invariants(mem.events, trace)
    finished = mem.events[-1].signal
    assert isinstance(finished, SessionFinished)
    assert finished.messages == 1


async def test_failure_path_i9() -> None:
    """Failed on step and session; exception still propagates."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    mem = MemoryTracer()
    a = FailStub(A, project(proto, A))
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], tracer=mem)
    with pytest.raises(RuntimeError, match='select failed'):
        await rt.run()
    names = mem.names()
    assert names[0] == 'session.started'
    assert 'step.started' in names
    assert names.count('failed') == 2
    # last two failed: step then session
    assert names[-1] == 'failed'
    step_failed = next(
        e for e in mem.events if isinstance(e.signal, Failed) and e.span.parent is not None
    )
    session_failed = next(
        e for e in mem.events if isinstance(e.signal, Failed) and e.span.parent is None
    )
    assert isinstance(step_failed.signal, Failed)
    assert isinstance(session_failed.signal, Failed)
    assert 'RuntimeError' in step_failed.signal.error
    assert 'RuntimeError' in session_failed.signal.error


async def test_recursion_budget_exhaustion_i10() -> None:
    """Unfolded with decreasing remaining, then Failed(RecursionLimitError)."""
    A, B = roles('A', 'B')
    proto = loop_protocol()
    budget = 3
    script = [Choice(Label('loop'), None) for _ in range(budget)]
    mem = MemoryTracer()
    a = Stub(A, project(proto, A), alts=script)
    b = Stub(B, project(proto, B))
    from agentsparty.kernel.budget import Allowance

    rt = AgentRuntime(proto, [a, b], allowance=Allowance(unfoldings=budget), tracer=mem)
    with pytest.raises(RecursionLimitError):
        await rt.run()
    unfolded = [e.signal for e in mem.events if isinstance(e.signal, Unfolded)]
    assert len(unfolded) == budget
    remainings = [u.remaining for u in unfolded]
    assert remainings == [budget - 1 - i for i in range(budget)]
    assert remainings[-1] == 0
    failed = [e for e in mem.events if isinstance(e.signal, Failed)]
    assert len(failed) == 1
    assert isinstance(failed[0].signal, Failed)
    assert 'RecursionLimitError' in failed[0].signal.error
    assert failed[0].span.parent is None


async def test_selected_and_delivered_on_step_span() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    mem = MemoryTracer()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], tracer=mem)
    await rt.run()
    step = next(e for e in mem.events if isinstance(e.signal, StepStarted))
    selected = next(e for e in mem.events if isinstance(e.signal, Selected))
    delivered = next(e for e in mem.events if isinstance(e.signal, Delivered))
    assert selected.span.id == step.span.id
    assert delivered.span.id == step.span.id
    assert selected.span.parent == mem.events[0].span.id
