# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Plan a three-day trip; the plan codec enforces exactly three days.

Sample run (conversation sketch, 3-6 lines)::

    Traveller:Wishes -> Selector 'Paris area, early June, museums and food'
    Selector:City -> Local 'Lyon — …'
    Local:Guide -> Concierge '…'
    Concierge:Estimate -> Prices [120.0, 80.5, 45.0]
    Prices:Total -> Concierge 245.5
    Concierge:Itinerary -> Traveller [{date, morning, evening}, … x3]
    Traveller:Book -> Concierge

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/trip.py
"""

from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
    seq,
)

Traveller, Selector, Local, Concierge, Prices = pa.roles(
    'Traveller',
    'Selector',
    'Local',
    'Concierge',
    'Prices',
)


DAY = pa.record('Day', date=str, morning=str, evening=str)
PLAN = DAY.many(3, 3)


Total = pa.Number('Total', 'The sum of the costs.')
Held = pa.Text('Held', 'Confirmation from the ledger.')
Released = pa.Text('Released', 'Confirmation from the ledger.')
Estimate = pa.Number.many()('Estimate', 'Costs to add up.')
Hold = pa.Number('Hold', 'The amount to hold.')
Release = pa.Number('Release', 'The amount to release.')
Itinerary = PLAN('Itinerary', 'A three-day plan.')
Book = pa.Nothing('Book', 'Accept the itinerary.')
Change = pa.Text('Change', 'What to change about the plan.')
Guide = pa.Text('Guide', 'What only a local would know.')
Wishes = pa.Text('Wishes', 'Origin, dates and interests.')
City = pa.Text('City', 'The chosen city and why.')

protocol = seq(
    msg[Traveller, Selector](Wishes),
    msg[Selector, Local](City),
    msg[Local, Concierge](Guide),
    msg[Concierge, Prices](Estimate),
    msg[Prices, Concierge](Total),
    msg[Concierge, Traveller](Itinerary),
    alt[Traveller, Concierge](
        Book >> msg[Concierge, Prices](Hold) >> msg[Prices, Concierge](Held),
        Change >> msg[Concierge, Prices](Release) >> msg[Prices, Concierge](Released),
    ),
).close()


def _price_tools() -> list[Any]:
    async def estimate(costs: list[float]) -> pa.Choice:
        return pa.reply(Total, sum(costs))

    async def hold(amount: float) -> pa.Choice:
        return pa.reply(Held, f'held {amount}')

    async def release(amount: float) -> pa.Choice:
        return pa.reply(Released, f'released {amount}')

    return [
        pa.tool_for(Estimate, estimate),
        pa.tool_for(Hold, hold),
        pa.tool_for(Release, release),
    ]


def build() -> tuple[SessionType, list[pa.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    selector = pa.Agent(
        model,
        Selector,
        'Pick one city that fits the wishes. City is one short sentence naming '
        'the place and why it fits.',
        protocol,
    )
    local = pa.Agent(
        model,
        Local,
        'Share what only a local would know in a few sentences as Guide.',
        protocol,
    )
    concierge = pa.Agent(
        model,
        Concierge,
        'Build a three-day plan. Estimate is a list of two to four numeric '
        'costs (floats). Itinerary must be a JSON list of exactly three '
        'objects; each object has string keys date, morning, and evening '
        '(no other keys required). After Book, Hold with the Total amount '
        'you received from Prices.',
        protocol,
        repair=pa.Repair(1),
    )
    traveller = pa.Human(
        Traveller,
        protocol,
        pa.ScriptedHumanIo(
            [
                pa.says(Wishes, 'Paris area, early June, museums and food'),
                pa.says(Book, None),
            ],
        ),
    )
    participants: list[pa.Participant] = [
        traveller,
        selector,
        local,
        concierge,
        pa.Toolbox(Prices, protocol, _price_tools()),
    ]
    return protocol, participants


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
