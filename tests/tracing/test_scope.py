"""Scope emission: seq, parenting, Failed, ambient current."""

from __future__ import annotations

import pytest

from agentsparty.kernel.role import roles
from agentsparty.protocol import Text, msg
from agentsparty.protocol.language.core import Label
from agentsparty.tracing.memory import MemoryTracer
from agentsparty.tracing.scope import (
    NULL_SCOPE,
    counting_ids,
    current,
    new_scope,
    uuid_ids,
)
from agentsparty.tracing.signals import (
    Failed,
    SessionFinished,
    SessionStarted,
    StepStarted,
)
from agentsparty.tracing.types import SpanId


def test_current_is_null_outside_session() -> None:
    assert current() is NULL_SCOPE


def test_seq_unique_and_strictly_increasing() -> None:
    mem = MemoryTracer()
    scope = new_scope(mem, counting_ids())
    A, B = roles('A', 'B')
    with scope.open(SessionStarted(msg[A, B]('Hi', Text).close(), (A, B))) as session:
        session.record(SessionFinished(0))
    seqs = [event.seq for event in mem.events]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))
    assert seqs == list(range(1, len(seqs) + 1))


def test_child_parents_to_self() -> None:
    mem = MemoryTracer()
    root = new_scope(mem, counting_ids())
    child = root.child()
    assert child.span.parent == root.span.id
    assert child.span.id != root.span.id
    assert child.span.id == SpanId('s2')
    assert root.span.id == SpanId('s1')


def test_open_records_failed_and_reraises() -> None:
    mem = MemoryTracer()
    scope = new_scope(mem, counting_ids())
    A, B = roles('A', 'B')
    with (
        pytest.raises(RuntimeError, match='boom'),
        scope.open(SessionStarted(msg[A, B]('Hi', Text).close(), (A, B))),
    ):
        raise RuntimeError('boom')
    names = mem.names()
    assert names[0] == 'session.started'
    assert names[-1] == 'failed'
    failed = mem.events[-1].signal
    assert isinstance(failed, Failed)
    assert 'RuntimeError' in failed.error
    assert 'boom' in failed.error


def test_open_publishes_ambient_and_restores() -> None:
    mem = MemoryTracer()
    scope = new_scope(mem, counting_ids())
    A, B = roles('A', 'B')
    assert current() is NULL_SCOPE
    with scope.open(SessionStarted(msg[A, B]('Hi', Text).close(), (A, B))) as session:
        assert current() is session
        child = session.child()
        with child.open(StepStarted(A, B, (Label('Hi'),))) as step:
            assert current() is step
        assert current() is session
    assert current() is NULL_SCOPE


def test_counting_ids_are_deterministic() -> None:
    ids = counting_ids('x')
    assert next(ids).value == 'x1'
    assert next(ids).value == 'x2'


def test_uuid_ids_yield_span_ids() -> None:
    sid = next(uuid_ids())
    assert isinstance(sid, SpanId)
    assert len(sid.value) == 12


def test_enter_makes_a_scope_ambient_without_recording() -> None:
    """enter publishes ambient scope and records nothing."""
    mem = MemoryTracer()
    scope = new_scope(mem, counting_ids())
    assert current() is NULL_SCOPE
    with scope.enter() as ambient:
        assert current() is ambient
        assert current() is scope
        assert mem.events == []
    assert current() is NULL_SCOPE
    assert mem.events == []
