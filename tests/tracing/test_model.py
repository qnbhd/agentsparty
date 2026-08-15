"""Traced model nests under the ambient step span."""

from __future__ import annotations

import pytest

from agentsparty.agent import Agent
from agentsparty.kernel.role import roles
from agentsparty.llm import Answer, Message, ModelId, StructuredRequest
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing.memory import MemoryTracer
from agentsparty.tracing.model import traced
from agentsparty.tracing.scope import counting_ids, new_scope
from agentsparty.tracing.signals import (
    ModelAnswered,
    ModelCalled,
    SessionStarted,
    StepStarted,
    describe,
)
from tests.conftest import Stub

STUB = ModelId('stub', 'v1')


class StubModel:
    def __init__(
        self,
        text: str = '{"alt": {"label": "Hi", "payload": "yo"}}',
    ) -> None:
        self.text = text
        self.requests: list[StructuredRequest] = []

    async def complete(self, request: StructuredRequest) -> Answer:
        self.requests.append(request)
        return Answer(self.text, STUB)


async def test_model_nesting_under_step_i11() -> None:
    """Model.called span parent is the current step span."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    mem = MemoryTracer()
    model = StubModel()
    agent = Agent(
        model=traced(model),
        role=A,
        instructions='pick Hi',
        proto=proto,
    )
    b = Stub(B, project(proto, B))
    rt = AgentRuntime(proto, [agent, b], tracer=mem)
    await rt.run()

    step = next(e for e in mem.events if isinstance(e.signal, StepStarted))
    called = next(e for e in mem.events if isinstance(e.signal, ModelCalled))
    answered = next(e for e in mem.events if isinstance(e.signal, ModelAnswered))
    assert called.span.parent == step.span.id
    assert answered.span.id == called.span.id
    assert describe(called.signal).name == 'model.called'
    assert describe(answered.signal).name == 'model.answered'
    assert model.requests  # real complete path driven


async def test_traced_outside_session_is_noop() -> None:
    """Outside a session, ambient NULL_SCOPE discards; complete still works."""
    model = StubModel('ok')
    wrapped = traced(model)
    request = StructuredRequest(
        instructions='',
        messages=(Message('user', 'hi'),),
        schema_name='t',
        schema={'type': 'object'},
        effort='low',
    )
    answer = await wrapped.complete(request)
    assert answer.text == 'ok'
    assert answer.model == STUB
    assert model.requests == [request]


async def test_traced_model_failed_on_raise() -> None:
    class BoomModel:
        async def complete(self, request: StructuredRequest) -> Answer:
            raise RuntimeError('llm down')

    mem = MemoryTracer()
    scope = new_scope(mem, counting_ids())
    A, B = roles('A', 'B')
    with (
        scope.open(SessionStarted(msg[A, B]('Hi', Text).close(), (A, B))) as session,
        session.child().open(StepStarted(A, B, (Label('Hi'),))),
        pytest.raises(RuntimeError, match='llm down'),
    ):
        await traced(BoomModel()).complete(
            StructuredRequest(
                instructions='',
                messages=(),
                schema_name='t',
                schema={},
                effort='none',
            ),
        )
    names = mem.names()
    assert 'model.called' in names
    assert 'failed' in names
    assert 'model.answered' not in names
