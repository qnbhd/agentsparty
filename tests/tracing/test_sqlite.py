"""SqliteTracer round-trip over a real session."""

from __future__ import annotations

import json
import sqlite3

from agentsparty.journal import ROOT_TRACK, MemoryJournal, StepIndex
from agentsparty.journal.types import Decision
from agentsparty.kernel.role import roles
from agentsparty.participant import Choice
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing.sqlite import SqliteTracer
from tests.conftest import Stub


async def test_sqliteround_trip_session() -> None:
    conn = sqlite3.connect(':memory:')
    tracer = SqliteTracer(conn)
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], tracer=tracer)
    await rt.run()

    rows = conn.execute(
        'SELECT seq, span, parent, name, fields FROM events ORDER BY seq',
    ).fetchall()
    names = [row[3] for row in rows]
    assert names == [
        'session.started',
        'step.started',
        'step.selected',
        'step.delivered',
        'session.finished',
    ]
    assert rows[0][0] == 1
    assert rows[0][2] is None  # session parent
    assert rows[1][2] == rows[0][1]  # step parent is session span
    fields = json.loads(rows[-1][4])
    assert fields['messages'] == '1'
    conn.close()


async def test_sqlitemixed_recalled_and_selected() -> None:
    """A partial journal replays a Recalled prefix then a live Selected tail."""
    conn = sqlite3.connect(':memory:')
    tracer = SqliteTracer(conn)
    A, B = roles('A', 'B')
    proto = msg[A, B]('First', Text) >> msg[A, B]('Second', Text)
    proto = proto.close()
    decision = Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('First'), 'str', 'first')
    journal = MemoryJournal([decision])
    a = Stub(A, project(proto, A), alts=[Choice(Label('Second'), 'second')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], tracer=tracer, journal=journal)
    await rt.run()
    names = [row[0] for row in conn.execute('SELECT name FROM events ORDER BY seq').fetchall()]
    assert 'step.recalled' in names
    assert 'step.selected' in names
    conn.close()
