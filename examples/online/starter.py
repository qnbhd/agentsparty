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

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
)

Client, Worker, Reviewer = pa.roles('Client', 'Worker', 'Reviewer')

DELIVERED = 'The accepted result.'
SHIP = 'Accept the result as it stands.'


# Same Delivered intent on both branches: a mismatch would refuse projection.


Task = pa.Text('Task', 'What must be done, in one sentence.')
Result = pa.Text('Result', 'The work product.')
Ship = pa.Nothing('Ship', SHIP)
Delivered = pa.Text('Delivered', DELIVERED)
Fix = pa.Text('Fix', 'One concrete change, at most twenty words.')

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


def build() -> tuple[SessionType, list[pa.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    worker = pa.Agent(
        model,
        Worker,
        'Do the work. Send Result as plain prose. After Ship, send Delivered '
        'with the accepted final wording.',
        protocol,
    )
    reviewer = pa.Agent(
        model,
        Reviewer,
        'Review Result. Prefer Ship when the work is acceptable. If something '
        'is missing, send Fix with one concrete change in at most twenty words, '
        'then Ship the revised Result.',
        protocol,
    )
    client = pa.Human(
        Client,
        protocol,
        pa.ScriptedHumanIo([pa.says(Task, 'summarise the brief')]),
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
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    cast = (
        pa
        .Cast(protocol)
        .play(Client, pa.human(pa.script(pa.says(Task, 'summarise the brief'))))
        .play(
            Worker,
            pa.agent(
                model,
                'Do the work. Send Result as plain prose. After Ship, send Delivered '
                'with the accepted final wording.',
            ),
        )
        .play(
            Reviewer,
            pa.agent(
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
