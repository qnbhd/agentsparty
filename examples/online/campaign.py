# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Draft a campaign: research, strategy, idea, and approved ad copy.

Sample run (conversation sketch, 3-6 lines)::

    Client:Domain -> Analyst 'B2B tooling for agent crews'
    Analyst:Research -> Strategist '…'
    Strategist:Strategy -> Creative {name, tactics, channels}
    Strategist:Idea -> Creative '…'
    Creative:Copy -> Director {title, body}
    Director:Approve -> Creative
    Creative:Campaign -> Client {title, body}

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/campaign.py
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    project_all,
)

Client, Analyst, Strategist, Creative, Director = pa.roles(
    'Client',
    'Analyst',
    'Strategist',
    'Creative',
    'Director',
)

STRATEGY_SCHEMA = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'tactics': {'type': 'array', 'items': {'type': 'string'}},
        'channels': {'type': 'array', 'items': {'type': 'string'}},
    },
    'required': ['name', 'tactics', 'channels'],
    'additionalProperties': False,
}


@dataclass(frozen=True, slots=True)
class Strategy:
    name: str
    tactics: tuple[str, ...]
    channels: tuple[str, ...]


def parse_strategy(text: str) -> Strategy:
    data = json.loads(text)
    try:
        return Strategy(
            name=str(data['name']),
            tactics=tuple(data['tactics']),
            channels=tuple(data['channels']),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f'invalid strategy: {exc}') from exc


STRATEGY = pa.json_model('Strategy', STRATEGY_SCHEMA, parse_strategy)


COPY = pa.record('Copy', title=str, body=str)
COPY_INTENT = 'Title and body of the ad copy.'
CAMPAIGN = 'The approved campaign copy.'
APPROVE = 'Ship the copy as it stands.'


Copy = COPY('Copy', COPY_INTENT)
Idea = pa.Text('Idea', 'One campaign idea and its audience.')
Approve = pa.Nothing('Approve', APPROVE)
Campaign = COPY('Campaign', CAMPAIGN)
StrategyCase = STRATEGY('Strategy', 'Name, tactics and channels.')
Domain = pa.Text('Domain', 'The customer domain and the project.')
Research = pa.Text('Research', 'What the market looks like.')
Rework = pa.Text('Rework', 'One sharp critique, at most twenty-five words.')


@pa.choreography
def campaign(c: pa.Chor) -> None:
    """Research and strategy feed one draft, which the director gates."""
    c.say(Client, Analyst, Domain)
    c.say(Analyst, Strategist, Research)
    c.say(Strategist, Creative, StrategyCase)
    c.say(Strategist, Creative, Idea)
    c.say(Creative, Director, Copy)
    with c.decide(Director, Creative) as verdict:
        with verdict.case(Approve):
            c.say(Creative, Client, Campaign)
        with verdict.case(Rework):
            # One rework round only: the second Copy is approved, not re-judged.
            c.say(Creative, Director, Copy)
            c.say(Director, Creative, Approve)
            c.say(Creative, Client, Campaign)


protocol = campaign()


def build() -> tuple[SessionType, list[pa.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    analyst = pa.Agent(
        model,
        Analyst,
        'Research the market. Research is a short paragraph of plain prose.',
        protocol,
    )
    strategist = pa.Agent(
        model,
        Strategist,
        'First send Strategy as JSON with string name, non-empty tactics array, '
        'and non-empty channels array (all three required). Then send Idea as '
        'one short sentence naming the audience.',
        protocol,
        repair=pa.Repair(1),
    )
    creative = pa.Agent(
        model,
        Creative,
        'Write ad copy. Copy and Campaign are objects with string keys title '
        'and body (both required). After Approve, send Campaign with the '
        'approved title and body.',
        protocol,
        repair=pa.Repair(attempts=2),
    )
    director = pa.Agent(
        model,
        Director,
        'Approve copy that has a clear title and body. Prefer Approve when the '
        'copy is usable; otherwise Rework with one sharp critique in at most '
        'twenty-five words, then Approve the revised Copy.',
        protocol,
    )
    client = pa.Human(
        Client,
        protocol,
        pa.ScriptedHumanIo([pa.says(Domain, 'B2B tooling for agent crews')]),
    )
    return protocol, [client, analyst, strategist, creative, director]


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
