# Bind the roles and run (/docs/tutorials/bind-and-run)

# Bind the roles and run

The protocol is closed. Now each role gets a participant. The workspace is
a `service`: it never speaks first, and it answers every request immediately.
Read handlers (`List`, `Read`, `Ready`) and write handlers (`Write`, `Done`,
`Idle`) share one directory. The planner still cannot select `Write` — that
label is not on its endpoint.

## Scope the tools

Resolve every path under the given root. A path that would escape replies
with an empty listing, a missing-file note, or a refused write. Decode
already rejected `..` on `List` and `Read`; the write handler is the
boundary for `Write.path`.

```python exec
import tempfile
from pathlib import Path

import runpy

from agentsparty.kernel.errors import PayloadError

shipped = runpy.run_path('examples/coding_agent.py')
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    shipped['seed_workspace'](root)
    listing = shipped['_list_dir'](root, '.')
    source = shipped['_read_file'](root, 'greet.py')
    refused = shipped['_write_file'](root, {'path': '../secret.py', 'content': 'no'})
    print(sorted(listing.payload))
    print(source.payload.splitlines()[0])
    print(refused.payload)
try:
    shipped['List'].payload.decode('../etc')
except PayloadError as error:
    print(type(error).__name__)
```

```text
['README.md', 'greet.py']
def greet(name):
refused: path escapes the workspace
PayloadError
```

The handlers themselves are small. `tool_for` ties each case to one
function; `service` binds the whole family to the workspace role.

```python compile
from pathlib import Path
from typing import Any

import agentsparty as ap

List = ap.Text('List')
Listing = ap.Text.many()('Listing')
Read = ap.Text('Read')
Source = ap.Text('Source')
Write = ap.record('Write', path=str, content=str)('Write')
Saved = ap.Text('Saved')
Noted = ap.Nothing('Noted')
Ready = ap.Nothing('Ready')
Done = ap.Nothing('Done')
Idle = ap.Nothing('Idle')


async def ack(_empty: None) -> ap.Choice:
    return ap.reply(Noted, None)


def workspace_tools(root: Path) -> list[Any]:
    async def list_dir(rel: str) -> ap.Choice:
        path = (root / (rel or '.')).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_dir():
            return ap.reply(Listing, [])
        names = sorted(child.relative_to(root).as_posix() for child in path.iterdir())
        return ap.reply(Listing, names)

    async def read_file(rel: str) -> ap.Choice:
        path = (root / rel).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            return ap.reply(Source, f'missing: {rel}')
        return ap.reply(Source, path.read_text(encoding='utf-8'))

    async def write(payload: dict[str, str]) -> ap.Choice:
        path = (root / payload['path']).resolve()
        if not path.is_relative_to(root.resolve()):
            return ap.reply(Saved, 'refused: path escapes the workspace')
        path.write_text(payload['content'], encoding='utf-8')
        return ap.reply(Saved, path.relative_to(root).as_posix())

    return [
        ap.tool_for(List, list_dir),
        ap.tool_for(Read, read_file),
        ap.tool_for(Ready, ack),
        ap.tool_for(Write, write),
        ap.tool_for(Done, ack),
        ap.tool_for(Idle, ack),
    ]
```

## Cast the phased roles

`Cast` demands every role is played. The client is an interactive CLI human.
The three authors share `gpt-5.6-luna` via `OPENAI_API_KEY`. The workspace is
the current directory, so accepted writes remain in the workspace. Models are
constructed in `build_cast` / `main`, never at import — the same rule as the
rest of the online catalogue.

```python compile
import os
from pathlib import Path

from openai import AsyncOpenAI

import agentsparty as ap
import runpy

shipped = runpy.run_path('examples/coding_agent.py')
protocol = shipped['protocol']
model = ap.OpenAIModel(
    'gpt-5.6-luna',
    AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'], max_retries=0),
)
root = Path.cwd()
trace = (
    pa
    .Cast(protocol)
    .play(
        shipped['Client'],
        ap.human(ap.CliHumanIo()),
    )
    .play(
        shipped['Planner'],
        ap.agent(model, shipped['PLANNER_BRIEF'], repair=ap.Repair(attempts=2)),
    )
    .play(
        shipped['Coder'],
        ap.agent(model, shipped['CODER_BRIEF'], repair=ap.Repair(attempts=2)),
    )
    .play(
        shipped['Reviewer'],
        ap.agent(model, shipped['REVIEWER_BRIEF'], repair=ap.Repair(attempts=2)),
    )
    .play(
        shipped['Workspace'],
        ap.service(*shipped['workspace_tools'](root)),
    )
    .run_sync(allowance=ap.Allowance(unfoldings=12))
)
print([envelope.label.name for envelope in trace])
```

`project_all` already succeeded when the protocol was closed. A live run
walks `Task` → explore (`List` / `Read` / `Ready`) → `Plan` → implement
(`Write` / `Done`) → one of `Ship` or `Fix` → `Delivered`.

When `Client` prompts, enter `1` (the `Task` branch), then enter the task
text. The workspace is the directory from which the command is run. For
example, from the repository root, enter:

```text
Write a fast matrix multiplication function into matrixmult.py.
```

The task is read by the running program. Do not type it as a new shell
command after the program exits; zsh treats parentheses and square brackets
in natural-language text as shell syntax.

Run the harness:

```bash
export OPENAI_API_KEY=...
uv run python examples/coding_agent.py
```

`debug.Report` prints the protocol, then the conversation. The example is
the source of truth; this tutorial is the same session, assembled by hand.
See [Cast](/docs/concepts/protocol-first),
[tools as roles](/docs/concepts/participants-and-roles), and
[[agentsparty.runtime.Cast]].
