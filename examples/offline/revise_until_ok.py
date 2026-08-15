# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Budget exhausted and work will not converge are different things.

Allowance bounds unfoldings. Non-convergence is a journalled Give up branch.
Length is a refine on the codec, not a tool the model may skip.

What you will see (exact):
  === protocol ===
  Editor -> Bard : Topic(str)
  rec draft { ... }
  === duties ===
  ...
  === session ===
  Editor:Topic -> Bard 'ambition and rest'
  Bard:Measure -> Meter 'To be, or not to be: ...'
  ...
  === skeleton ===
  Editor:Topic  Bard:Measure  Meter:Length  ...
  === accept on second ===
  ...
  === recursion limit ===
  ...
  RecursionLimitError after two unfoldings

Offline: deterministic double, no API key.

Run::

    uv run python examples/offline/revise_until_ok.py
"""

from __future__ import annotations

import json
from typing import Any

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    Label,
    SessionType,
    alt,
    msg,
    project_all,
    rec,
    var,
)

Editor, Bard, Critic, Meter = pa.roles('Editor', 'Bard', 'Critic', 'Meter')

POST = pa.Text.where('at most 280 characters', lambda s: len(s) <= 280)
CLOSED = 'Meter acknowledgement.'
PROGRESS = 'Progress note.'


# Editor is told on every branch (Final / Abandoned / Retrying) — recipe §4.2.


Length = pa.Integer('Length', 'Character count of the draft.')
Closed = pa.Text('Closed', CLOSED)
Measure = pa.Text('Measure', 'The draft to measure.')
Done = pa.Nothing('Done', 'No further draft is coming.')
Again = pa.Nothing('Again', 'Another draft is coming.')
Topic = pa.Text('Topic', 'What the post is about.')
Post = POST('Post', 'A Shakespearean post within the limit.')
Final = POST('Final', 'The accepted post.')
Abandoned = pa.Text('Abandoned', 'Why nothing was produced.')
Retrying = pa.Text('Retrying', PROGRESS)
Ok = pa.Nothing('Ok', 'Accept the post.')
GiveUp = pa.Text('Give up', 'Why this post will not converge.')
Revise = pa.Text('Revise', 'One critique, at most twenty-five words.')

protocol = (
    msg[Editor, Bard](Topic)
    >> rec(
        'draft',
        msg[Bard, Meter](Measure)
        >> msg[Meter, Bard](Length)
        >> msg[Bard, Critic](Post)
        >> alt[Critic, Bard](
            Ok >> msg[Bard, Meter](Done) >> msg[Meter, Bard](Closed) >> msg[Bard, Editor](Final),
            Revise
            >> msg[Bard, Meter](Again)
            >> msg[Meter, Bard](Closed)
            >> msg[Bard, Editor](Retrying)
            >> var('draft'),
            GiveUp
            >> msg[Bard, Meter](Done)
            >> msg[Meter, Bard](Closed)
            >> msg[Bard, Editor](Abandoned),
        ),
    )
).close()

DRAFT_1 = 'To be, or not to be: that is the question.'
DRAFT_2 = 'Brevity is the soul of wit, good sir.'
DRAFT_3 = "All the world's a stage, and we mere players."


def _answer(label: str, payload: object = None) -> str:
    return json.dumps({'alt': {'label': label, 'payload': payload}})


def _meter_tools() -> list[Any]:
    async def measure(draft: str) -> pa.Choice:
        return pa.reply(Length, len(draft))

    async def done(_empty: None) -> pa.Choice:
        return pa.reply(Closed, CLOSED)

    async def again(_empty: None) -> pa.Choice:
        return pa.reply(Closed, CLOSED)

    return [
        pa.tool_for(Measure, measure),
        pa.tool_for(Done, done),
        pa.tool_for(Again, again),
    ]


def _critic_decide(max_attempts: int, *, always_revise: bool = False):
    def decide(view: pa.View) -> pa.Choice:
        attempts = sum(1 for e in view.seen if e.label == Label('Post'))
        if always_revise:
            return pa.says(Revise, 'tighten the meter')
        if max_attempts == 2 and attempts >= 2:
            return pa.says(Ok, None)
        if attempts >= max_attempts:
            return pa.says(GiveUp, 'three drafts still miss the mark')
        return pa.says(Revise, 'tighten the meter')

    return decide


def _attempt(draft: str) -> list[str]:
    return [
        _answer('Measure', draft),
        _answer('Post', draft),
        _answer('Again', None),
        _answer('Retrying', 'drafting again'),
    ]


# deterministic double: scripted model answers
def _bard_script(path: str) -> list[str]:
    # Measure+Post then Again/Retrying, or Done+Final/Abandoned on exit.
    if path == 'give-up':
        return [
            *_attempt(DRAFT_1),
            *_attempt(DRAFT_2),
            _answer('Measure', DRAFT_3),
            _answer('Post', DRAFT_3),
            _answer('Done', None),
            _answer('Abandoned', 'could not converge on a post'),
        ]
    if path == 'ok':
        return [
            *_attempt(DRAFT_1),
            _answer('Measure', DRAFT_2),
            _answer('Post', DRAFT_2),
            _answer('Done', None),
            _answer('Final', DRAFT_2),
        ]
    return [*_attempt(DRAFT_1), *_attempt(DRAFT_2), *_attempt(DRAFT_3)]


def build(
    *,
    path: str = 'give-up',
    max_attempts: int = 3,
    always_revise: bool = False,
) -> tuple[SessionType, list[pa.Participant]]:
    # give-up: Critic yields on third Post; ok: accepts on second; limit: always Revise.
    bard = pa.Agent(
        pa.ScriptedLanguageModel(_bard_script(path)),
        Bard,
        'Draft a short Shakespearean post within the limit.',
        protocol,
    )
    critic = pa.Machine(
        Critic,
        protocol,
        _critic_decide(max_attempts, always_revise=always_revise),
    )
    editor = pa.Human(
        Editor,
        protocol,
        pa.ScriptedHumanIo([pa.says(Topic, 'ambition and rest')]),
    )
    return protocol, [editor, bard, critic, pa.Toolbox(Meter, protocol, _meter_tools())]


def _run(
    path: str,
    *,
    max_attempts: int = 3,
    always_revise: bool = False,
    unfoldings: int | None = None,
) -> list[Any]:
    _, participants = build(
        path=path,
        max_attempts=max_attempts,
        always_revise=always_revise,
    )
    allowance = pa.Allowance(unfoldings=unfoldings) if unfoldings is not None else pa.Allowance()
    runtime = pa.AgentRuntime(protocol, participants, allowance=allowance)
    try:
        return runtime.run_sync()
    except pa.RecursionLimitError:
        return list(runtime.trace)


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)
    report.duties(protocol)

    trace = _run('give-up', max_attempts=3)
    report.conversation(trace, title='session')
    report.skeleton(trace)

    ok_trace = _run('ok', max_attempts=2)
    report.skeleton(ok_trace, title='accept on second')

    limited = _run('limit', always_revise=True, unfoldings=2)
    report.skeleton(limited, title='recursion limit')
    report.note('RecursionLimitError after two unfoldings', title='limit result')


if __name__ == '__main__':
    main()
