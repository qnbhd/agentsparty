# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Lint markdown until the linter reports Clean, then return the fixed document.

What you will see (sample run):
  === protocol ===
  Author -> Fixer : Document(str)
  rec pass.
    Fixer -> Linter : Scan(str)
    Linter -> Fixer {
      Findings([str]):
        Fixer -> Author : Progress(int)
        ...
      Clean():
        Fixer -> Author : Clean(str)
        end
    }
  === conversation ===
  Author:Document -> Fixer '#NoSpace\\n...'
  Fixer:Scan -> Linter '...'
  Linter:Findings -> Fixer ['L1: heading needs a space after #', ...]
  Fixer:Progress -> Author 2
  ...
  Fixer:Clean -> Author '# Fixed heading\\nshort line\\n'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/lint_and_fix.py
"""

from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    RawValue,
    SessionType,
    alt,
    msg,
    project_all,
    rec,
    var,
)

Author, Fixer, Linter = ap.roles('Author', 'Fixer', 'Linter')

FINDINGS = ap.Text.many(1)


Clean = ap.Text('Clean', 'No violation found.')
Scan = ap.Text('Scan', 'The current document text.')
Document = ap.Text('Document', 'The markdown to clean up.')
Findings = FINDINGS('Findings', 'One line per rule violation.')
Progress = ap.Integer('Progress', 'How many findings remain.')

protocol = (
    msg[Author, Fixer](Document)
    >> rec(
        'pass',
        msg[Fixer, Linter](Scan)
        >> alt[Linter, Fixer](
            Findings >> msg[Fixer, Author](Progress) >> var('pass'),
            Clean >> msg[Fixer, Author](Clean),
        ),
    )
).close()

LONG = (
    'this line is deliberately longer than eighty characters so the linter reports a length finding'
)
DOC_V0 = f'#NoSpace\n{LONG}\n'


def _lint(text: str) -> list[str]:
    findings: list[str] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if len(line) > 80:
            findings.append(f'L{index}: line longer than 80 characters')
        stripped = line.lstrip()
        if not stripped.startswith('#'):
            continue
        hashes = 0
        while hashes < len(stripped) and stripped[hashes] == '#':
            hashes += 1
        if hashes < len(stripped) and stripped[hashes] != ' ':
            findings.append(f'L{index}: heading needs a space after #')
    return findings


def _linter_tools() -> list[Any]:
    async def scan(document: str) -> ap.Choice:
        findings: list[RawValue] = list(_lint(document))
        if findings:
            return ap.reply(Findings, findings)
        return ap.reply(Clean, None)

    return [ap.tool_for(Scan, scan)]


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    fixer = ap.Agent(
        model,
        Fixer,
        (
            'Scan the current document text with the linter. '
            'On Findings: fix every reported issue (space after # headings; '
            'lines at most 80 characters), send Progress as the remaining '
            'finding count, then Scan again. '
            'On Clean: send Clean with the full corrected document text.'
        ),
        protocol,
        repair=ap.Repair(attempts=2),
    )
    author = ap.Human(
        Author,
        protocol,
        ap.ScriptedHumanIo([ap.says(Document, DOC_V0)]),
    )
    participants: list[ap.Participant] = [
        author,
        fixer,
        ap.Toolbox(Linter, protocol, _linter_tools()),
    ]
    return protocol, participants


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    runtime = ap.AgentRuntime(
        protocol,
        participants,
        allowance=ap.Allowance(unfoldings=3),
    )
    report.conversation(runtime.run_sync())


if __name__ == '__main__':
    main()
