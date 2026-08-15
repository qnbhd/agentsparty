# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Score a fixed pack of candidates, redo once, then write outreach letters.

What you will see (sample run):
  === protocol ===
  rec round.
    Recruiter -> Scorer : Criteria(str)
    (score three candidates)
    Scorer -> Recruiter : Shortlist([{str: str}])
    Recruiter -> Scorer {
      Redo(): ...
      Reach out(): ...
      Stop(str): ...
    }
  === conversation ===
  Recruiter:Criteria -> Scorer 'systems and types'
  Scorer:Next -> Roster None
  Roster:Candidate -> Scorer {'id': 'c1', 'name': 'Ada', ...}
  Scorer:Score -> Roster 80
  ...
  Recruiter:Redo -> Scorer None
  ...
  Recruiter:Reach out -> Scorer None
  Writer:Letters -> Recruiter ['Dear Ada...', ...]

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/score_leads.py
"""

from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    RawValue,
    SessionType,
    alt,
    msg,
    project_all,
    rec,
    repeat,
    var,
)

Recruiter, Scorer, Writer, Roster = pa.roles('Recruiter', 'Scorer', 'Writer', 'Roster')


CANDIDATE = pa.record('Candidate', id=str, name=str, bio=str)
SCORE = pa.Integer.between(0, 100)
SHORTLIST = CANDIDATE.many(at_most=3)

CLOSE = 'The search is over.'
CLOSED = 'The roster is closed.'

CANDIDATES: tuple[dict[str, str], ...] = (
    {'id': 'c1', 'name': 'Ada', 'bio': 'distributed systems'},
    {'id': 'c2', 'name': 'Bea', 'bio': 'product design'},
    {'id': 'c3', 'name': 'Cal', 'bio': 'session types research'},
)


Recorded = pa.Nothing('Recorded', 'The score is on file.')
Score = SCORE('Score', 'Fit against the criteria, zero to one hundred.')
Candidate = CANDIDATE('Candidate', 'The next candidate on file.')
Top = SHORTLIST('Top', 'The best candidates on file.')
Cleared = pa.Text('Cleared', 'The scores are gone.')
Closed = pa.Text('Closed', CLOSED)
Next = pa.Nothing('Next', 'Ask for the next candidate.')
Rank = pa.Nothing('Rank', 'Ask for the ranked shortlist.')
Reset = pa.Nothing('Reset', "Discard this round's scores.")
Close = pa.Nothing('Close', CLOSE)
Shortlist = SHORTLIST('Shortlist', 'The shortlist for review.')
Criteria = pa.Text('Criteria', 'What matters in a candidate this round.')
Letters = pa.Text.many()('Letters', 'One letter per candidate.')
Acknowledged = pa.Text('Acknowledged', 'Writer acknowledgement.')
Ready = pa.Nothing('Ready', 'Writer acknowledgement.')
ReachOut = pa.Nothing('Reach out', 'Approve the shortlist and write outreach.')
Stop = pa.Text('Stop', 'Abandon the search and say why.')
StandDown = pa.Text('Stand down', 'Why no outreach happens.')
Redo = pa.Nothing('Redo', 'Score again with new criteria.')
Wait = pa.Nothing('Wait', 'No outreach this round.')

SCORE_ONE = (
    msg[Scorer, Roster](Next)
    >> msg[Roster, Scorer](Candidate)
    >> msg[Scorer, Roster](Score)
    >> msg[Roster, Scorer](Recorded)
)


protocol = rec(
    'round',
    msg[Recruiter, Scorer](Criteria)
    >> repeat(3, SCORE_ONE)
    >> msg[Scorer, Roster](Rank)
    >> msg[Roster, Scorer](Top)
    >> msg[Scorer, Recruiter](Shortlist)
    >> alt[Recruiter, Scorer](
        Redo
        >> msg[Scorer, Writer](Wait)
        >> msg[Writer, Scorer](Ready)
        >> msg[Scorer, Roster](Reset)
        >> msg[Roster, Scorer](Cleared)
        >> var('round'),
        ReachOut
        >> msg[Scorer, Writer](Shortlist)
        >> msg[Writer, Recruiter](Letters)
        >> msg[Scorer, Roster](Close)
        >> msg[Roster, Scorer](Closed),
        Stop
        >> msg[Scorer, Writer](StandDown)
        >> msg[Writer, Recruiter](Acknowledged)
        >> msg[Scorer, Roster](Close)
        >> msg[Roster, Scorer](Closed),
    ),
).close()


def _roster_tools() -> list[Any]:
    queue = list(CANDIDATES)
    scores: dict[str, int] = {}
    cursor = 0

    async def next_candidate(_empty: None) -> pa.Choice:
        nonlocal cursor
        item = queue[cursor % len(queue)]
        cursor += 1
        payload: dict[str, RawValue] = dict(item)
        return pa.reply(Candidate, payload)

    async def score(value: int) -> pa.Choice:
        # last handed-out candidate is cursor-1
        item = queue[(cursor - 1) % len(queue)]
        scores[item['id']] = value
        return pa.reply(Recorded, None)

    async def rank(_empty: None) -> pa.Choice:
        ordered = sorted(queue, key=lambda c: scores.get(c['id'], 0), reverse=True)
        top: list[RawValue] = [dict(c) for c in ordered[:3]]
        return pa.reply(Top, top)

    async def reset(_empty: None) -> pa.Choice:
        nonlocal cursor
        scores.clear()
        cursor = 0
        return pa.reply(Cleared, None)

    async def close(_empty: None) -> pa.Choice:
        return pa.reply(Closed, None)

    return [
        pa.tool_for(Next, next_candidate),
        pa.tool_for(Score, score),
        pa.tool_for(Rank, rank),
        pa.tool_for(Reset, reset),
        pa.tool_for(Close, close),
    ]


def build() -> tuple[SessionType, list[pa.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    strict = pa.Repair(attempts=2)
    human = pa.ScriptedHumanIo(
        [
            pa.says(Criteria, 'systems and types'),
            pa.says(Redo, None),
            pa.says(Criteria, 'research depth'),
            pa.says(ReachOut, None),
        ],
    )
    scorer = pa.Agent(
        model,
        Scorer,
        (
            'Each round: for three candidates, Next then Score (integer 0-100). '
            'Then Rank, and forward Top as Shortlist to the Recruiter. '
            'On Redo: Wait, then Reset, then the next round starts. '
            'On Reach out: forward Shortlist to Writer, then Close the roster. '
            'On Stop: Stand down with the reason, then Close.'
        ),
        protocol,
        repair=strict,
    )
    writer = pa.Agent(
        model,
        Writer,
        (
            'On Wait: reply Ready. '
            'On Shortlist: write Letters as a list of one short outreach string '
            'per candidate. On Stand down: reply Acknowledged with a short note.'
        ),
        protocol,
        repair=strict,
    )
    return protocol, [
        pa.Human(Recruiter, protocol, human),
        scorer,
        writer,
        pa.Toolbox(Roster, protocol, _roster_tools()),
    ]


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
