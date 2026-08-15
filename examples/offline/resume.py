"""Fall mid-session and resume from a journal without re-asking.

First run records decisions; a second run with an empty scripted agent
replays them. Only decisions are durable — not opaque agent state.

What you will see (exact):
  === protocol ===
  Author -> Editor : Draft(str)
  Author -> Editor : Revision(str)
  end
  === conversation ===
  first run: ['v1', 'v2']
  resume: ['v1', 'v2']

Offline: deterministic double, no API key.

Run::

    uv run python examples/offline/resume.py
"""

from __future__ import annotations

import json
from pathlib import Path

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import msg


def main() -> None:
    report = debug.Report()
    A, B = ap.roles('Author', 'Editor')
    Draft = ap.Text('Draft')
    Revision = ap.Text('Revision')
    protocol = (msg[A, B](Draft) >> msg[A, B](Revision)).close()
    report.protocol(protocol)
    path = Path('examples_resume.jsonl')
    path.unlink(missing_ok=True)

    # deterministic double: scripted model answers
    answers = [
        json.dumps({'alt': {'label': 'Draft', 'payload': 'v1'}}),
        json.dumps({'alt': {'label': 'Revision', 'payload': 'v2'}}),
    ]
    model = ap.ScriptedLanguageModel(answers)
    journal = ap.JsonlJournal(path, protocol)
    author = ap.Agent(model, A, 'write short drafts', protocol)
    editor = ap.Human(B, protocol, ap.ScriptedHumanIo([]))
    first = ap.AgentRuntime(protocol, [author, editor], journal=journal).run_sync()

    # Resume: no remaining model answers; journal supplies decisions.
    empty = ap.ScriptedLanguageModel([])
    author2 = ap.Agent(empty, A, 'write short drafts', protocol)
    editor2 = ap.Human(B, protocol, ap.ScriptedHumanIo([]))
    resumed = ap.JsonlJournal(path, protocol)
    second = ap.AgentRuntime(protocol, [author2, editor2], journal=resumed).run_sync()
    report.note(
        f'first run: {[e.payload for e in first]}',
        f'resume: {[e.payload for e in second]}',
        title='conversation',
    )
    path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
