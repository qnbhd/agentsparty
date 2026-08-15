# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Extract meeting actions; silent toolbox roles hear Skip on a redo branch.

What you will see (sample run):
  === protocol ===
  Chair -> Analyst : Transcript(str)
  rec review.
    Analyst -> Chair : Actions([{str: str}])
    Chair -> Analyst {
      Publish(): ...
      Redo(str): Analyst announces Skip to Board/Ledger/Channel ...
    }
  === conversation ===
  Chair:Transcript -> Analyst 'we agreed to ship docs and book a room'
  Analyst:Actions -> Chair [{'name': 'Ship docs', ...}, ...]
  Chair:Redo -> Analyst 'add owners to each item'
  Analyst:Skip -> Board None
  ...
  Chair:Publish -> Analyst None
  Analyst:Cards -> Board [...]
  ...
  Analyst:Published -> Chair '...'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/meeting_actions.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project,
    project_all,
    rec,
    seq,
    var,
)

Chair, Analyst, Board, Ledger, Channel = ap.roles(
    'Chair',
    'Analyst',
    'Board',
    'Ledger',
    'Channel',
)


TASK = ap.record('Task', name=str, description=str)
TASKS = TASK.many(1, 10)

CREATED = 'How many cards exist now.'
WRITTEN = 'How many rows exist now.'
POSTED = 'Where the notice landed.'

# Receivers live only on Publish — projection refuses this for Board.


Created = ap.Integer('Created', CREATED)
Cards = TASKS('Cards', 'Cards to create.')
Skip = ap.Nothing('Skip', 'Nothing to announce this round.')
Written = ap.Integer('Written', WRITTEN)
Rows = TASKS('Rows', 'Rows to append.')
Posted = ap.Text('Posted', POSTED)
Notice = ap.Text('Notice', 'One line for the team.')
Transcript = ap.Text('Transcript', 'The meeting transcript.')
Actions = TASKS('Actions', 'Action items found in the transcript.')
Published = ap.Text('Published', 'What was distributed.')
Redo = ap.Text('Redo', 'What the analyst missed.')
Publish = ap.Nothing('Publish', 'Approve the action items for distribution.')

NAIVE = seq(
    msg[Chair, Analyst](Transcript),
    rec(
        'review',
        seq(
            msg[Analyst, Chair](Actions),
            alt[Chair, Analyst](
                Publish
                >> msg[Analyst, Board](Cards)
                >> msg[Board, Analyst](Created)
                >> msg[Analyst, Ledger](Rows)
                >> msg[Ledger, Analyst](Written)
                >> msg[Analyst, Channel](Notice)
                >> msg[Channel, Analyst](Posted)
                >> msg[Analyst, Chair](Published),
                Redo >> var('review'),
            ),
        ),
    ),
).close()


protocol = seq(
    msg[Chair, Analyst](Transcript),
    rec(
        'review',
        seq(
            msg[Analyst, Chair](Actions),
            alt[Chair, Analyst](
                Publish
                >> msg[Analyst, Board](Cards)
                >> msg[Board, Analyst](Created)
                >> msg[Analyst, Ledger](Rows)
                >> msg[Ledger, Analyst](Written)
                >> msg[Analyst, Channel](Notice)
                >> msg[Channel, Analyst](Posted)
                >> msg[Analyst, Chair](Published),
                Redo
                >> msg[Analyst, Board](Skip)
                >> msg[Board, Analyst](Created)
                >> msg[Analyst, Ledger](Skip)
                >> msg[Ledger, Analyst](Written)
                >> msg[Analyst, Channel](Skip)
                >> msg[Channel, Analyst](Posted)
                >> var('review'),
            ),
        ),
    ),
).close()


def _board_tools() -> list[Any]:
    cards: list[dict[str, str]] = []

    async def create(items: list[dict[str, str]]) -> ap.Choice:
        cards.extend(items)
        return ap.reply(Created, len(cards))

    async def skip(_empty: None) -> ap.Choice:
        return ap.reply(Created, len(cards))

    return [ap.tool_for(Cards, create), ap.tool_for(Skip, skip)]


def ledger_path(workdir: Path) -> Path:
    """The only file this example writes: actions.csv under *workdir*."""
    path = (workdir / 'actions.csv').resolve()
    if not path.is_relative_to(workdir.resolve()):
        raise ValueError(f'refused write outside workspace: {path}')
    return path


def _ledger_tools(workdir: Path) -> list[Any]:
    path = ledger_path(workdir)
    rows = 0

    async def write(items: list[dict[str, str]]) -> ap.Choice:
        nonlocal rows
        with path.open('a', encoding='utf-8') as handle:
            for item in items:
                handle.write(f'{item["name"]},{item["description"]}\n')
                rows += 1
        return ap.reply(Written, rows)

    async def skip(_empty: None) -> ap.Choice:
        return ap.reply(Written, rows)

    return [ap.tool_for(Rows, write), ap.tool_for(Skip, skip)]


def _channel_tools() -> list[Any]:
    async def notice(text: str) -> ap.Choice:
        return ap.reply(Posted, f'channel:{text}')

    async def skip(_empty: None) -> ap.Choice:
        return ap.reply(Posted, 'channel:skipped')

    return [ap.tool_for(Notice, notice), ap.tool_for(Skip, skip)]


def build(workdir: Path) -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    analyst = ap.Agent(
        model,
        Analyst,
        (
            "Extract Actions as a list of 1-10 dicts with keys 'name' and "
            "'description'. On Redo: send Skip to Board, Ledger, and Channel "
            '(in that order), then extract Actions again. '
            'On Publish: send Cards (same tasks), Rows (same tasks), '
            'Notice (one line), then Published (short summary).'
        ),
        protocol,
        repair=ap.Repair(attempts=2),
    )
    chair = ap.Human(
        Chair,
        protocol,
        ap.ScriptedHumanIo(
            [
                ap.says(Transcript, 'we agreed to ship docs and book a room'),
                ap.says(Redo, 'add owners to each item'),
                ap.says(Publish, None),
            ],
        ),
    )
    participants: list[ap.Participant] = [
        chair,
        analyst,
        ap.Toolbox(Board, protocol, _board_tools()),
        ap.Toolbox(Ledger, protocol, _ledger_tools(workdir)),
        ap.Toolbox(Channel, protocol, _channel_tools()),
    ]
    return protocol, participants


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        _, participants = build(workdir)
        # Redo returns via var; Publish ends. Two review unfoldings then end.
        runtime = ap.AgentRuntime(
            protocol,
            participants,
            allowance=ap.Allowance(unfoldings=4),
        )
        report.conversation(runtime.run_sync())

    with report.refusing(ap.ProjectionError, title='why the naive shape is refused'):
        project(NAIVE, Board)


if __name__ == '__main__':
    main()
