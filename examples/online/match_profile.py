# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Rank open positions for a CV; best score first is a codec, not a hope.

What you will see (sample run):
  === protocol ===
  Candidate -> Reader : CV(str)
  Reader -> Matcher : Profile([str])
  Matcher -> Positions : Search([str])
  Positions -> Matcher : Openings([str])
  Matcher -> Candidate : Matches(Matches)
  end
  === conversation ===
  Candidate:CV -> Reader 'python backend, multiparty session protocols'
  Reader:Profile -> Matcher ['python', 'protocols', ...]
  Matcher:Search -> Positions [...]
  Positions:Openings -> Matcher ['Backend engineer — python, protocols', ...]
  Matcher:Matches -> Candidate (Match(position='Backend engineer', score=9, ...), ...)

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/match_profile.py
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    RawValue,
    SessionType,
    msg,
    project_all,
    seq,
)

Candidate, Reader, Matcher, Positions = ap.roles(
    'Candidate',
    'Reader',
    'Matcher',
    'Positions',
)

MATCHES_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'position': {'type': 'string'},
            'score': {'type': 'integer'},
            'reason': {'type': 'string'},
        },
        'required': ['position', 'score', 'reason'],
        'additionalProperties': False,
    },
}


@dataclass(frozen=True, slots=True)
class Match:
    position: str
    score: int
    reason: str


def parse_matches(text: str) -> tuple[Match, ...]:
    data = json.loads(text)
    return tuple(
        Match(
            position=str(row['position']),
            score=int(row['score']),
            reason=str(row['reason']),
        )
        for row in data
    )


MATCHES = ap.json_model('Matches', MATCHES_SCHEMA, parse_matches).where(
    'at most three matches, ordered by descending score',
    lambda ms: len(ms) <= 3 and all(a.score >= b.score for a, b in pairwise(ms)),
)


Openings = ap.Text.many()('Openings', 'Positions that mention those skills.')
Search = ap.Text.many()('Search', 'Skills to search positions by.')
Matches = MATCHES('Matches', 'Up to three positions, best first.')
CV = ap.Text('CV', 'The curriculum vitae, as text.')
Profile = ap.Text.many()('Profile', 'Skills and experience, one per line.')

protocol = seq(
    msg[Candidate, Reader](CV),
    msg[Reader, Matcher](Profile),
    msg[Matcher, Positions](Search),
    msg[Positions, Matcher](Openings),
    msg[Matcher, Candidate](Matches),
).close()

OPENINGS: tuple[str, ...] = (
    'Backend engineer — python, protocols',
    'Frontend engineer — react, css',
    'Platform engineer — python, systemd',
)


def _positions_tools() -> list[Any]:
    async def search(skills: list[str]) -> ap.Choice:
        lowered = [skill.lower() for skill in skills]
        hits: list[RawValue] = [
            opening for opening in OPENINGS if any(skill in opening.lower() for skill in lowered)
        ]
        return ap.reply(Openings, hits)

    return [ap.tool_for(Search, search)]


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    strict = ap.Repair(attempts=2)
    reader = ap.Agent(
        model,
        Reader,
        'Extract a short list of skill strings from the CV (e.g. python, protocols).',
        protocol,
    )
    matcher = ap.Agent(
        model,
        Matcher,
        (
            'Search openings with the profile skills. '
            'Matches must be a JSON array of at most three objects with keys '
            'position, score (integer), reason — ordered by descending score.'
        ),
        protocol,
        repair=strict,
    )
    candidate = ap.Human(
        Candidate,
        protocol,
        ap.ScriptedHumanIo([ap.says(CV, 'python backend, multiparty session protocols')]),
    )
    participants: list[ap.Participant] = [
        candidate,
        reader,
        matcher,
        ap.Toolbox(Positions, protocol, _positions_tools()),
    ]
    return protocol, participants


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
