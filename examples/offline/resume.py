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

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import msg


def main() -> None:
    report = debug.Report()
    A, B = pa.roles('Author', 'Editor')
    Draft = pa.Text('Draft')
    Revision = pa.Text('Revision')
    protocol = (msg[A, B](Draft) >> msg[A, B](Revision)).close()
    report.protocol(protocol)
    path = Path('examples_resume.jsonl')
    path.unlink(missing_ok=True)

    # deterministic double: scripted model answers
    answers = [
        json.dumps({'alt': {'label': 'Draft', 'payload': 'v1'}}),
        json.dumps({'alt': {'label': 'Revision', 'payload': 'v2'}}),
    ]
    model = pa.ScriptedLanguageModel(answers)
    journal = pa.JsonlJournal(path, protocol)
    author = pa.Agent(model, A, 'write short drafts', protocol)
    editor = pa.Human(B, protocol, pa.ScriptedHumanIo([]))
    first = pa.AgentRuntime(protocol, [author, editor], journal=journal).run_sync()

    # Resume: no remaining model answers; journal supplies decisions.
    empty = pa.ScriptedLanguageModel([])
    author2 = pa.Agent(empty, A, 'write short drafts', protocol)
    editor2 = pa.Human(B, protocol, pa.ScriptedHumanIo([]))
    resumed = pa.JsonlJournal(path, protocol)
    second = pa.AgentRuntime(protocol, [author2, editor2], journal=resumed).run_sync()
    report.note(
        f'first run: {[e.payload for e in first]}',
        f'resume: {[e.payload for e in second]}',
        title='conversation',
    )
    path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
