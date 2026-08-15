"""JSONL sink: a header line naming the protocol, then one line per decision."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from agentsparty.journal.types import (
    Decision,
    Digest,
    Script,
    SessionId,
    StepIndex,
    Track,
    _check_append,
    digest_of,
)
from agentsparty.kernel.errors import JournalError
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Label
from agentsparty.protocol.language.raw import (
    RawValue,
    as_array,
    as_integer,
    as_object,
    as_text,
    load_json,
)
from agentsparty.protocol.session.types import SessionType

__all__ = ['JsonlJournal']

FORMAT = 'agentsparty/2'
"""Value of the ``journal`` field in a header line."""

SESSION_ID_LENGTH = 12
"""Number of hexadecimal characters used in a generated session id."""


class JsonlJournal:
    """Journal stored as one JSON object per line in an append-only file."""

    def __init__(self, path: Path, proto: SessionType) -> None:
        """Open, or create, the journal at *path* for *proto*.

        This is the parsing boundary: an existing file is read and checked
        against the protocol's digest, a missing one gets a fresh header.
        Nothing downstream re-checks.

        Args:
            path: The journal file.
            proto: The choreography this journal belongs to.

        Raises:
            JournalError: if the file does not read as a journal, or was
                written under a different protocol.
        """
        self._path = path
        self._digest = digest_of(proto)
        if path.exists():
            session, decisions = _read(path, self._digest)
        else:
            session_id = uuid4().hex[:SESSION_ID_LENGTH]
            session = SessionId(session_id)
            decisions = ()
            _write(path, _header_line(session, self._digest))
        self._session = session
        self._script = Script.of(decisions)

    @property
    def session(self) -> SessionId:
        """Identity recorded in the journal's header."""
        return self._session

    def script(self) -> Script:
        """Everything decided so far, one word per track."""
        return self._script

    def append(self, decision: Decision) -> None:
        """Write *decision* as one line and flush it to disk.

        Args:
            decision: The alt to record.
        """
        _check_append(self._script, decision)
        _write(self._path, _line(decision))
        # rebuild: free interleaving is fine; Script.of re-groups by track
        self._script = Script.of((*self._script.decisions, decision))


def _write(path: Path, line: str) -> None:
    """Append *line* to *path* and flush it all the way to disk."""
    with path.open('a', encoding='utf-8') as handle:
        handle.write(f'{line}\n')
        handle.flush()
        os.fsync(handle.fileno())


def _line(decision: Decision) -> str:
    """Render *decision* as one JSON object."""
    return json.dumps(
        {
            'track': list(decision.step.track.path),
            'step': decision.step.position,
            'sender': decision.sender.name,
            'receiver': decision.receiver.name,
            'label': str(decision.label),
            'codec': decision.codec,
            'raw': decision.raw,
        },
        ensure_ascii=False,
    )


def _header_line(session: SessionId, digest: Digest) -> str:
    """Render the header naming the format, the session and the protocol."""
    return json.dumps(
        {'journal': FORMAT, 'session': session.value, 'protocol': digest.value},
    )


def _read_entries(lines: list[str], path: Path) -> tuple[Decision, ...]:
    entries: list[Decision] = []
    for index, line in enumerate(lines, start=1):
        try:
            raw = _parsed(line, path)
        except JournalError:
            if index == len(lines):
                break
            raise
        entries.append(_decision_of(raw, path))
    return tuple(entries)


def _read(path: Path, digest: Digest) -> tuple[SessionId, tuple[Decision, ...]]:
    """Parse the journal at *path*, checking that it belongs to *digest*.

    A single torn final line is tolerated: a power loss mid-``append`` can
    leave the last line half-written. Such a line is not JSON, so it is
    dropped here and the journal stays a valid prefix — the runtime re-asks
    the lost step live. A broken line that is not the last one is a real
    corruption and still raises.

    Raises:
        JournalError: on an empty file, a line that is not JSON (other than a
            torn final line), a foreign format, a protocol mismatch or a
            malformed entry.
    """
    lines = [line for line in path.read_text(encoding='utf-8').splitlines() if line]
    if not lines:
        raise JournalError(f'{path} is empty; a journal starts with a header line')
    session = _session_of(_parsed(lines[0], path), digest, path)
    return session, _read_entries(lines[1:], path)


def _parsed(line: str, path: Path) -> RawValue:
    """One journal line as raw JSON."""
    try:
        return load_json(line)
    except ValueError as exc:
        raise JournalError(f'{path}: line is not JSON: {line!r}') from exc


def _session_of(raw: RawValue, digest: Digest, path: Path) -> SessionId:
    """The session named by a header line that matches *digest*."""
    try:
        fields = as_object(raw)
    except (KeyError, ValueError) as exc:
        raise JournalError(f'{path}: malformed header line') from exc
    return _session_from_fields(fields, digest, path)


def _session_from_fields(
    fields: dict[str, RawValue],
    digest: Digest,
    path: Path,
) -> SessionId:
    try:
        parsed = _header_fields(fields)
    except (KeyError, ValueError) as exc:
        raise JournalError(f'{path}: malformed header line') from exc
    found, session, version = parsed
    if version != FORMAT:
        raise JournalError(f'{path}: unknown journal format {version!r}')
    if found != digest:
        raise JournalError(
            f'{path} was written under protocol {found.value}, '
            f'but this session runs {digest.value}',
        )
    return session


def _header_fields(fields: dict[str, RawValue]) -> tuple[Digest, SessionId, str]:
    found = Digest(as_text(fields['protocol']))
    session = SessionId(as_text(fields['session']))
    version = as_text(fields['journal'])
    return found, session, version


def _decision_of(raw: RawValue, path: Path) -> Decision:
    """One recorded decision, parsed from a journal line."""
    try:
        fields = as_object(raw)
    except (KeyError, ValueError) as exc:
        raise JournalError(f'{path}: malformed journal entry: {raw!r}') from exc
    return _decision_from_fields(fields, path, raw)


def _decision_from_fields(
    fields: dict[str, RawValue],
    path: Path,
    raw: RawValue,
) -> Decision:
    try:
        return _decision_fields(fields)
    except (KeyError, ValueError) as exc:
        raise JournalError(f'{path}: malformed journal entry: {raw!r}') from exc


def _decision_fields(fields: dict[str, RawValue]) -> Decision:
    track_raw = fields.get('track', [])
    track = Track(tuple(as_integer(item) for item in as_array(track_raw)))
    return Decision(
        StepIndex(track, as_integer(fields['step'])),
        Role(as_text(fields['sender'])),
        Role(as_text(fields['receiver'])),
        Label(as_text(fields['label'])),
        as_text(fields['codec']),
        fields['raw'],
    )
