# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Client commissions work; reviewer may fix once, then worker delivers.

Sample run (conversation sketch, 3-6 lines)::

    Client:Task -> Worker 'summarise the brief'
    Worker:Result -> Reviewer '…first draft…'
    Reviewer:Fix -> Worker 'add one concrete number'
    Worker:Result -> Reviewer '…revised…'
    Reviewer:Ship -> Worker
    Worker:Delivered -> Client '…final…'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/starter.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
)

Client, Worker, Reviewer = ap.roles('Client', 'Worker', 'Reviewer')

DELIVERED = 'The accepted result.'
SHIP = 'Accept the result as it stands.'


# Same Delivered intent on both branches: a mismatch would refuse projection.


Task = ap.Text('Task', 'What must be done, in one sentence.')
Result = ap.Text('Result', 'The work product.')
Ship = ap.Nothing('Ship', SHIP)
Delivered = ap.Text('Delivered', DELIVERED)
Fix = ap.Text('Fix', 'One concrete change, at most twenty words.')

protocol = (
    msg[Client, Worker](Task)
    >> msg[Worker, Reviewer](Result)
    >> alt[Reviewer, Worker](
        Ship >> msg[Worker, Client](Delivered),
        Fix
        >> msg[Worker, Reviewer](Result)
        >> msg[Reviewer, Worker](Ship)
        >> msg[Worker, Client](Delivered),
    )
).close()


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    worker = ap.Agent(
        model,
        Worker,
        'Do the work. Send Result as plain prose. After Ship, send Delivered '
        'with the accepted final wording.',
        protocol,
    )
    reviewer = ap.Agent(
        model,
        Reviewer,
        'Review Result. Prefer Ship when the work is acceptable. If something '
        'is missing, send Fix with one concrete change in at most twenty words, '
        'then Ship the revised Result.',
        protocol,
    )
    client = ap.Human(
        Client,
        protocol,
        ap.ScriptedHumanIo([ap.says(Task, 'summarise the brief')]),
    )
    return protocol, [client, worker, reviewer]


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    cast = (
        ap
        .Cast(protocol)
        .play(Client, ap.human(ap.script(ap.says(Task, 'summarise the brief'))))
        .play(
            Worker,
            ap.agent(
                model,
                'Do the work. Send Result as plain prose. After Ship, send Delivered '
                'with the accepted final wording.',
            ),
        )
        .play(
            Reviewer,
            ap.agent(
                model,
                'Review Result. Prefer Ship when the work is acceptable. If something '
                'is missing, send Fix with one concrete change in at most twenty words, '
                'then Ship the revised Result.',
            ),
        )
    )
    report.conversation(cast.run_sync())


if __name__ == '__main__':
    main()
