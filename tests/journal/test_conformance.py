"""Conformance of Memory / Jsonl / Sqlite journals on one fixed protocol."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agentsparty.journal import (
    ROOT_TRACK,
    Decision,
    JsonlJournal,
    MemoryJournal,
    SessionId,
    StepIndex,
)
from agentsparty.journal.sqlite import SqliteJournal
from agentsparty.journal.types import Journal
from agentsparty.kernel.role import roles
from agentsparty.protocol import Label, Text, msg


@pytest.fixture(params=['memory', 'jsonl', 'sqlite'])
def journal(request, tmp_path: Path) -> Journal:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    if request.param == 'memory':
        return MemoryJournal()
    if request.param == 'jsonl':
        return JsonlJournal(tmp_path / 'session.jsonl', proto)
    conn = sqlite3.connect(':memory:')
    return SqliteJournal(conn, proto, SessionId('conformance'))


def _samples(a, b) -> list[Decision]:
    return [
        Decision(StepIndex(ROOT_TRACK, 1), a, b, Label('a'), 'undefined', None),
        Decision(StepIndex(ROOT_TRACK, 2), a, b, Label('b'), 'str', 'text'),
        Decision(StepIndex(ROOT_TRACK, 3), a, b, Label('c'), 'int', 1),
        Decision(StepIndex(ROOT_TRACK, 4), a, b, Label('d'), 'float', 1.5),
        Decision(StepIndex(ROOT_TRACK, 5), a, b, Label('e'), 'bool', raw=True),
        Decision(StepIndex(ROOT_TRACK, 6), a, b, Label('f'), 'object', {'a': [1, 2]}),
    ]


def test_fresh_journal_is_empty(journal: Journal) -> None:
    assert journal.script().length == 0


def test_append_order_and_raw_round_trip(journal: Journal) -> None:
    A, B = roles('A', 'B')
    samples = _samples(A, B)
    for decision in samples:
        journal.append(decision)
    assert journal.script().decisions == tuple(samples)


def test_multi_track_entries_round_trip(journal: Journal) -> None:
    """Two entries on different tracks read back as two words."""
    A, B, C, D = roles('A', 'B', 'C', 'D')
    left = ROOT_TRACK.branch(0)
    right = ROOT_TRACK.branch(1)
    samples = [
        Decision(StepIndex(left, 1), A, B, Label('L'), 'str', 'left'),
        Decision(StepIndex(right, 1), C, D, Label('R'), 'str', 'right'),
        Decision(StepIndex(left, 2), A, B, Label('L2'), 'str', 'again'),
    ]
    for decision in samples:
        journal.append(decision)
    script = journal.script()
    assert script.length_of(left) == 2
    assert script.length_of(right) == 1
    assert script.words[left][0].raw == 'left'
    assert script.words[right][0].raw == 'right'


def test_durable_reopen_preserves_script(tmp_path: Path) -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    samples = _samples(A, B)

    path = tmp_path / 'session.jsonl'
    jsonl = JsonlJournal(path, proto)
    for decision in samples:
        jsonl.append(decision)
    reopened_jsonl = JsonlJournal(path, proto)
    assert reopened_jsonl.script().decisions == tuple(samples)

    conn = sqlite3.connect(':memory:')
    sqlite = SqliteJournal(conn, proto, SessionId('reopen'))
    for decision in samples:
        sqlite.append(decision)
    reopened_sqlite = SqliteJournal(conn, proto, SessionId('reopen'))
    assert reopened_sqlite.script().decisions == tuple(samples)
