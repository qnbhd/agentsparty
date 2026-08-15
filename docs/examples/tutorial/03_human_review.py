# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Tutorial 3: human is a protocol role, not a callback."""

from __future__ import annotations

from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty.participant import says
from agentsparty import Nothing, Text
from agentsparty.protocol import alt, msg, render
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Writer, Reviewer = roles('Writer', 'Reviewer')
Draft = Text('Draft')
Approve = Nothing('Approve')
Revise = Text('Revise')
protocol = msg[Writer, Reviewer] ( Draft) >> alt[Reviewer, Writer] ( Approve, Revise)


def main() -> None:
    print(render(protocol))
    model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
    for e in (
        Cast(protocol)
        .play(Writer, agent(model, 'draft'))
        .play(Reviewer, human(script(says(Revise, 'add numbers'))))
        .run_sync()
    ):
        print(e.label.name, e.payload)


if __name__ == '__main__':
    main()
