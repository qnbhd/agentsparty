# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Providers: ModelId parses provider-prefixed names; one adapter shape.

ModelId.parse splits on the first colon and does not resolve hosts. Every
and the live example uses the standard OpenAI client configuration.

What you will see (sample run):
  === model identity ===
  'openrouter:anthropic/claude' -> provider='openrouter' name='anthropic/claude'
  === protocol ===
  Client -> Worker : Task(str)
  Worker -> Reviewer : Draft(str)
  Reviewer -> Client : Verdict(str)
  end
  === conversation ===
  Client:Task -> Worker '...'
  Worker:Draft -> Reviewer '...'
  Reviewer:Verdict -> Client '...'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/providers.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import SessionType, msg, project_all, seq

Client, Worker, Reviewer = ap.roles('Client', 'Worker', 'Reviewer')


Verdict = ap.Text('Verdict', 'Accept or a short note.')
Task = ap.Text('Task', 'What must be done, in one sentence.')
Draft = ap.Text('Draft', 'The work product.')

protocol = seq(
    msg[Client, Worker](Task),
    msg[Worker, Reviewer](Draft),
    msg[Reviewer, Client](Verdict),
).close()


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    worker = ap.Agent(model, Worker, 'Do the work in one short draft.', protocol)
    reviewer = ap.Agent(model, Reviewer, 'Accept or note one change.', protocol)
    client = ap.Human(
        Client,
        protocol,
        ap.ScriptedHumanIo([ap.says(Task, 'summarise the provider story')]),
    )
    return protocol, [client, worker, reviewer]


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)

    identity = []
    for text in ('openrouter:anthropic/claude', 'ollama:llama3:70b'):
        mid = ap.ModelId.parse(text)
        identity.append(
            f'{text!r} -> provider={mid.provider!r} name={mid.name!r}; '
            f'str(mid)==text: {str(mid) == text}',
        )
    report.note(*identity, title='model identity')

    report.note(
        "OpenAIModel('gpt-5.6-luna', AsyncOpenAI(...))",
        'provider-prefixed names are parsed separately from the live model',
        title='live model',
    )

    _, participants = build()
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
