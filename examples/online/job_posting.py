# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Research culture and industry, then draft a publishable job posting.

Sample run (conversation sketch, 3-6 lines)::

    Hiring:Company -> Researcher 'typed agents startup hiring a backend engineer'
    Researcher:Culture -> Writer '…'
    Researcher:Requirements -> Writer {skills, experience, qualities}
    Researcher:Industry -> Reviewer '…'
    Writer:Draft -> Reviewer '…'
    Reviewer:Publish -> Writer '…'
    Writer:Posting -> Hiring '…'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/job_posting.py
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
    seq,
)

Hiring, Researcher, Writer, Reviewer = ap.roles(
    'Hiring',
    'Researcher',
    'Writer',
    'Reviewer',
)

POSTING = 'The posting as it should be published.'
DRAFT = 'The drafted posting.'

REQUIREMENTS_SCHEMA = {
    'type': 'object',
    'properties': {
        'skills': {'type': 'array', 'items': {'type': 'string'}},
        'experience': {'type': 'array', 'items': {'type': 'string'}},
        'qualities': {'type': 'array', 'items': {'type': 'string'}},
    },
    'required': ['skills', 'experience', 'qualities'],
    'additionalProperties': False,
}


@dataclass(frozen=True, slots=True)
class Requirements:
    skills: tuple[str, ...]
    experience: tuple[str, ...]
    qualities: tuple[str, ...]


def parse_requirements(text: str) -> Requirements:
    data = json.loads(text)
    skills = tuple(data['skills'])
    experience = tuple(data['experience'])
    qualities = tuple(data['qualities'])
    if not (skills and experience and qualities):
        raise ValueError('each section must be a non-empty list')
    return Requirements(skills, experience, qualities)


# refine wraps json_model so holds receives Requirements, not a dict.
REQUIREMENTS = ap.json_model('Requirements', REQUIREMENTS_SCHEMA, parse_requirements).where(
    'no empty section',
    lambda r: all((r.skills, r.experience, r.qualities)),
)


Draft = ap.Text('Draft', DRAFT)
Industry = ap.Text('Industry', 'Market context the reviewer must weigh.')
Publish = ap.Text('Publish', POSTING)
Posting = ap.Text('Posting', POSTING)
RequirementsCase = REQUIREMENTS('Requirements', 'Skills, experience and qualities.')
Company = ap.Text('Company', 'Domain, description and hiring need.')
Culture = ap.Text('Culture', 'What the company is like to work at.')
Rewrite = ap.Text('Rewrite', 'What is missing from the draft.')

protocol = seq(
    msg[Hiring, Researcher](Company),
    msg[Researcher, Writer](Culture),
    msg[Researcher, Writer](RequirementsCase),
    msg[Researcher, Reviewer](Industry),
    msg[Writer, Reviewer](Draft),
    alt[Reviewer, Writer](
        Publish.then(msg[Writer, Hiring](Posting)),
        Rewrite.then(
            msg[Writer, Reviewer](Draft),
            msg[Reviewer, Writer](Publish),
            msg[Writer, Hiring](Posting),
        ),
    ),
).close()


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    researcher = ap.Agent(
        model,
        Researcher,
        'Research in three steps. Culture is plain prose. Requirements is JSON '
        'with three non-empty string arrays: skills, experience, qualities '
        '(all required, no empty list). Industry is a short market paragraph '
        'for the reviewer.',
        protocol,
        repair=ap.Repair(attempts=2),
    )
    writer = ap.Agent(
        model,
        Writer,
        'Draft a concise job posting as plain text Draft. After Publish, send '
        'Posting with the publish-ready wording (may match Publish).',
        protocol,
    )
    reviewer = ap.Agent(
        model,
        Reviewer,
        'Weigh Draft against Industry. Prefer Publish with the final posting '
        'text when the draft is usable; otherwise Rewrite naming one gap, then '
        'Publish the revised Draft.',
        protocol,
    )
    hiring = ap.Human(
        Hiring,
        protocol,
        ap.ScriptedHumanIo(
            [ap.says(Company, 'typed agents startup hiring a backend engineer')],
        ),
    )
    return protocol, [hiring, researcher, writer, reviewer]


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
