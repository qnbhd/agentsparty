"""The tracing contract: what a recorded event is and where it goes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from agentsparty.tracing.signals import Signal

__all__ = [
    'NULL_TRACER',
    'Event',
    'Fanout',
    'Mapped',
    'NoTracer',
    'Span',
    'SpanId',
    'Tracer',
    'fanout',
    'mapped',
]


@dataclass(frozen=True, order=True, slots=True)
class SpanId:
    """Identity of one span within a traced session."""

    value: str

    def __str__(self) -> str:
        """Return the id's :attr:`value`."""
        return self.value


@dataclass(frozen=True, slots=True)
class Span:
    """A scope of work: its own id plus the span that opened it."""

    id: SpanId
    parent: SpanId | None = None


@dataclass(frozen=True, slots=True)
class Event:
    """One recorded signal: what happened, where, and in which order."""

    signal: Signal
    span: Span
    seq: int


class Tracer(Protocol):
    """Where recorded events go: a stream, a database, a collector."""

    def record(self, event: Event) -> None:
        """Take *event*.

        Implementations must not raise, must not block and must not await:
        ``record`` is called synchronously from the task running the session.

        Args:
            event: The event to record.
        """
        ...


class NoTracer:
    """Tracer that discards every event; the runtime default."""

    def record(self, event: Event) -> None:
        """Discard *event*.

        Args:
            event: The event to discard.
        """


NULL_TRACER: Tracer = NoTracer()
"""The tracer used when observability is not switched on."""


@dataclass(frozen=True, slots=True)
class Fanout:
    """Tracer that forwards every event to each of :attr:`tracers`, in order."""

    tracers: tuple[Tracer, ...]

    def record(self, event: Event) -> None:
        """Forward *event* to every wrapped tracer.

        Args:
            event: The event to forward.
        """
        for tracer in self.tracers:
            tracer.record(event)


def fanout(*tracers: Tracer) -> Tracer:
    """Combine *tracers* into one that forwards to all of them, in order.

    Args:
        *tracers: The sinks to feed; none means "discard everything".
    """
    return Fanout(tracers)


@dataclass(frozen=True, slots=True)
class Mapped:
    """Tracer that rewrites or drops each event before forwarding it."""

    transform: Callable[[Event], Event | None]
    inner: Tracer

    def record(self, event: Event) -> None:
        """Forward ``transform(event)`` unless it is ``None``.

        Args:
            event: The event to transform.
        """
        mapped_event = self.transform(event)
        if mapped_event is not None:
            self.inner.record(mapped_event)


def mapped(transform: Callable[[Event], Event | None], inner: Tracer) -> Tracer:
    """Filter (return ``None``) or redact (return a new event) before *inner*.

    Args:
        transform: Applied to every event; ``None`` drops it.
        inner: The sink that receives the surviving events.
    """
    return Mapped(transform, inner)
