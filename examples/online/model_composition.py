# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Model composition: fallback, retries, and a spend meter — no provider subclass.

A model is one method, so it composes by nesting:

  primary  = Retrying(Unavailable(...), attempts=2)   # empty primary
  reserve  = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(...))  # answers after fallback
  meter    = Metered(fallback(primary, reserve), tokens=...)
  model    = traced(meter)

Unavailable always fails; Retrying exhausts attempts; fallback hands the call
to the reserve; Metered bounds billed tokens before the *next* call (tokens
are not in Allowance — see ADR metering).

What you will see (sample run):
  === protocol ===
  Client -> Worker : Task(str)
  Worker -> Reviewer : Draft(str)
  Reviewer -> Client : Verdict(str)
  end
  === conversation ===
  Client:Task -> Worker '...'
  Worker:Draft -> Reviewer '...'   # answered by the live reserve after retries
  Reviewer:Verdict -> Client '...'
  === model composition ===
  primary: Unavailable — always fails
  Retrying(attempts=2) then fallback to live reserve
  Metered.billed: Usage(...)
  === a spent meter ===
  TokenLimitError ...

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/model_composition.py
"""

from __future__ import annotations

import asyncio
import os

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import SessionType, msg, project_all, seq

Client, Worker, Reviewer = pa.roles('Client', 'Worker', 'Reviewer')


Verdict = pa.Text('Verdict', 'Accept or a short note.')
Task = pa.Text('Task', 'What must be done, in one sentence.')
Draft = pa.Text('Draft', 'The work product.')

protocol = seq(
    msg[Client, Worker](Task), msg[Worker, Reviewer](Draft), msg[Reviewer, Client](Verdict)
).close()


def _composed() -> tuple[pa.LanguageModel, pa.Metered]:
    # Retrying wraps Unavailable so attempts exhaust before the live reserve.
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    reserve = pa.OpenAIModel('gpt-5.6-luna', client)
    primary = pa.Retrying(pa.Unavailable('the primary endpoint is down'), attempts=2)
    # High budget: live calls bill real tokens; meter still records usage.
    meter = pa.Metered(pa.fallback(primary, reserve), tokens=100_000)
    return pa.traced(meter), meter


def build() -> tuple[SessionType, list[pa.Participant], pa.Metered, pa.MemoryTracer]:
    worker_model, worker_meter = _composed()
    reviewer_model, _reviewer_meter = _composed()
    worker = pa.Agent(worker_model, Worker, 'Do the work in one short draft.', protocol)
    reviewer = pa.Agent(reviewer_model, Reviewer, 'Accept or note one change.', protocol)
    client = pa.Human(
        Client,
        protocol,
        pa.ScriptedHumanIo([pa.says(Task, 'show model composition')]),
    )
    tracer = pa.MemoryTracer()
    return protocol, [client, worker, reviewer], worker_meter, tracer


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)
    _, participants, worker_meter, tracer = build()
    trace = pa.AgentRuntime(protocol, participants, tracer=tracer).run_sync()
    report.conversation(trace)

    report.facts(tracer.events, title='model composition')
    report.note(
        "primary: Unavailable('the primary endpoint is down') — always fails",
        'Retrying(attempts=2) exhausts retries on the primary, then fallback',
        'reserve: OpenAIModel answered',
        f'Metered.billed: {worker_meter.billed}',
        title='model composition details',
    )

    # Pure local demo: zero budget, no live call — TokenLimitError before complete.
    spent = pa.Metered(
        pa.ScriptedLanguageModel(['{"alt": {"label": "Draft", "payload": "unused"}}']),
        tokens=0,
    )
    with report.refusing(pa.TokenLimitError, title='a spent meter'):
        asyncio.run(
            spent.complete(
                pa.StructuredRequest(
                    instructions='n/a',
                    messages=(pa.Message(role='user', content='hi'),),
                    schema_name='spent',
                    schema={'type': 'object'},
                    effort='low',
                ),
            ),
        )


if __name__ == '__main__':
    main()
