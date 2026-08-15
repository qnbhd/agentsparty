# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Outline two chapters and write each under a shared chapter routine.

Sample run (conversation sketch, 3-6 lines)::

    Publisher:Topic -> Planner 'session protocols for agents'
    Planner:Outline -> Author [{title, description}, … x2]
    Author:Draft -> Editor '…'
    Editor:Keep -> Author
    Editor:Chapter -> Archivist '…'
    Archivist:Manuscript -> Publisher '…'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/write_a_book.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    Label,
    Routine,
    SessionType,
    alt,
    do,
    msg,
    project_all,
)

Publisher, Planner, Author, Editor, Archivist = ap.roles(
    'Publisher',
    'Planner',
    'Author',
    'Editor',
    'Archivist',
)
Writer_, Critic_ = ap.roles('Writer', 'Critic')
Extra_ = ap.roles('Extra')[0]


OUTLINE_ITEM = ap.record('OutlineItem', title=str, description=str)
OUTLINE = OUTLINE_ITEM.many(2, 2)


Draft = ap.Text('Draft', 'The chapter as drafted.')
Keep = ap.Nothing('Keep', 'Accept the chapter.')
Manuscript = ap.Text('Manuscript', 'Both chapters, in order.')
Chapter = ap.Text('Chapter', 'A finished chapter.')
Sharpen = ap.Text('Sharpen', 'One change, at most twenty words.')
Topic = ap.Text('Topic', 'What the book is about.')
Outline = OUTLINE('Outline', 'Two chapters, title and description.')

CHAPTER = Routine(
    'Chapter',
    (Writer_, Critic_),
    msg[Writer_, Critic_](Draft)
    >> alt[Critic_, Writer_](
        Keep,
        Sharpen >> msg[Writer_, Critic_](Draft) >> msg[Critic_, Writer_](Keep),
    ),
)


protocol = (
    msg[Publisher, Planner](Topic)
    >> msg[Planner, Author](Outline)
    >> do(CHAPTER, Author, Editor)
    >> msg[Editor, Archivist](Chapter)
    >> do(CHAPTER, Author, Editor)
    >> msg[Editor, Archivist](Chapter)
    >> msg[Archivist, Publisher](Manuscript)
).close()


def _archivist_decide(view: ap.View) -> ap.Choice:
    chapters = [e.payload for e in view.seen if e.label == Label('Chapter')]
    body = '\n\n'.join(str(c) for c in chapters)
    return ap.says(Manuscript, body)


def _editor_decide(view: ap.View) -> ap.Choice:
    offered = {label.name for label in view.offered}
    if 'Keep' in offered:
        return ap.says(Keep, None)
    if 'Chapter' in offered:
        drafts = [e.payload for e in view.seen if e.label == Label('Draft')]
        return ap.says(Chapter, str(drafts[-1]) if drafts else '')
    return ap.Choice(view.offered[0])


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
        'Produce Outline as a JSON list of exactly two objects. Each object '
        'has string keys title and description (both required).',
        protocol,
        repair=ap.Repair(attempts=2),
    )
    author = ap.Agent(
        model,
        Author,
        'Write each chapter Draft as plain markdown prose following the '
        'Outline. If Sharpen arrives, send a revised Draft addressing the '
        'change. Two chapters are written in protocol order.',
        protocol,
    )
    publisher = ap.Human(
        Publisher,
        protocol,
        ap.ScriptedHumanIo([ap.says(Topic, 'session protocols for agents')]),
    )
    return protocol, [
        publisher,
        planner,
        author,
        ap.Machine(Editor, protocol, _editor_decide),
        ap.Machine(Archivist, protocol, _archivist_decide),
    ]


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)
    _, participants = build()
    report.conversation(ap.AgentRuntime(protocol, participants).run_sync())
    with report.refusing(ValueError, title='duplicate param'):
        Routine('Dup', (Writer_, Writer_), msg[Writer_, Critic_](Draft))
    with report.refusing(ValueError, title='role not in params'):
        Routine('Hidden', (Writer_,), msg[Writer_, Critic_](Draft))
    with report.refusing(ValueError, title='unused param'):
        Routine('Spare', (Writer_, Critic_, Extra_), msg[Writer_, Critic_](Draft))
    with report.refusing(ValueError, title='non-injective do'):
        do(CHAPTER, Author, Author)


if __name__ == '__main__':
    main()
