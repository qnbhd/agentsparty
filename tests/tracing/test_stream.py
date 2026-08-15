"""StreamTracer format and indentation from span parents."""

from __future__ import annotations

import io

from agentsparty.journal import ROOT_TRACK, MemoryJournal, StepIndex
from agentsparty.journal.types import Decision
from agentsparty.kernel.role import roles
from agentsparty.participant import Choice
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing.scope import counting_ids, new_scope
from agentsparty.tracing.signals import SessionFinished, SessionStarted, StepStarted
from agentsparty.tracing.stream import StreamTracer, _brief
from tests.conftest import Stub


def test_streamindents_by_parent() -> None:
    buf = io.StringIO()
    tracer = StreamTracer(buf)
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    scope = new_scope(tracer, counting_ids())
    with scope.open(SessionStarted(proto, (A, B))) as session:
        with session.child().open(StepStarted(A, B, (Label('Hi'),))):
            pass
        session.record(SessionFinished(0))
    lines = buf.getvalue().splitlines()
    assert lines[0].startswith('session.started')
    assert lines[1].startswith('  step.started')
    assert lines[2].startswith('session.finished')


async def test_streamon_runtime_session() -> None:
    buf = io.StringIO()
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], tracer=StreamTracer(buf))
    await rt.run()
    text = buf.getvalue()
    assert 'session.started' in text
    assert 'step.started' in text
    assert 'step.selected' in text
    assert 'step.delivered' in text
    assert 'session.finished' in text
    assert '  step.started' in text


def test_brief_truncates() -> None:
    assert _brief('hi', 10) == "'hi'"
    long = 'x' * 200
    out = _brief(long, 20)
    assert out.endswith('...')
    assert len(out) == 23  # 20 + "..."


async def test_streammixed_recalled_and_selected() -> None:
    """A partial journal replays a Recalled prefix then a live Selected tail."""
    buf = io.StringIO()
    A, B = roles('A', 'B')
    proto = msg[A, B]('First', Text) >> msg[A, B]('Second', Text)
    proto = proto.close()
    decision = Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('First'), 'str', 'first')
    journal = MemoryJournal([decision])
    a = Stub(A, project(proto, A), alts=[Choice(Label('Second'), 'second')])
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [a, b], tracer=StreamTracer(buf), journal=journal)
    await rt.run()
    text = buf.getvalue()
    assert 'step.recalled' in text
    assert 'step.selected' in text
    assert 'step.delivered' in text
