"""Where events are recorded from: span identity and the ambient scope."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from itertools import count
from uuid import uuid4

from agentsparty.kernel.errors import fault
from agentsparty.tracing.signals import Failed, Signal
from agentsparty.tracing.types import NULL_TRACER, Event, Span, SpanId, Tracer

__all__ = [
    'NULL_SCOPE',
    'Scope',
    'counting_ids',
    'current',
    'new_scope',
    'uuid_ids',
]

SPAN_ID_LENGTH = 12
"""Number of hexadecimal characters used by the UUID span-id source."""


def uuid_ids() -> Iterator[SpanId]:
    """Endless globally unique span ids; the production default."""
    return (SpanId(uuid4().hex[:SPAN_ID_LENGTH]) for _ in count())


def counting_ids(prefix: str = 's') -> Iterator[SpanId]:
    """Endless deterministic span ids (``s1``, ``s2``, …) for tests and docs.

    Args:
        prefix: The text placed before the counter.
    """
    return (SpanId(f'{prefix}{number}') for number in count(1))


@dataclass(frozen=True, slots=True)
class Scope:
    """A place to record from: a tracer, one span, and the shared counters."""

    tracer: Tracer
    span: Span
    ids: Iterator[SpanId]
    seq: Iterator[int]

    def record(self, signal: Signal) -> None:
        """Record *signal* as a point event in this scope's span.

        Args:
            signal: The fact to record.
        """
        self.tracer.record(Event(signal, self.span, next(self.seq)))

    def child(self) -> Scope:
        """A scope for a nested span, sharing the tracer and the counters."""
        return Scope(
            self.tracer,
            Span(next(self.ids), self.span.id),
            self.ids,
            self.seq,
        )

    @contextmanager
    def enter(self) -> Iterator[Scope]:
        """Make this scope the ambient one for the length of the block.

        Nothing is recorded and no span is opened: this is the ambient scope's
        acquire/release pair on its own, for the case where there is no domain
        signal to open with. Watching a single model call is that case. When
        there *is* a signal, use :meth:`open`.

        Yields:
            This scope, now the ambient one.
        """
        token = _CURRENT.set(self)
        try:
            yield self
        finally:
            _CURRENT.reset(token)

    @contextmanager
    def open(self, opening: Signal) -> Iterator[Scope]:
        """Record *opening*, make this scope ambient, and close it on the way out.

        If the body raises, :class:`~agentsparty.tracing.signals.Failed` is recorded
        before the exception propagates; the domain terminator (for example
        ``Delivered``) is the caller's to record.

        Args:
            opening: The signal that opens the span.

        Yields:
            This scope, now the ambient one.
        """
        with self.enter():
            self.record(opening)
            try:
                yield self
            except Exception as exc:
                self.record(Failed(fault(exc)))
                raise


def new_scope(tracer: Tracer, ids: Iterator[SpanId] | None = None) -> Scope:
    """A fresh root scope over *tracer*.

    Args:
        tracer: Where the recorded events go.
        ids: Span-id source; :func:`uuid_ids` when omitted.
    """
    factory = uuid_ids() if ids is None else ids
    return Scope(tracer, Span(next(factory), None), factory, count(1))


NULL_SCOPE: Scope = new_scope(NULL_TRACER)
"""The scope in force outside a traced session; discards everything."""

_CURRENT: ContextVar[Scope] = ContextVar('agentsparty_scope', default=NULL_SCOPE)


def current() -> Scope:
    """The innermost open scope, or :data:`NULL_SCOPE` outside a session."""
    return _CURRENT.get()
