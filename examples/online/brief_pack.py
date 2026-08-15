# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Build a meeting brief by consolidating research along a chain (not a join).

What you will see (sample run):
  === protocol ===
  Exec -> Researcher : Meeting(str)
  Researcher -> Analyst : Participants(str)
  Analyst -> Strategist : Dossier({str: str})
  Strategist -> Briefer : Pack({str: str})
  Briefer -> Exec : Brief({str: str})
  end
  === conversation ===
  Exec:Meeting -> Researcher 'corridor pilot; Ada and Grace; decide next week'
  Researcher:Participants -> Analyst 'Ada CTO; Grace CFO'
  Analyst:Dossier -> Strategist {'participants': '...', 'industry': '...'}
  Strategist:Pack -> Briefer {..., 'angles': '...'}
  Briefer:Brief -> Exec {..., 'recommendation': '...'}

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/brief_pack.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    msg,
    par,
    project_all,
)

Exec, Researcher, Analyst, Strategist, Briefer = ap.roles(
    'Exec',
    'Researcher',
    'Analyst',
    'Strategist',
    'Briefer',
)


DOSSIER = ap.record('Dossier', participants=str, industry=str)
PACK = ap.record('Pack', participants=str, industry=str, angles=str)
BRIEF = ap.record('Brief', participants=str, industry=str, angles=str, recommendation=str)

# Chain order: each role consolidates once for the next (not a fan-out join).
Meeting = ap.Text('Meeting', 'Participants, context and objective.')
Participants = ap.Text('Participants', 'One line per participant.')
Dossier = DOSSIER('Dossier', 'Participants plus industry context.')
Pack = PACK('Pack', 'The dossier plus talking points.')
Brief = BRIEF('Brief', 'The briefing document.')

# Labels used only in the illegal-par demos below.
P = ap.Text('P')
Q = ap.Text('Q')
Join = ap.Text('Join')

protocol = (
    msg[Exec, Researcher](Meeting)
    >> msg[Researcher, Analyst](Participants)
    >> msg[Analyst, Strategist](Dossier)
    >> msg[Strategist, Briefer](Pack)
    >> msg[Briefer, Exec](Brief)
).close()


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    strict = ap.Repair(attempts=2)
    researcher = ap.Agent(
        model,
        Researcher,
        'List the people in the room as one short Participants string.',
        protocol,
    )
    analyst = ap.Agent(
        model,
        Analyst,
        (
            "Send Dossier as a dict with exactly keys 'participants' and "
            "'industry' (short string values)."
        ),
        protocol,
        repair=strict,
    )
    strategist = ap.Agent(
        model,
        Strategist,
        (
            "Send Pack as a dict with keys 'participants', 'industry', and "
            "'angles' (short talking points)."
        ),
        protocol,
        repair=strict,
    )
    briefer = ap.Agent(
        model,
        Briefer,
        (
            "Send Brief as a dict with keys 'participants', 'industry', "
            "'angles', and 'recommendation'."
        ),
        protocol,
        repair=strict,
    )
    exec_ = ap.Human(
        Exec,
        protocol,
        ap.ScriptedHumanIo(
            [ap.says(Meeting, 'corridor pilot; Ada and Grace; decide next week')],
        ),
    )
    return protocol, [exec_, researcher, analyst, strategist, briefer]


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())

    with report.refusing(ValueError, title='why par refuses fan-out joins'):
        (
            par(
                msg[Researcher, Analyst](P),
                msg[Strategist, Briefer](Q),
            )
            >> msg[Exec, Researcher](Join)
        ).close()
    with report.refusing(ValueError, title='why par refuses a second join'):
        par(
            msg[Researcher, Analyst](P),
            msg[Researcher, Strategist](Q),
        ).close()


if __name__ == '__main__':
    main()
