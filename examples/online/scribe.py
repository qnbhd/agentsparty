# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Compaction as choreography: a Scribe digests work into the protocol.

Worker is a live Agent. Scribe stays a Machine that digests every N progress
units, then finishes. Digests are protocol messages — journalled and replayed
(ADR 0008), not a hidden memory middleware call.

What you will see (sample run):
  === protocol ===
  rec work {
    Worker -> Scribe : Progress(str)
    Scribe -> Worker {
      Carry on(): work
      Digest(str): work
      Finish(str): end
    }
  }
  === conversation ===
  Worker:Progress -> Scribe '...'
  Scribe:Carry on -> Worker
  ...
  Scribe:Digest -> Worker 'summary of ...'
  ...
  Scribe:Finish -> Worker 'done: ...'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/scribe.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    Label,
    alt,
    msg,
    project,
    rec,
    var,
)

Worker, Scribe = pa.roles('Worker', 'Scribe')

Progress = pa.Text('Progress')
CarryOn = pa.Nothing('Carry on')
Digest = pa.Text('Digest')
Finish = pa.Text('Finish')

protocol = rec(
    'work',
    msg[Worker, Scribe](Progress)
    >> alt[Scribe, Worker](
        CarryOn >> var('work'),
        Digest >> var('work'),
        Finish,
    ),
).close()


def _scribe_decide(threshold: int = 3):
    """Digest every *threshold* units of progress, then finish."""

    def decide(view: pa.View) -> pa.Choice:
        offered = {label.name for label in view.offered}
        if not ({'Carry on', 'Digest', 'Finish'} & offered):
            return pa.Choice(min(view.offered))
        progresses = [e for e in view.seen if e.label == Label('Progress')]
        digests = [e for e in view.seen if e.label == Label('Digest')]
        if len(progresses) >= threshold * 2:
            units = [str(e.payload) for e in progresses]
            return pa.says(Finish, f'done: {", ".join(units)}')
        if (
            len(progresses) > 0
            and len(progresses) % threshold == 0
            and len(digests) < len(progresses) // threshold
        ):
            recent = [str(e.payload) for e in progresses[-threshold:]]
            return pa.says(Digest, f'summary of {", ".join(recent)}')
        return pa.says(CarryOn)

    return decide


def build_participants(threshold: int = 3) -> list:
    """Live Worker + Scribe machine; *threshold* units per digest."""
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    worker = pa.Agent(
        model,
        Worker,
        'Report short progress units as Progress when offered. '
        f'Emit about {threshold * 2} distinct units (one sentence each). '
        'After Carry on or Digest, send the next Progress.',
        protocol,
        brief=pa.Recent(Worker, keep=4),
    )
    return [
        worker,
        pa.Machine(Scribe, protocol, _scribe_decide(threshold)),
    ]


def main() -> None:
    report = debug.Report()
    for role in (Worker, Scribe):
        project(protocol, role)

    report.protocol(protocol)
    report.note(
        'Worker brief policy: Recent(keep=4) — digests stay in the window;',
        'older Progress envelopes fall out. Resume still matches live because',
        'every Digest is a journalled Decision.',
        title='brief policy',
    )

    participants = build_participants(threshold=3)
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
