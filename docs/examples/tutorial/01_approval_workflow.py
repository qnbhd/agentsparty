# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Tutorial 1: Writer drafts; Reviewer approves or rejects; Reader gets Final."""

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

Writer, Reviewer, Reader = roles('Writer', 'Reviewer', 'Reader')
Draft = Text('Draft')
Approve = Nothing('Approve') >> msg[Writer, Reader] ( Text('Final'))
Reject = Nothing('Reject') >> msg[Writer, Reader] ( Text('Rejected'))

# docs: start protocol
protocol = (
    msg[Writer, Reviewer] ( Draft)
    >> alt[Reviewer, Writer] ( Approve, Reject)
)
# docs: end protocol


def main() -> None:
    print('=== protocol ===')
    print(render(protocol))
    model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
    cast = (
        Cast(protocol)
        .play(Writer, agent(model, 'Draft then send the branch result.'))
        .play(Reviewer, human(script(says(Approve))))
        .play(Reader, human(script()))
    )
    print('=== conversation ===')
    for e in cast.run_sync():
        print(f'{e.sender.name}:{e.label} -> {e.receiver.name} {e.payload!r}')


if __name__ == '__main__':
    main()
