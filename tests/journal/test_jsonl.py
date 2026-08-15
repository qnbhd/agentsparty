"""JsonlJournal durability and boundary errors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentsparty.journal import JsonlJournal, MemoryJournal
from agentsparty.kernel.errors import JournalError
from agentsparty.kernel.role import roles
from agentsparty.protocol import Text, msg
from tests.journal.conftest import session, three_message_protocol


async def test_jsonlwrites_header_and_one_line_per_decision(tmp_path: Path) -> None:
    proto = three_message_protocol()
    path = tmp_path / 'session.jsonl'
    journal = JsonlJournal(path, proto)
    baseline, _ = await session(proto, journal)
    text = path.read_text(encoding='utf-8')
    lines = [line for line in text.splitlines() if line]
    assert len(lines) == len(baseline) + 1
    header = json.loads(lines[0])
    assert header['journal'] == 'agentsparty/2'
    assert 'session' in header
    assert 'protocol' in header


async def test_jsonlreopen_sees_same_decisions(tmp_path: Path) -> None:
    proto = three_message_protocol()
    path = tmp_path / 'session.jsonl'
    first = JsonlJournal(path, proto)
    baseline, _ = await session(proto, first)
    reopened = JsonlJournal(path, proto)
    assert reopened.script().decisions == first.script().decisions
    trace, peers = await session(proto, reopened)
    assert trace == baseline
    assert all(peer.selects == 0 for peer in peers)


def test_jsonlforeign_protocol(tmp_path: Path) -> None:
    A, B = roles('A', 'B')
    path = tmp_path / 'session.jsonl'
    JsonlJournal(path, msg[A, B]('Hi', Text).close())
    with pytest.raises(JournalError, match='written under protocol'):
        JsonlJournal(path, msg[A, B]('Bye', Text).close())


async def test_jsonlbroken_line(tmp_path: Path) -> None:
    proto = three_message_protocol()
    path = tmp_path / 'session.jsonl'
    await session(proto, JsonlJournal(path, proto))
    lines = path.read_text(encoding='utf-8').splitlines()
    # A broken line that is not the last one is a real corruption, not a
    # torn tail, and must raise.
    lines.insert(1, '{')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with pytest.raises(JournalError, match='not JSON'):
        JsonlJournal(path, proto)


async def test_jsonltolerates_torn_tail(tmp_path: Path) -> None:
    proto = three_message_protocol()
    path = tmp_path / 'session.jsonl'
    journal = JsonlJournal(path, proto)
    baseline, _ = await session(proto, journal)
    # Simulate a power loss mid-append: a partial last line.
    with path.open('a', encoding='utf-8') as handle:
        handle.write('{"step": 4, "sende')
    reopened = JsonlJournal(path, proto)
    assert reopened.script().length == journal.script().length
    trace, peers = await session(proto, reopened)
    assert trace == baseline
    assert all(peer.selects == 0 for peer in peers)


async def test_jsonlentry_missing_raw(tmp_path: Path) -> None:
    proto = three_message_protocol()
    path = tmp_path / 'session.jsonl'
    journal = JsonlJournal(path, proto)
    await session(proto, journal)
    lines = path.read_text(encoding='utf-8').splitlines()
    broken = json.loads(lines[1])
    del broken['raw']
    lines[1] = json.dumps(broken)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with pytest.raises(JournalError, match='malformed journal entry'):
        JsonlJournal(path, proto)


async def test_jsonlentry_wrong_type(tmp_path: Path) -> None:
    proto = three_message_protocol()
    path = tmp_path / 'session.jsonl'
    journal = JsonlJournal(path, proto)
    await session(proto, journal)
    lines = path.read_text(encoding='utf-8').splitlines()
    broken = json.loads(lines[1])
    broken['step'] = 'not-an-int'
    lines[1] = json.dumps(broken)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with pytest.raises(JournalError, match='malformed journal entry'):
        JsonlJournal(path, proto)


def test_jsonlunknown_format(tmp_path: Path) -> None:
    A, B = roles('A', 'B')
    path = tmp_path / 'session.jsonl'
    path.write_text(
        json.dumps({'journal': 'other/9', 'session': 'x', 'protocol': 'y'}) + '\n',
        encoding='utf-8',
    )
    with pytest.raises(JournalError, match='unknown journal format'):
        JsonlJournal(path, msg[A, B]('Hi', Text).close())


def test_jsonlmalformed_header_wrong_type(tmp_path: Path) -> None:
    A, B = roles('A', 'B')
    path = tmp_path / 'session.jsonl'
    path.write_text(
        json.dumps({'journal': 'agentsparty/1', 'session': 'x', 'protocol': 123}) + '\n',
        encoding='utf-8',
    )
    with pytest.raises(JournalError, match='malformed header line'):
        JsonlJournal(path, msg[A, B]('Hi', Text).close())


def test_jsonlempty_file(tmp_path: Path) -> None:
    A, B = roles('A', 'B')
    path = tmp_path / 'session.jsonl'
    path.touch()
    with pytest.raises(JournalError, match='empty'):
        JsonlJournal(path, msg[A, B]('Hi', Text).close())


async def test_jsonlmatches_memory_trace(tmp_path: Path) -> None:
    proto = three_message_protocol()
    mem_trace, _ = await session(proto, MemoryJournal())
    path = tmp_path / 'session.jsonl'
    file_trace, _ = await session(proto, JsonlJournal(path, proto))
    assert file_trace == mem_trace
