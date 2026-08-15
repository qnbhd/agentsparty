# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Tutorial 5: MemoryTracer observes without steering."""

from __future__ import annotations

from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty import Text
from agentsparty.protocol import msg, render
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast
from agentsparty.tracing import MemoryTracer

A, B = roles('A', 'B')
Note = Text('Note')
protocol = msg[A, B] ( Note)


def main() -> None:
    print(render(protocol))
    tracer = MemoryTracer()
    model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
    Cast(protocol).play(A, agent(model, 'n')).play(B, human(script())).run_sync(tracer=tracer)
    print('trace events', len(tracer.events))


if __name__ == '__main__':
    main()
