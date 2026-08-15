# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Tutorial 4: journal decisions then replay without model calls."""

from __future__ import annotations

from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty.journal import MemoryJournal
from agentsparty import OpenAIModel
from agentsparty import Text
from agentsparty.protocol import msg, render
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

A, B = roles('A', 'B')
Note = Text('Note')
protocol = msg[A, B] ( Note)


def main() -> None:
    print(render(protocol))
    journal = MemoryJournal()
    model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
    Cast(protocol).play(A, agent(model, 'n')).play(B, human(script())).run_sync(journal=journal)
    print('recorded', len(journal.script().decisions))
    replayed = (
        Cast(protocol)
        .play(A, agent(OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0)), 'n'))
        .play(B, human(script()))
        .run_sync(journal=MemoryJournal(journal.script().decisions))
    )
    print('replayed', replayed[0].payload)


if __name__ == '__main__':
    main()
