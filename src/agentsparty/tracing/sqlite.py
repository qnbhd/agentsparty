"""SQLite sink: one row per event in an ``events`` table."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping

from agentsparty.tracing.signals import describe
from agentsparty.tracing.types import Event

__all__ = ['SqliteTracer']

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq    INTEGER NOT NULL,
    span   TEXT    NOT NULL,
    parent TEXT,
    name   TEXT    NOT NULL,
    fields TEXT    NOT NULL
)
"""


class SqliteTracer:
    """Tracer that appends one row per event to an ``events`` table."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Create the table on *connection* if it is missing.

        The caller owns the connection: opening, closing and any pragmas
        (``journal_mode=WAL`` is a good idea) are outside this tracer.

        Args:
            connection: An open SQLite connection owned by the caller.
        """
        self._connection = connection
        connection.execute(SCHEMA)
        connection.commit()

    def record(self, event: Event) -> None:
        """Insert *event* as one row and commit.

        Args:
            event: The event to store.
        """
        self._connection.execute(
            'INSERT INTO events (seq, span, parent, name, fields) VALUES (?, ?, ?, ?, ?)',
            _event_row(event),
        )
        self._connection.commit()


def _event_row(event: Event) -> tuple[int, str, str | None, str, str]:
    described = describe(event.signal)
    fields = json.dumps(_string_fields(described.fields))
    return (
        event.seq,
        str(event.span.id),
        None if event.span.parent is None else str(event.span.parent),
        described.name,
        fields,
    )


def _string_fields(fields: Mapping[str, object]) -> dict[str, str]:
    return {key: str(value) for key, value in fields.items()}
