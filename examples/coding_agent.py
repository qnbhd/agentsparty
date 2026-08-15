# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""A coding-agent harness: plan (read-only), implement, one review, then ship.

The protocol is the control. During planning the local type offers List and
Read against a given directory — Write is unrepresentable. The implementer
then writes. The reviewer takes one step: Ship, or one Fix, then a result.

Interactive run (conversation sketch)::

    Client selects Task -> Planner
    > label: 1
    > Task (str): Write a fast matrix multiplication function into matrixmult.py.
    Planner:List -> Workspace '.'
    Workspace:Listing -> Planner ['README.md', 'greet.py']
    Planner:Looking -> Client
    Planner:Looking -> Coder
    Planner:Looking -> Reviewer
    Planner:Read -> Workspace 'greet.py'
    Workspace:Source -> Planner 'def greet(name):\\n    return name\\n'
    Planner:Ready -> Workspace
    Planner:Plan -> Coder '…'
    Coder:Write -> Workspace {'path': 'greet.py', 'content': '…'}
    Coder:Done -> Workspace
    Coder:Patch -> Reviewer '…'
    Reviewer:Ship -> Coder
    Coder:Delivered -> Client '…'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/coding_agent.py
    # at the Client prompt: enter 1, then the task text
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import alt, msg, project_all, rec, var

Client, Planner, Workspace, Coder, Reviewer = ap.roles(
    'Client',
    'Planner',
    'Workspace',
    'Coder',
    'Reviewer',
)

MODEL = 'gpt-5.6-luna'
SEED = {
    'README.md': 'A tiny greeting helper.\n',
    'greet.py': 'def greet(name):\n    return name\n',
}

RelPath = ap.Text.where(
    'a relative path that stays in the workspace',
    lambda p: not Path(p).is_absolute() and '..' not in Path(p).parts,
)

Task = ap.Text('Task', 'The coding task in one sentence.')
List = RelPath('List', 'Relative directory to list.')
Listing = ap.Text.many()('Listing', 'Relative paths under that directory.')
Read = RelPath('Read', 'Relative file path to read.')
Source = ap.Text('Source', 'File contents, or a missing-file note.')
Ready = ap.Nothing('Ready', 'Planning is finished.')
Noted = ap.Nothing('Noted', 'Workspace acknowledgement.')
Looking = ap.Nothing('Looking', 'Planner is still reading.')
Outline = ap.Text('Outline', 'The plan, visible to everyone who waits.')
Plan = ap.Text('Plan', 'What the coder should implement.')
Write = ap.record('Write', path=str, content=str)(
    'Write',
    'Relative path and the full file contents.',
)
Saved = ap.Text('Saved', 'Where the write landed.')
Done = ap.Nothing('Done', 'Implementation is ready for review.')
Working = ap.Nothing('Working', 'Coder is still writing.')
Patch = ap.Text('Patch', 'What changed, for review.')
Ship = ap.Nothing('Ship', 'Accept the work as it stands.')
Fix = ap.Text('Fix', 'One concrete change, at most twenty words.')
Idle = ap.Nothing('Idle', 'No further write.')
Delivered = ap.Text('Delivered', 'The accepted result.')


def _still_reading():
    # Silent roles hear Looking so the explore alt is mergeable.
    return (
        msg[Planner, Client](Looking)
        >> msg[Planner, Coder](Looking)
        >> msg[Planner, Reviewer](Looking)
        >> var('explore')
    )


def _handoff():
    return (
        msg[Planner, Coder](Plan)
        >> msg[Planner, Client](Outline)
        >> msg[Planner, Reviewer](Outline)
    )


def _still_writing():
    return msg[Coder, Client](Working) >> msg[Coder, Reviewer](Working) >> var('implement')


review = alt[Reviewer, Coder](
    Ship
    >> msg[Coder, Workspace](Idle)
    >> msg[Workspace, Coder](Noted)
    >> msg[Coder, Client](Delivered),
    Fix
    >> msg[Coder, Workspace](Write)
    >> msg[Workspace, Coder](Saved)
    >> msg[Coder, Client](Delivered),
)

implement = rec(
    'implement',
    alt[Coder, Workspace](
        Write >> msg[Workspace, Coder](Saved) >> _still_writing(),
        Done
        >> msg[Workspace, Coder](Noted)
        >> msg[Coder, Reviewer](Patch)
        >> msg[Coder, Client](Patch)
        >> review,
    ),
)

protocol = (
    msg[Client, Planner](Task)
    >> rec(
        'explore',
        alt[Planner, Workspace](
            List >> msg[Workspace, Planner](Listing) >> _still_reading(),
            Read >> msg[Workspace, Planner](Source) >> _still_reading(),
            Ready >> msg[Workspace, Planner](Noted) >> _handoff() >> implement,
        ),
    )
).close()


def _inside(root: Path, rel: str) -> Path | None:
    """Resolve *rel* under *root*, or None when it would escape."""
    candidate = (root / (rel or '.')).resolve()
    if not candidate.is_relative_to(root.resolve()):
        return None
    return candidate


async def _ack(_empty: None) -> ap.Choice:
    return ap.reply(Noted, None)


def _list_dir(root: Path, rel: str) -> ap.Choice:
    path = _inside(root, rel)
    if path is None or not path.is_dir():
        return ap.reply(Listing, [])
    names = sorted(child.relative_to(root).as_posix() for child in path.iterdir())
    return ap.reply(Listing, names)


def _read_file(root: Path, rel: str) -> ap.Choice:
    path = _inside(root, rel)
    if path is None or not path.is_file():
        return ap.reply(Source, f'missing: {rel}')
    return ap.reply(Source, path.read_text(encoding='utf-8'))


def _write_file(root: Path, payload: dict[str, str]) -> ap.Choice:
    path = _inside(root, payload['path'])
    if path is None:
        return ap.reply(Saved, 'refused: path escapes the workspace')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload['content'], encoding='utf-8')
    return ap.reply(Saved, path.relative_to(root).as_posix())


def workspace_tools(root: Path) -> list[Any]:
    """Read tools plus write tools for one workspace directory."""

    async def list_dir(rel: str) -> ap.Choice:
        return _list_dir(root, rel)

    async def read_file(rel: str) -> ap.Choice:
        return _read_file(root, rel)

    async def write(payload: dict[str, str]) -> ap.Choice:
        return _write_file(root, payload)

    return [
        ap.tool_for(List, list_dir),
        ap.tool_for(Read, read_file),
        ap.tool_for(Ready, _ack),
        ap.tool_for(Write, write),
        ap.tool_for(Done, _ack),
        ap.tool_for(Idle, _ack),
    ]


def seed_workspace(root: Path) -> None:
    """Write the tiny sample tree used by deterministic tests and docs."""
    for name, body in SEED.items():
        (root / name).write_text(body, encoding='utf-8')


PLANNER_BRIEF = (
    'Explore with List and Read only. List the workspace, read the files '
    'you need, then Ready and send Plan: what to change and in which file. '
    'Do not invent files you have not read.'
)
CODER_BRIEF = (
    'Carry out Plan. Write the full file contents. When the change is in '
    'place, Done and send Patch describing what changed. After Ship, send '
    'Idle then Delivered. After Fix, Write once more, then Delivered.'
)
REVIEWER_BRIEF = (
    'Review Patch against Task and Plan. Prefer Ship when the change '
    'matches the task. If something concrete is missing, send Fix in at '
    'most twenty words — you review once.'
)


def _model() -> ap.OpenAIModel:
    client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'], max_retries=0, timeout=30.0)
    return ap.OpenAIModel(MODEL, client)


def build_cast(
    root: Path,
    client_io: Any | None = None,
    model: Any | None = None,
) -> ap.Cast:
    """Bind every role for an interactive run against *root*."""
    model = _model() if model is None else model
    client_io = ap.CliHumanIo() if client_io is None else client_io
    return (
        ap
        .Cast(protocol)
        .play(Client, ap.human(client_io))
        .play(Planner, ap.agent(model, PLANNER_BRIEF, repair=ap.Repair(attempts=2)))
        .play(Coder, ap.agent(model, CODER_BRIEF, repair=ap.Repair(attempts=2)))
        .play(Reviewer, ap.agent(model, REVIEWER_BRIEF, repair=ap.Repair(attempts=2)))
        .play(Workspace, ap.service(*workspace_tools(root)))
    )


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    root = Path.cwd()
    print(f'workspace: {root}')
    print('Enter the task when Client prompts; the protocol drives the rest.')
    trace = build_cast(root).run_sync(allowance=ap.Allowance(unfoldings=12))
    report.conversation(trace)


if __name__ == '__main__':
    main()
