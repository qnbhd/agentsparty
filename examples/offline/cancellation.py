"""How a session dies: broadcast cancellation and clean roll-up.

The session is allowed two protocol steps but needs four, so it dies after
the toolbox received the query. Every participant hears ``cancel``. The same
Analyst agent and toolbox then complete a fresh session.

What you will see (exact):
  === protocol ===
  Lead -> Analyst : task(str)
  Analyst -> Tools : search(str)
  Tools -> Analyst {
    hits(list[str]):
      Analyst -> Lead : answer(str)
      end
    offline(str):
      Analyst -> Lead : answer(str)
      end
  }
  === first attempt ===
  the caller still sees the original exception: StepLimitError
  the waiting human was told: ...
  === second attempt ===
  Lead:task -> Analyst 'multiparty session types'
  Analyst:search -> Tools 'multiparty session types'
  Tools:hits -> Analyst [...]
  Analyst:answer -> Lead 'three sources found'

Offline: deterministic double, no API key.

Run::

    uv run python examples/offline/cancellation.py
"""

from __future__ import annotations

import json

import agentsparty as pa
from agentsparty import debug

Lead, Analyst, Tools = pa.roles('Lead', 'Analyst', 'Tools')


Hits = pa.Text.many()('hits')
Task = pa.Text('task')
Search = pa.Text('search')
Answer = pa.Text('answer')
Offline = pa.Text('offline')


@pa.choreography
def build_protocol(c: pa.Chor) -> None:
    c.say(Lead, Analyst, Task)
    c.say(Analyst, Tools, Search)
    with c.decide(Tools, Analyst) as verdict:
        with verdict.case(Hits):
            c.say(Analyst, Lead, Answer)
        with verdict.case(Offline):
            c.say(Analyst, Lead, Answer)


protocol = build_protocol()


async def _search(query: str) -> pa.Choice:
    """Answer a search out of a tiny in-memory index."""
    return pa.reply(Hits, ['Honda et al.', 'Bocchi et al.', 'timed MPST'])


def _analyst(answers: list[str]) -> pa.Agent:
    return pa.Agent(
        pa.ScriptedLanguageModel(answers),
        Analyst,
        'Search then answer the lead.',
        protocol,
    )


def _fresh_lead() -> tuple[pa.Human, pa.ScriptedHumanIo]:
    """A delegating human with one scripted task, and the io that records it."""
    io = pa.ScriptedHumanIo([pa.says(Task, 'multiparty session types')])
    return pa.Human(Lead, protocol, io), io


def main() -> None:
    """Run the session twice: once rolled up, once to completion."""
    report = debug.Report()
    report.protocol(protocol)

    # deterministic double: scripted model answers
    script = [
        json.dumps(
            {'alt': {'label': 'search', 'payload': 'multiparty session types'}},
        ),
        json.dumps({'alt': {'label': 'answer', 'payload': 'three sources found'}}),
    ]
    box = pa.Toolbox(Tools, protocol, [pa.tool_for(Search, _search)])

    report.note('allowance for two steps; protocol needs four', title='first attempt')
    lead, io = _fresh_lead()
    crashed = pa.MemoryTracer()
    try:
        pa.AgentRuntime(
            protocol,
            [lead, _analyst(list(script)), box],
            allowance=pa.Allowance(steps=2),
            tracer=crashed,
        ).run_sync()
    except pa.StepLimitError as error:
        report.note(
            f'the caller still sees the original exception: {type(error).__name__}',
            title='caller',
        )

    [notice] = io.cancellations
    report.note(f'the waiting human was told: {notice.reason}', title='human notice')
    report.facts(crashed.events, title='trace of the rolled-up session')

    report.note('fresh analyst + same toolbox, full allowance', title='second attempt')
    retry_lead, _ = _fresh_lead()
    retried = pa.MemoryTracer()
    trace = pa.AgentRuntime(
        protocol,
        [retry_lead, _analyst(list(script)), box],
        tracer=retried,
    ).run_sync()
    report.conversation(trace)
    report.facts(retried.events, title='trace of the completed session')


if __name__ == '__main__':
    main()
