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
  Owner:Topic -> Author 'session protocols for agents'
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

import agentsparty as ap
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

Owner, Author, Editor, Librarian = ap.roles('Owner', 'Author', 'Editor', 'Librarian')

Draft = ap.Text('Draft')
Accept = ap.Nothing('Accept')
Topic = ap.Text('Topic')
Revise = ap.Text('Revise')
Section = ap.Text('Section')
GuideMsg = ap.Text('Guide')
Go = ap.Text('Go')
Stop = ap.Text('Stop')
Next = ap.Nothing('Next')
Continue = ap.Text('Continue')
Enough = ap.Nothing('Enough')
Wrap = ap.Text('Wrap')

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


def _owner_decide(view: ap.View) -> ap.Choice:
    offered = {label.name for label in view.offered}
    if 'Topic' in offered:
        return ap.Choice(Label('Topic'), 'session protocols for agents')
    if 'Continue' in offered:
        return ap.Choice(Label('Continue'), 'continue')
    if 'Wrap' in offered:
        return ap.Choice(Label('Wrap'), 'wrap')
    return ap.Choice(view.offered[0])


def _editor_decide(view: ap.View) -> ap.Choice:
    offered = {label.name for label in view.offered}
    if 'Accept' in offered:
        return ap.Choice(Label('Accept'))
    if 'Section' in offered:
        drafts = [e.payload for e in view.seen if e.label == Label('Draft')]
        body = drafts[-1] if drafts else 'empty'
        return ap.Choice(Label('Section'), str(body))
    return ap.Choice(view.offered[0])


def _librarian_decide(threshold: int = 2):
    def decide(view: ap.View) -> ap.Choice:
        offered = {label.name for label in view.offered}
        if 'Guide' in offered:
            sections = [e.payload for e in view.seen if e.label == Label('Section')]
            return ap.Choice(Label('Guide'), '\n'.join(str(s) for s in sections))
        sections = sum(1 for e in view.seen if e.label == Label('Section'))
        if sections >= threshold:
            return ap.Choice(Label('Enough'))
        return ap.Choice(Label('Next'))

    return decide


def build_participants(threshold: int = 2) -> list:
    """Owner/Editor/Librarian machines + live Author agent."""
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    author = ap.Agent(
        model,
        Author,
        'Write short section drafts when Draft is offered. '
        'On Continue, reply Go. On Wrap, reply Stop. Keep each draft to 1-2 sentences.',
        protocol,
    )
    return [
        ap.Machine(Owner, protocol, _owner_decide),
        author,
        ap.Machine(Editor, protocol, _editor_decide),
        ap.Machine(Librarian, protocol, _librarian_decide(threshold)),
    ]


def main() -> None:
    report = debug.Report()
    for role in (Owner, Author, Editor, Librarian):
        project(protocol, role)

    report.protocol(protocol)

    participants = build_participants(threshold=2)
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
