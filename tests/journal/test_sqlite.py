"""SqliteJournal isolation and boundary errors."""

from __future__ import annotations

import sqlite3

import pytest

from agentsparty.journal import ROOT_TRACK, Decision, SessionId, StepIndex, digest_of
from agentsparty.journal.sqlite import SqliteJournal
from agentsparty.kernel.errors import JournalError
from agentsparty.kernel.role import roles
from agentsparty.protocol import Label, Text, msg
from tests.journal.conftest import session, three_message_protocol


async def test_sqliterecords_and_replays() -> None:
    proto = three_message_protocol()
    conn = sqlite3.connect(':memory:')
    journal = SqliteJournal(conn, proto, SessionId('s1'))
    baseline, _ = await session(proto, journal)
    assert journal.script().length == len(baseline)
    reopened = SqliteJournal(conn, proto, SessionId('s1'))
    trace, peers = await session(proto, reopened)
    assert trace == baseline
    assert all(peer.selects == 0 for peer in peers)


async def test_sqlitesessions_are_isolated() -> None:
    proto = three_message_protocol()
    conn = sqlite3.connect(':memory:')
    first = SqliteJournal(conn, proto, SessionId('one'))
    second = SqliteJournal(conn, proto, SessionId('two'))
    baseline, _ = await session(proto, first)
    assert second.script().length == 0
    assert first.script().length == len(baseline)


def test_sqliteduplicate_step_raises() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    conn = sqlite3.connect(':memory:')
    journal = SqliteJournal(conn, proto, SessionId('s1'))
    decision = Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('Hi'), 'str', 'yo')
    journal.append(decision)
    # The contiguity pre-check (invariant 1) rejects a duplicate before the
    # primary key even sees it.
    with pytest.raises(AssertionError, match='append must extend track'):
        journal.append(decision)


def test_sqliteforeign_protocol() -> None:
    A, B = roles('A', 'B')
    hi = msg[A, B]('Hi', Text).close()
    bye = msg[A, B]('Bye', Text).close()
    conn = sqlite3.connect(':memory:')
    journal = SqliteJournal(conn, hi, SessionId('s1'))
    journal.append(Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('Hi'), 'str', 'yo'))
    with pytest.raises(JournalError, match='recorded under protocol'):
        SqliteJournal(conn, bye, SessionId('s1'))


def test_sqlitemalformed_row_raises() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    conn = sqlite3.connect(':memory:')
    journal = SqliteJournal(conn, proto, SessionId('s1'))
    conn.execute(
        'INSERT INTO decisions '
        '(session, protocol, track, step, sender, receiver, label, codec, raw) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            SessionId('s1').value,
            digest_of(proto).value,
            '',
            1,
            'A',
            'B',
            'Hi',
            'str',
            'not-json{',
        ),
    )
    conn.commit()
    with pytest.raises(JournalError, match='malformed decision row'):
        journal.script()
