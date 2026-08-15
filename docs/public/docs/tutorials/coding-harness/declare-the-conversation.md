# Declare the conversation (/docs/tutorials/coding-harness/declare-the-conversation)

Continue in `coding_agent.py`. This page declares the complete session before
attaching models, terminal I/O, or filesystem functions. Keeping the protocol
independent from its participants lets `agentsparty` project and check every role
before the first model call.

<Steps>

<Step>
### Declare the roles

Create one role for each authority in the harness:

```python compile
Client, Planner, Workspace, Coder, Reviewer = ap.roles(
    'Client',
    'Planner',
    'Workspace',
    'Coder',
    'Reviewer',
)

MODEL = 'gpt-5.6-luna'
```

`Workspace` is a participant in the session. Filesystem access therefore
appears in the protocol trace and stays scoped to the messages offered at each
phase.
</Step>

<Step>
### Define the message vocabulary

Every message label carries a codec. Primitive codecs cover text and empty
signals; `many()` describes a sequence; `record()` gives `Write` a structured
payload.

`RelPath` parses every path that `List` and `Read` carry. The refinement rejects
absolute paths and parent-directory traversal as soon as the payload is decoded.

```python compile
RelPath = ap.Text.where(
    'a relative path that stays in the workspace',
    lambda path: not Path(path).is_absolute() and '..' not in Path(path).parts,
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
```

The path refinement protects read requests at the message boundary. The write
payload contains a raw string because its record describes two fields together;
the workspace will resolve that path under its root before touching the
filesystem.
</Step>

<Step>
### Announce progress to waiting roles

An alternative must remain observable to every role whose future depends on
its branch. While the planner explores, the client, coder, and reviewer receive
`Looking`. While the coder writes, the client and reviewer receive `Working`.
These signals give each local endpoint enough information to follow a loop or
leave it.

```python compile
def _still_reading():
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
    return (
        msg[Coder, Client](Working)
        >> msg[Coder, Reviewer](Working)
        >> var('implement')
    )
```

The explicit notifications are a consequence of
[knowledge of choice](/docs/concepts/knowledge-of-alt). They also leave a useful
trace: an observer can distinguish continued exploration from a stalled model
call.
</Step>

<Step>
### Build the review phase

`alt[Reviewer, Coder]` lets the reviewer select a branch addressed to the coder.
On `Ship`, the coder tells the workspace that no further write will arrive. On
`Fix`, the coder performs exactly one additional write. Both branches end with
delivery to the client.

```python compile
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
```

The absence of `rec` in this fragment gives the reviewer one decision. A second
review would require an explicit edge back to a recursive variable.
</Step>

<Step>
### Add implementation and planning

The implementation phase is recursive. Each `Write` returns `Saved`, announces
continued work, and unfolds `implement`. `Done` acknowledges the workspace,
publishes the patch, and enters review.

```python compile
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
```

The complete conversation begins with the client's task. Planning repeats over
`List` and `Read`; `Ready` acknowledges the workspace, hands the plan to the
other roles, and transfers control to the coder.

```python compile
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
```

`close()` requires every recursive variable to be bound and produces a closed
session. Later, `project_all(protocol)` will derive all five local endpoints and
reject an incoherent global conversation before execution.
</Step>

</Steps>

The protocol now encodes the permissions and phase transitions. Continue with
[add tools](/docs/tutorials/coding-harness/add-tools) to attach the filesystem service.

