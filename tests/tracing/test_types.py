"""Fanout and mapped combinator laws; NoTracer discards."""

from __future__ import annotations

from dataclasses import replace

from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.role import roles
from agentsparty.protocol import Label, Text, msg
from agentsparty.tracing.memory import MemoryTracer
from agentsparty.tracing.signals import SessionFinished, SessionStarted, StepStarted
from agentsparty.tracing.types import (
    NULL_TRACER,
    Event,
    NoTracer,
    Span,
    SpanId,
    fanout,
    mapped,
)


def _sample_events(n: int) -> list[Event]:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    root = Span(SpanId('s1'), None)
    child = Span(SpanId('s2'), SpanId('s1'))
    templates = [
        Event(SessionStarted(proto, (A, B)), root, 1),
        Event(StepStarted(A, B, (Label('Hi'),)), child, 2),
        Event(SessionFinished(0), root, 3),
    ]
    return [templates[i % len(templates)] for i in range(n)]


@given(st.lists(st.integers(0, 2), min_size=0, max_size=12))
def test_fanout_single_is_identity(indices: list[int]) -> None:
    """Fanout(t) ≡ t."""
    events = _sample_events(len(indices))
    mem = MemoryTracer()
    wrapped = fanout(mem)
    for event in events:
        wrapped.record(event)
    assert mem.events == events


@given(st.lists(st.integers(0, 2), min_size=0, max_size=8))
def test_fanout_empty_discards(indices: list[int]) -> None:
    """Fanout() ≡ NULL_TRACER (discards)."""
    events = _sample_events(len(indices))
    for event in events:
        fanout().record(event)
        NULL_TRACER.record(event)


@given(st.lists(st.integers(0, 2), min_size=0, max_size=8))
def test_fanout_associativity_and_order(indices: list[int]) -> None:
    """Fanout(fanout(a, b), c) ≡ fanout(a, fanout(b, c)); order preserved."""
    events = _sample_events(len(indices))
    a, b, c = MemoryTracer(), MemoryTracer(), MemoryTracer()
    left = fanout(fanout(a, b), c)
    for event in events:
        left.record(event)

    a2, b2, c2 = MemoryTracer(), MemoryTracer(), MemoryTracer()
    right = fanout(a2, fanout(b2, c2))
    for event in events:
        right.record(event)

    assert a.events == a2.events == events
    assert b.events == b2.events == events
    assert c.events == c2.events == events


@given(st.lists(st.integers(0, 2), min_size=0, max_size=8))
def test_mapped_identity(indices: list[int]) -> None:
    """Mapped(identity, t) ≡ t."""
    events = _sample_events(len(indices))
    mem = MemoryTracer()
    wrapped = mapped(lambda event: event, mem)
    for event in events:
        wrapped.record(event)
    assert mem.events == events


@given(st.lists(st.integers(0, 2), min_size=0, max_size=8))
def test_mapped_drop_all(indices: list[int]) -> None:
    """Mapped(lambda _: None, t) ≡ NULL_TRACER."""
    events = _sample_events(len(indices))
    mem = MemoryTracer()
    wrapped = mapped(lambda _: None, mem)
    for event in events:
        wrapped.record(event)
    assert mem.events == []


def test_mapped_can_redact() -> None:
    _A, _B = roles('A', 'B')
    event = Event(
        SessionFinished(1),
        Span(SpanId('s1'), None),
        1,
    )
    mem = MemoryTracer()

    def redact(e: Event) -> Event:
        return replace(e, signal=SessionFinished(0))

    mapped(redact, mem).record(event)
    assert mem.events[0].signal == SessionFinished(0)


def test_no_tracer_discards() -> None:
    _A, _B = roles('A', 'B')
    NoTracer().record(Event(SessionFinished(0), Span(SpanId('s1'), None), 1))
