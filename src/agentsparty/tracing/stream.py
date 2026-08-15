"""Stream sink: one indented line per event on a text stream."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from functools import partial
from typing import Final, TextIO, TypeAlias

from agentsparty._utils.assertions import require_positive
from agentsparty.tracing.signals import describe
from agentsparty.tracing.types import Event, Span, SpanId

__all__ = ['StreamTracer']

DEFAULT_LIMIT: Final = 120
"""Characters kept per field value; an ellipsis is appended beyond that."""

_INDENT: Final = '  '
FieldItem: TypeAlias = tuple[str, object]
FieldItems: TypeAlias = Iterable[FieldItem]


class StreamTracer:
    """One indented line per event. Not thread-safe; span depths are never evicted."""

    def __init__(
        self,
        writer: TextIO | None = None,
        limit: int = DEFAULT_LIMIT,
        *,
        flush: bool = True,
    ) -> None:
        """Create a stream sink writing one indented line per event.

        Args:
            writer: The text stream to write to; ``sys.stderr`` when unset.
            limit: Characters kept per field value, an ellipsis appended beyond.
            flush: Whether to flush the stream after every event.
        """
        require_positive('limit', limit)
        self._writer = writer
        self._limit = limit
        self._flush = flush
        self._depth: dict[SpanId, int] = {}

    def record(self, event: Event) -> None:
        """Write *event* as one indented line to the stream.

        Args:
            event: The event to record.
        """
        # Resolved per call so that a rebound sys.stderr (pytest) is honoured.
        out = sys.stderr if self._writer is None else self._writer
        line = self._format(event)
        out.write(f'{line}\n')
        if self._flush:
            out.flush()

    def _format(self, event: Event) -> str:
        described = describe(event.signal)
        parts = [described.name]
        fields = _fields(described.fields.items(), self._limit)
        parts.extend(fields)
        return _INDENT * self._depth_of(event.span) + ' '.join(parts)

    def _depth_of(self, span: Span) -> int:
        # An unseen parent (out-of-order events) reads as a root.
        parent_depth = -1
        if span.parent is not None:
            parent_depth = self._depth.get(span.parent, -1)
        return self._depth.setdefault(span.id, parent_depth + 1)


def _brief(value: object, limit: int) -> str:
    """Single-line repr of *value*, cut to *limit* characters."""
    text = repr(value).replace('\n', r'\n')
    if len(text) <= limit:
        return text
    preview = text[:limit]
    return f'{preview}...'


def _field(key: str, value: object, limit: int) -> str:
    return f'{key}={_brief(value, limit)}'


def _fields(items: FieldItems, limit: int) -> tuple[str, ...]:
    formatter = partial(_field_from_item, limit=limit)
    return tuple(map(formatter, items))


def _field_from_item(item: FieldItem, limit: int) -> str:
    key, value = item
    return _field(key, value, limit)
