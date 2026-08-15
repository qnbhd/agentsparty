"""SQLite sink: one row per decision, keyed by session, track and step."""

from __future__ import annotations

import json
import sqlite3

from agentsparty._utils.assertions import pre
from agentsparty.journal.types import (
    Decision,
    Script,
    SessionId,
    StepIndex,
    Track,
    digest_of,
)
from agentsparty.kernel.errors import JournalError
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Label
from agentsparty.protocol.language.raw import as_integer, as_text, load_json
from agentsparty.protocol.session.types import SessionType

__all__ = ['SqliteJournal']

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    session  TEXT    NOT NULL,
    protocol TEXT    NOT NULL,
    track    TEXT    NOT NULL,
    step     INTEGER NOT NULL,
    sender   TEXT    NOT NULL,
    receiver TEXT    NOT NULL,
    label    TEXT    NOT NULL,
    codec    TEXT    NOT NULL,
    raw      TEXT    NOT NULL,
    PRIMARY KEY (session, track, step)
)
"""


class SqliteJournal:
    """Journal that keeps one row per decision in a ``decisions`` table.

    The primary key ``(session, track, step)`` makes a duplicated step on
    one track impossible at the storage layer: a second writer on the same
    track fails instead of silently interleaving two histories.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        proto: SessionType,
        session: SessionId,
    ) -> None:
        """Create the table if missing and adopt *session* on *connection*.

        The caller owns the connection: opening, closing and any pragmas
        (``journal_mode=WAL`` is a good idea) are outside this journal.

        Args:
            connection: An open SQLite connection owned by the caller.
            proto: The choreography this journal belongs to.
            session: Which recorded session to read and extend.

        Raises:
            JournalError: if rows for *session* were written under another
                protocol.
        """
        self._connection = connection
        self._session = session
        self._digest = digest_of(proto)
        connection.execute(SCHEMA)
        connection.commit()
        self._reject_foreign_protocol()

    def script(self) -> Script:
        """Everything decided so far, one word per track."""
        rows = self._connection.execute(
            'SELECT track, step, sender, receiver, label, codec, raw '
            'FROM decisions WHERE session = ? ORDER BY track, step',
            (self._session.value,),
        ).fetchall()
        return Script.of(_decision_of(row) for row in rows)

    def append(self, decision: Decision) -> None:
        """Insert *decision* as one row and commit.

        Args:
            decision: The alt to record.
        """
        track_text = _track_text(decision.step.track)
        recorded = self._connection.execute(
            'SELECT COUNT(*) FROM decisions WHERE session = ? AND track = ?',
            (self._session.value, track_text),
        ).fetchone()[0]
        track_path = decision.step.track.path
        position = decision.step.position
        next_position = recorded + 1
        pre(
            expr=position == recorded + 1,
            message=f'append must extend track {track_path} step {next_position}, got {position}',
        )
        self._connection.execute(
            'INSERT INTO decisions '
            '(session, protocol, track, step, sender, receiver, label, codec, raw) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                self._session.value,
                self._digest.value,
                track_text,
                decision.step.position,
                decision.sender.name,
                decision.receiver.name,
                str(decision.label),
                decision.codec,
                json.dumps(decision.raw),
            ),
        )
        self._connection.commit()

    def _reject_foreign_protocol(self) -> None:
        """Refuse rows recorded for this session under another protocol."""
        rows = self._connection.execute(
            'SELECT DISTINCT protocol FROM decisions WHERE session = ?',
            (self._session.value,),
        ).fetchall()
        digest = self._digest.value
        foreign = _foreign_protocols(rows, digest)
        if foreign:
            session = self._session.value
            raise JournalError(
                f'session {session} was recorded under protocol '
                f'{foreign[0]}, but this session runs {digest}',
            )


def _foreign_protocols(rows: list[tuple[object, ...]], digest: str) -> list[object]:
    """Protocol digests among *rows* that differ from *digest*."""
    return [row[0] for row in rows if row[0] != digest]


def _track_text(track: Track) -> str:
    """Encode a track path as a primary-key string; root is the empty string."""
    return '/'.join(str(index) for index in track.path)


def _track_of(text: str) -> Track:
    """Decode a track path written by :func:`_track_text`."""
    if not text:
        return Track(())
    return Track(tuple(int(part) for part in text.split('/')))


def _decision_of(row: tuple[str, int, str, str, str, str, str]) -> Decision:
    """One recorded decision, parsed from a database row."""
    try:
        return Decision(
            StepIndex(_track_of(as_text(row[0])), as_integer(row[1])),
            Role(as_text(row[2])),
            Role(as_text(row[3])),
            Label(as_text(row[4])),
            as_text(row[5]),
            load_json(row[6]),
        )
    except ValueError as exc:
        raise JournalError(f'malformed decision row: {row!r}') from exc
