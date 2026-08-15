# Protocol-first (/docs/concepts/protocol-first)

A multiparty conversation is a typed value: named roles, labelled messages,
branches, and loops. `render` prints it, `project` derives each role's
endpoint, and `Cast` binds a participant to every seat.

## A session

Declare the conversation first. The protocol is the source of truth for
every participant that later occupies a role.

```python exec
from agentsparty.protocol import Text, msg, project_all, render
from agentsparty.kernel.role import roles

Writer, Reader = roles('Writer', 'Reader')
Note = Text('Note')
protocol = msg[Writer, Reader](Note).close()

print(render(protocol))
views = project_all(protocol)
assert {role for role, _ in views} == {Writer, Reader}
```

```text
Writer -> Reader : Note(str)
end
```

Control edges (who talks to whom, in which order, under which labels) are
fixed before the run. Content is the only remaining freedom: a participant
fills a typed payload or picks a declared branch. See
[control and content](/docs/concepts/control-and-content).

If a role would have to act differently on a branch it never observed,
`project` raises [[agentsparty.kernel.errors.ProjectionError]] before any model
call. The repair is a declared message. See
[knowledge of alt](/docs/concepts/knowledge-of-alt).

## Cast

`Cast` is the same binding written as a pipeline. Each `play` attaches a
factory to one projected endpoint; `run_sync` demands every role is played.

```python exec
from agentsparty.machine import machine
from agentsparty.participant import says
from agentsparty.protocol import Text, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Writer, Reader = roles('Writer', 'Reader')
Note = Text('Note')
protocol = msg[Writer, Reader](Note)


def assign(view):
    return says(Note, 'hello')


trace = (
    Cast(protocol)
    .play(Writer, machine(assign))
    .play(Reader, machine(lambda view: None))
    .run_sync()
)
print(trace[0].payload)
```

The factory can be an agent, a human, a machine, or a tool service; the
endpoint contract stays the one `project` derived. An OpenAI-backed pair
looks the same, with `agent` in place of `machine`:

```python compile
from openai import AsyncOpenAI
from agentsparty.agent import agent
from agentsparty import OpenAIModel
from agentsparty.protocol import Text, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Writer, Reader = roles('Writer', 'Reader')
protocol = msg[Writer, Reader](Text('Note'))
model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
trace = (
    Cast(protocol)
    .play(Writer, agent(model, 'Send a concise note.'))
    .play(Reader, agent(model, 'Receive the note.'))
    .run_sync()
)
envelope = trace[0]
print(
    f'{envelope.sender.name} -> {envelope.receiver.name}: '
    f'{envelope.label}({envelope.payload!r})'
)
```

Related: [combinators](/docs/concepts/combinators),
[participants and roles](/docs/concepts/participants-and-roles),
[[agentsparty.runtime.Cast]], and [[agentsparty.protocol.render]].

