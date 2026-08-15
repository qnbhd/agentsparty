# Declare the conversation (/docs/tutorials/declare-the-conversation)

# Declare the conversation

A session type is a value. Name the roles, name the payloads, then sequence
the phases. This page builds the same protocol as `examples/coding_agent.py`
and checks the two local types that make the harness honest.

## Roles and payloads

Five roles: the client commissions, the planner reads, the workspace
answers tools, the coder writes, the reviewer ships or fixes once.
`RelPath` refuses `..` and absolute paths at the codec — the planner cannot
ask to list outside the given directory.

```python exec
from pathlib import Path

import agentsparty as pa
from agentsparty.protocol import alt, msg, rec, var

Client, Planner, Workspace, Coder, Reviewer = pa.roles(
    'Client',
    'Planner',
    'Workspace',
    'Coder',
    'Reviewer',
)

RelPath = pa.Text.where(
    'a relative path that stays in the workspace',
    lambda p: not Path(p).is_absolute() and '..' not in Path(p).parts,
)

Task = pa.Text('Task', 'The coding task in one sentence.')
List = RelPath('List', 'Relative directory to list.')
Listing = pa.Text.many()('Listing', 'Relative paths under that directory.')
Read = RelPath('Read', 'Relative file path to read.')
Source = pa.Text('Source', 'File contents, or a missing-file note.')
Ready = pa.Nothing('Ready', 'Planning is finished.')
Noted = pa.Nothing('Noted', 'Workspace acknowledgement.')
Looking = pa.Nothing('Looking', 'Planner is still reading.')
Outline = pa.Text('Outline', 'The plan, visible to everyone who waits.')
Plan = pa.Text('Plan', 'What the coder should implement.')
Write = pa.record('Write', path=str, content=str)(
    'Write',
    'Relative path and the full file contents.',
)
Saved = pa.Text('Saved', 'Where the write landed.')
Done = pa.Nothing('Done', 'Implementation is ready for review.')
Working = pa.Nothing('Working', 'Coder is still writing.')
Patch = pa.Text('Patch', 'What changed, for review.')
Ship = pa.Nothing('Ship', 'Accept the work as it stands.')
Fix = pa.Text('Fix', 'One concrete change, at most twenty words.')
Idle = pa.Nothing('Idle', 'No further write.')
Delivered = pa.Text('Delivered', 'The accepted result.')
print(Client.name, Write.label.name, List.payload.name)
```

## One-shot review, then implement, then explore

Review is the starter shape: `Ship` or one `Fix`, then `Delivered`. The
workspace hears `Idle` or `Write` so it can tell the branches apart.
Implement is a `rec` of `Write` / `Done`. Explore is a `rec` of `List` /
`Read` / `Ready` — `Ready` is the only exit, and it hands the plan to the
coder.

Client, coder, and reviewer are silent during explore, so they receive
`Looking` on the loop and `Plan` / `Outline` on the exit. That is the
[knowledge of alt](/docs/concepts/knowledge-of-alt) tax: without those
messages [projection](/docs/concepts/projection) refuses the protocol.

```python exec
from pathlib import Path

import agentsparty as pa
from agentsparty.protocol import alt, equal_session, msg, rec, var

Client, Planner, Workspace, Coder, Reviewer = pa.roles(
    'Client',
    'Planner',
    'Workspace',
    'Coder',
    'Reviewer',
)
RelPath = pa.Text.where(
    'a relative path that stays in the workspace',
    lambda p: not Path(p).is_absolute() and '..' not in Path(p).parts,
)
Task = pa.Text('Task', 'The coding task in one sentence.')
List = RelPath('List', 'Relative directory to list.')
Listing = pa.Text.many()('Listing', 'Relative paths under that directory.')
Read = RelPath('Read', 'Relative file path to read.')
Source = pa.Text('Source', 'File contents, or a missing-file note.')
Ready = pa.Nothing('Ready', 'Planning is finished.')
Noted = pa.Nothing('Noted', 'Workspace acknowledgement.')
Looking = pa.Nothing('Looking', 'Planner is still reading.')
Outline = pa.Text('Outline', 'The plan, visible to everyone who waits.')
Plan = pa.Text('Plan', 'What the coder should implement.')
Write = pa.record('Write', path=str, content=str)(
    'Write',
    'Relative path and the full file contents.',
)
Saved = pa.Text('Saved', 'Where the write landed.')
Done = pa.Nothing('Done', 'Implementation is ready for review.')
Working = pa.Nothing('Working', 'Coder is still writing.')
Patch = pa.Text('Patch', 'What changed, for review.')
Ship = pa.Nothing('Ship', 'Accept the work as it stands.')
Fix = pa.Text('Fix', 'One concrete change, at most twenty words.')
Idle = pa.Nothing('Idle', 'No further write.')
Delivered = pa.Text('Delivered', 'The accepted result.')

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
        Write
        >> msg[Workspace, Coder](Saved)
        >> msg[Coder, Client](Working)
        >> msg[Coder, Reviewer](Working)
        >> var('implement'),
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
            List
            >> msg[Workspace, Planner](Listing)
            >> msg[Planner, Client](Looking)
            >> msg[Planner, Coder](Looking)
            >> msg[Planner, Reviewer](Looking)
            >> var('explore'),
            Read
            >> msg[Workspace, Planner](Source)
            >> msg[Planner, Client](Looking)
            >> msg[Planner, Coder](Looking)
            >> msg[Planner, Reviewer](Looking)
            >> var('explore'),
            Ready
            >> msg[Workspace, Planner](Noted)
            >> msg[Planner, Coder](Plan)
            >> msg[Planner, Client](Outline)
            >> msg[Planner, Reviewer](Outline)
            >> implement,
        ),
    )
).close()
print(protocol.__class__.__name__)
```

## The local types

`project` derives each role's endpoint. The planner's selects toward the
workspace are exactly `List`, `Read`, and `Ready`. The reviewer's only
select is `Ship` / `Fix`, and both continuations are `end`.

```python exec
from agentsparty.protocol import project
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointVar,
)

def selects(node):
    match node:
        case EndpointEnd() | EndpointVar():
            return
        case EndpointRec(body=body):
            yield from selects(body)
        case EndpointBranch(branches=branches):
            for branch in branches.values():
                yield from selects(branch.continuation)
        case EndpointSelect(receiver=receiver, branches=branches):
            yield receiver, branches
            for branch in branches.values():
                yield from selects(branch.continuation)

offered = set()
for receiver, branches in selects(project(protocol, Planner)):
    if receiver == Workspace:
        offered.update(branches)
print(sorted(label.name for label in offered))

receiver, branches = next(selects(project(protocol, Reviewer)))
print(receiver.name, sorted(label.name for label in branches))
print(all(isinstance(b.continuation, EndpointEnd) for b in branches.values()))
```

```text
['List', 'Read', 'Ready']
Coder ['Fix', 'Ship']
True
```

The construction is the shipped example. `equal_session` is the drift
check — this page and `examples/coding_agent.py` are one protocol.

```python exec
import runpy

from agentsparty.protocol import equal_session

shipped = runpy.run_path('examples/coding_agent.py')
print(equal_session(protocol, shipped['protocol']))
```

Next: [bind the roles and run](/docs/tutorials/bind-and-run).

