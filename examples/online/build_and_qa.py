# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Implement a small program; review and rework until the chief ships it.

Sample run (conversation sketch, 3-6 lines)::

    Product:Spec -> Engineer 'a function that adds two numbers'
    Engineer:Code -> Reviewer '```…```'
    Reviewer:Defects -> Chief '…'   # or Clean
    Chief:Rework -> Engineer '…'    # or Ship
    Engineer:Release -> Product '```…```'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/build_and_qa.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.choreography import Chor, choreography
from agentsparty.protocol import (
    SessionType,
    project_all,
)

Product, Engineer, Reviewer, Chief = ap.roles('Product', 'Engineer', 'Reviewer', 'Chief')

CODE = ap.Text.where('a fenced code block', lambda s: s.count('```') >= 2)
REWORK = 'What must change before the next round.'
ITERATING = 'Progress note.'


# Same REWORK intent on both Rework arms so merge succeeds; Reviewer is told
# Again / Stand down so Clean vs Ship/Rework projects (recipe §4.2).


Spec = ap.Text('Spec', 'What the program must do.')
Code = CODE('Code', 'The current implementation.')
Clean = CODE('Clean', 'Code in which no defect was found.')
Iterating = ap.Text('Iterating', ITERATING)
Release = CODE('Release', 'The released program.')
Again = ap.Nothing('Again', 'Another review is coming.')
Ship = ap.Nothing('Ship', 'Release the implementation.')
StandDown = ap.Nothing('Stand down', 'No more review.')
Defects = ap.Text('Defects', 'The defects found, one per line.')
Rework = ap.Text('Rework', REWORK)


@choreography
def build_and_qa(c: Chor) -> None:
    c.say(Product, Engineer, Spec)
    with c.loop('build') as build:
        c.say(Engineer, Reviewer, Code)
        with c.decide(Reviewer, Chief) as review:
            with review.case(Clean), c.decide(Chief, Engineer) as decision:
                with decision.case(Ship):
                    c.say(Engineer, Reviewer, StandDown)
                    c.say(Engineer, Product, Release)
                with decision.case(Rework):
                    c.say(Engineer, Reviewer, Again)
                    c.say(Engineer, Product, Iterating)
                    build.again()
            with review.case(Defects):
                c.say(Chief, Engineer, Rework)
                c.say(Engineer, Reviewer, Again)
                c.say(Engineer, Product, Iterating)
                build.again()


protocol = build_and_qa()


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    product = ap.Human(
        Product,
        protocol,
        ap.ScriptedHumanIo([ap.says(Spec, 'a function that adds two numbers')]),
    )
    return protocol, [
        product,
        ap.Agent(
            model,
            Engineer,
            'Implement the Spec. Code and Release must be a fenced code block '
            'containing at least one pair of triple backticks (``` … ```). After '
            'Rework or Defects path: send Again (empty), then Iterating with a '
            'short progress note, then a new Code. After Ship: Stand down '
            '(empty), then Release with the final fenced code.',
            protocol,
            repair=ap.Repair(attempts=2),
        ),
        ap.Agent(
            model,
            Reviewer,
            'Review Code. If wrong, Defects lists defects one per line. If '
            'correct, Clean echoes the code still as a fenced block with ```.',
            protocol,
            repair=ap.Repair(attempts=2),
        ),
        ap.Agent(
            model,
            Chief,
            'After Clean, prefer Ship when the code meets the Spec; otherwise '
            'Rework with one concrete change. After Defects, always Rework '
            'naming what must change.',
            protocol,
        ),
    ]


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
