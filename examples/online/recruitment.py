# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Source, rank, and contact candidates; a missing role fails at bind time.

Sample run (conversation sketch, 3-6 lines)::

    Manager:Requirements -> Sourcer 'staff research engineer'
    Sourcer:Candidates -> Matcher [{name, position, location}, …]
    Matcher:Ranked -> Communicator […]
    Communicator:Outreach -> Reporter ['…', …]
    Reporter:Report -> Manager '…'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/recruitment.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    msg,
    project_all,
    seq,
)
from agentsparty.protocol.language import endpoint

Manager, Sourcer, Matcher, Communicator, Reporter = pa.roles(
    'Manager',
    'Sourcer',
    'Matcher',
    'Communicator',
    'Reporter',
)


PROFILE = pa.record('Profile', name=str, position=str, location=str)
PROFILES = PROFILE.many(1, 5)


Report = pa.Text('Report', 'Who was found, ranked and contacted.')
Candidates = PROFILES('Candidates', 'Profiles that look plausible.')
Ranked = PROFILES('Ranked', 'The same profiles, best first.')
Outreach = pa.Text.many()('Outreach', 'One message per candidate.')
Requirements = pa.Text('Requirements', 'The role being filled.')
Paused = pa.Text('Paused')

protocol = seq(
    msg[Manager, Sourcer](Requirements),
    msg[Sourcer, Matcher](Candidates),
    msg[Matcher, Communicator](Ranked),
    msg[Communicator, Reporter](Outreach),
    msg[Matcher, Reporter](Ranked),
    msg[Sourcer, Reporter](Candidates),
    msg[Reporter, Manager](Report),
).close()

_PROFILES_SHAPE = (
    'Profiles are a JSON list of one to five objects; each object has '
    'string keys name, position, and location (all required).'
)


def build() -> tuple[SessionType, list[pa.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    return protocol, [
        pa.Human(
            Manager,
            protocol,
            pa.ScriptedHumanIo([pa.says(Requirements, 'staff research engineer')]),
        ),
        pa.Agent(
            model,
            Sourcer,
            f'Find plausible candidate profiles. {_PROFILES_SHAPE} Send '
            'Candidates twice: first to Matcher, then later to Reporter, with '
            'the same list both times.',
            protocol,
            repair=pa.Repair(attempts=2),
        ),
        pa.Agent(
            model,
            Matcher,
            f'Rank profiles best first. {_PROFILES_SHAPE} Send Ranked twice: '
            'first to Communicator, then later to Reporter.',
            protocol,
            repair=pa.Repair(attempts=2),
        ),
        pa.Agent(
            model,
            Communicator,
            'Draft Outreach as a JSON list of short plain-text messages, one '
            'per candidate, in rank order.',
            protocol,
            repair=pa.Repair(attempts=2),
        ),
        pa.Agent(
            model,
            Reporter,
            'After receiving Outreach, Ranked, and Candidates, send Report as '
            'a short prose summary of who was found, ranked, and contacted.',
            protocol,
        ),
    ]


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)
    _, participants = build()
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    with report.refusing(ValueError, title='a missing participant'):
        pa.AgentRuntime(protocol, participants[:-1])
    expanded = (
        endpoint.offer(Manager, Requirements, Paused)
        >> endpoint.send(Matcher, 'Candidates', PROFILES)
        >> endpoint.send(Reporter, 'Candidates', PROFILES)
    ).close()
    tolerant = pa.Agent(model, Sourcer, 'Find profiles.', protocol, declares=expanded)
    rest = [p for p in participants if p.role.name != 'Sourcer']
    pa.AgentRuntime(protocol, [tolerant, *rest])
    report.note(
        'Sourcer declares= accepts extra Paused and still binds',
        title='a declared endpoint',
    )
    forbidden = (
        endpoint.recv(Manager, 'Requirements', pa.Text)
        >> endpoint.send(Matcher, 'Candidates', PROFILES)
        >> endpoint.send(Reporter, 'Leaked', pa.Text)
    ).close()
    with report.refusing(pa.ConformanceError, title='a refused endpoint'):
        pa.Agent(model, Sourcer, 'Find profiles.', protocol, declares=forbidden)


if __name__ == '__main__':
    main()
