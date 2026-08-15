"""The tool span nests under the ambient step span, like the model span."""

from __future__ import annotations

from agentsparty.kernel.role import roles
from agentsparty.machine import Machine, View
from agentsparty.participant import Choice
from agentsparty.protocol import Label, Text, alt, case, msg, seq
from agentsparty.runtime import AgentRuntime
from agentsparty.toolbox import Toolbox, reply, tool
from agentsparty.tracing.memory import MemoryTracer
from agentsparty.tracing.signals import (
    StepStarted,
    ToolAnswered,
    ToolCalled,
    describe,
)


async def test_tool_span_nests_under_the_step() -> None:
    Planner, Tools = roles('Planner', 'Tools')
    proto = seq(
        alt[Planner, Tools](case('search', Text)),
        msg[Tools, Planner]('hits', Text),
    ).close()

    async def search(query: str) -> Choice:
        return reply('hits', f'about {query}')

    def plan(view: View) -> Choice:
        return Choice(Label('search'), 'mpst')

    memory = MemoryTracer()
    await AgentRuntime(
        proto,
        [
            Machine(Planner, proto, plan),
            Toolbox(Tools, proto, [tool('search', Text, search)]),
        ],
        tracer=memory,
    ).run()

    steps = [e for e in memory.events if isinstance(e.signal, StepStarted)]
    called = next(e for e in memory.events if isinstance(e.signal, ToolCalled))
    answered = next(e for e in memory.events if isinstance(e.signal, ToolAnswered))
    assert called.span.parent in {step.span.id for step in steps}
    assert answered.span.id == called.span.id
    assert describe(called.signal).name == 'tool.called'
    assert describe(answered.signal).name == 'tool.answered'
