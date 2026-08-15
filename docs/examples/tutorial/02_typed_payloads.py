# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Tutorial 2: refine payload at the boundary."""

from __future__ import annotations

from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty import Integer
from agentsparty.protocol import msg, render
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Counter, Display = roles('Counter', 'Display')
Positive = Integer.where('positive', lambda n: n > 0)
Count = Positive('Count')
protocol = msg[Counter, Display] ( Count)


def main() -> None:
    print(render(protocol))
    model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
    for e in (
        Cast(protocol)
        .play(Counter, agent(model, 'send a positive count'))
        .play(Display, human(script()))
        .run_sync()
    ):
        print(e.payload)


if __name__ == '__main__':
    main()
