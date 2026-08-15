# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]", "pydantic"]
# ///
"""Plan a surprise trip the traveller never sees until departure logistics.

What you will see (sample run):
  === protocol ===
  Traveller -> Planner : Preferences(str)
  Planner -> Scout : Shortlist([str])
  Scout -> Compiler : Vetted([str])
  Compiler -> Concierge : Itinerary(Itinerary)
  Concierge -> Traveller : Departure(str)
  Traveller -> Concierge {
    Go(): ...
    Reveal(str): ...
  }
  === conversation ===
  Traveller:Preferences -> Planner 'July, mid budget, quiet coast walks'
  Planner:Shortlist -> Scout ['harbour walk', ...]
  Scout:Vetted -> Compiler ['harbour walk', 'cliff path']
  Compiler:Itinerary -> Concierge Itinerary(...)
  Concierge:Departure -> Traveller 'Gate B, 09:00 — bring a light coat'
  Traveller:Go -> Concierge None
  Concierge:Confirmed -> Compiler None
  Itinerary: not reachable by Traveller

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/surprise_trip.py
"""

from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project,
    project_all,
    render,
    seq,
)

Traveller, Planner, Scout, Compiler, Concierge = ap.roles(
    'Traveller',
    'Planner',
    'Scout',
    'Compiler',
    'Concierge',
)


class Activity(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    location: str
    why_it_suits: str


class DayPlan(BaseModel):
    model_config = ConfigDict(extra='forbid')

    date: str
    activities: list[Activity]


class Itinerary(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    days: list[DayPlan]


DayPlan.model_rebuild()
Itinerary.model_rebuild()


def _strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Inline $defs and force additionalProperties:false (OpenAI strict mode)."""
    raw: dict[str, Any] = model.model_json_schema()
    defs: dict[str, Any] = raw.pop('$defs', {})

    def fix(node: Any) -> Any:
        if isinstance(node, dict):
            if '$ref' in node:
                ref = str(node['$ref']).rsplit('/', 1)[-1]
                return fix(defs[ref])
            out = {k: fix(v) for k, v in node.items() if k != 'title'}
            if out.get('type') == 'object':
                out['additionalProperties'] = False
                props = out.get('properties') or {}
                out['required'] = list(props.keys())
            return out
        if isinstance(node, list):
            return [fix(item) for item in node]
        return node

    return fix(raw)  # type: ignore[return-value]


ITINERARY = ap.json_model(
    'Itinerary',
    _strict_schema(Itinerary),
    Itinerary.model_validate_json,
)


Preferences = ap.Text('Preferences', 'Dates, budget and what the traveller likes.')
Shortlist = ap.Text.many()('Shortlist', 'Candidate activities.')
Vetted = ap.Text.many()('Vetted', 'Activities worth including.')
ItineraryMsg = ITINERARY('Itinerary', 'The full itinerary, day by day.')
Departure = ap.Text('Departure', 'When and where to be, and nothing else.')
Go = ap.Nothing('Go', 'Accept the surprise as it stands.')
Confirmed = ap.Nothing('Confirmed', 'The traveller is going.')
Reveal = ap.Text('Reveal', 'Why the traveller wants the surprise spoiled.')
Spoiled = ap.Text('Spoiled', 'Why the surprise was dropped.')
Preview = ITINERARY('Preview', 'The full plan, spoiled on request.')

protocol = seq(
    msg[Traveller, Planner](Preferences),
    msg[Planner, Scout](Shortlist),
    msg[Scout, Compiler](Vetted),
    msg[Compiler, Concierge](ItineraryMsg),
    msg[Concierge, Traveller](Departure),
    alt[Traveller, Concierge](
        Go >> msg[Concierge, Compiler](Confirmed),
        Reveal >> msg[Concierge, Compiler](Spoiled),
    ),
).close()

# Same shape plus a leak: Concierge shows the plan to Traveller.
SPOILED = seq(
    msg[Traveller, Planner](Preferences),
    msg[Planner, Scout](Shortlist),
    msg[Scout, Compiler](Vetted),
    msg[Compiler, Concierge](ItineraryMsg),
    msg[Concierge, Traveller](Departure),
    msg[Concierge, Traveller](Preview),
    alt[Traveller, Concierge](
        Go >> msg[Concierge, Compiler](Confirmed),
        Reveal >> msg[Concierge, Compiler](Spoiled),
    ),
).close()


def _concierge() -> ap.Machine:
    def decide(view: ap.View) -> ap.Choice:
        names = {label.name for label in view.offered}
        if Departure.label.name in names:
            return ap.says(Departure, 'Gate B, 09:00 — bring a light coat')
        if Confirmed.label.name in names:
            return ap.says(Confirmed)
        if Spoiled.label.name in names:
            return ap.says(Spoiled, 'traveller asked to know')
        return ap.Choice(min(view.offered))

    return ap.Machine(Concierge, protocol, decide)


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    planner = ap.Agent(
        model,
        Planner,
        'Propose a Shortlist of three short candidate activity names as a list of strings.',
        protocol,
    )
    scout = ap.Agent(
        model,
        Scout,
        'Keep only activities worth including; send Vetted as a list of short strings.',
        protocol,
    )
    compiler = ap.Agent(
        model,
        Compiler,
        (
            'Compile a full Itinerary JSON object with keys name and days; '
            'each day has date and activities; each activity has name, location, '
            'why_it_suits. At least one day.'
        ),
        protocol,
        repair=ap.Repair(attempts=2),
    )
    traveller = ap.Human(
        Traveller,
        protocol,
        ap.ScriptedHumanIo(
            [
                ap.says(Preferences, 'July, mid budget, quiet coast walks'),
                ap.says(Go, None),
            ],
        ),
    )
    return protocol, [traveller, planner, scout, compiler, _concierge()]


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)
    _, participants = build()
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())

    hidden = render(project(protocol, Traveller))
    assert 'Itinerary' not in hidden
    report.note('Itinerary: not reachable by Traveller', title='what the traveller cannot learn')
    leaked = render(project(SPOILED, Traveller))
    assert 'Itinerary' in leaked
    report.note('Itinerary: reachable by Traveller (on SPOILED)', title='spoiled protocol')


if __name__ == '__main__':
    main()
