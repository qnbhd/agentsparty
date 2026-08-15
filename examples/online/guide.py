# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Multi-role guide: sections are *delivered*, not shared state.

Author is a live Agent. Owner, Editor, and Librarian stay Machines for the
branching policy (when to Accept, when to stop collecting sections).

What you will see (sample run):
  === protocol ===
  Owner -> Author : Topic(str)
  rec sections {
    Author -> Editor : Draft(str)
    ...
  }
  === conversation ===
  Owner:Topic -> Author 'session types for agents'
  Author:Draft -> Editor '...'
  Editor:Accept -> Author
  ...

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/guide.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    Label,
    Routine,
    alt,
    do,
    msg,
    project,
    rec,
    var,
)

Owner, Author, Editor, Librarian = pa.roles('Owner', 'Author', 'Editor', 'Librarian')

Draft = pa.Text('Draft')
Accept = pa.Nothing('Accept')
Topic = pa.Text('Topic')
Revise = pa.Text('Revise')
Section = pa.Text('Section')
GuideMsg = pa.Text('Guide')
Go = pa.Text('Go')
Stop = pa.Text('Stop')
Next = pa.Nothing('Next')
Continue = pa.Text('Continue')
Enough = pa.Nothing('Enough')
Wrap = pa.Text('Wrap')

write = Routine(
    'Write',
    (Author, Editor),
    msg[Author, Editor](Draft)
    >> alt[Editor, Author](
        Accept,
        Revise >> msg[Author, Editor](Draft) >> msg[Editor, Author](Accept),
    ),
)

protocol = (
    msg[Owner, Author](Topic)
    >> rec(
        'sections',
        do(write, Author, Editor)
        >> msg[Editor, Librarian](Section)
        # Exit from the loop must be announced to everyone who behaves
        # differently afterward: Owner hears it directly; Author from Owner;
        >> alt[Librarian, Owner](
            Next >> msg[Owner, Author](Continue) >> msg[Author, Editor](Go) >> var('sections'),
            Enough.then(
                msg[Owner, Author](Wrap),
                msg[Author, Editor](Stop),
                msg[Librarian, Owner](GuideMsg),
            ),
        ),
    )
).close()


def _owner_decide(view: pa.View) -> pa.Choice:
    offered = {label.name for label in view.offered}
    if 'Topic' in offered:
        return pa.Choice(Label('Topic'), 'session types for agents')
    if 'Continue' in offered:
        return pa.Choice(Label('Continue'), 'continue')
    if 'Wrap' in offered:
        return pa.Choice(Label('Wrap'), 'wrap')
    return pa.Choice(view.offered[0])


def _editor_decide(view: pa.View) -> pa.Choice:
    offered = {label.name for label in view.offered}
    if 'Accept' in offered:
        return pa.Choice(Label('Accept'))
    if 'Section' in offered:
        drafts = [e.payload for e in view.seen if e.label == Label('Draft')]
        body = drafts[-1] if drafts else 'empty'
        return pa.Choice(Label('Section'), str(body))
    return pa.Choice(view.offered[0])


def _librarian_decide(threshold: int = 2):
    def decide(view: pa.View) -> pa.Choice:
        offered = {label.name for label in view.offered}
        if 'Guide' in offered:
            sections = [e.payload for e in view.seen if e.label == Label('Section')]
            return pa.Choice(Label('Guide'), '\n'.join(str(s) for s in sections))
        sections = sum(1 for e in view.seen if e.label == Label('Section'))
        if sections >= threshold:
            return pa.Choice(Label('Enough'))
        return pa.Choice(Label('Next'))

    return decide


def build_participants(threshold: int = 2) -> list:
    """Owner/Editor/Librarian machines + live Author agent."""
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    author = pa.Agent(
        model,
        Author,
        'Write short section drafts when Draft is offered. '
        'On Continue, reply Go. On Wrap, reply Stop. Keep each draft to 1-2 sentences.',
        protocol,
    )
    return [
        pa.Machine(Owner, protocol, _owner_decide),
        author,
        pa.Machine(Editor, protocol, _editor_decide),
        pa.Machine(Librarian, protocol, _librarian_decide(threshold)),
    ]


def main() -> None:
    report = debug.Report()
    for role in (Owner, Author, Editor, Librarian):
        project(protocol, role)

    report.protocol(protocol)

    participants = build_participants(threshold=2)
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
