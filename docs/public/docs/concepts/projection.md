# Projection (/docs/concepts/projection)

A participant cannot act on the whole conversation. Projection derives the
local endpoint for each role: what that role may send, receive, select, and
offer. The global type describes the session; an endpoint describes one
seat.

One tree fans out into as many endpoints as there are roles: each node
either becomes a local action for some role or disappears from that role's
endpoint entirely.

Spelled out, the fan-out is three columns beside the global messages, with
each global line and its local counterparts on one row.

<DiagProjection />

## The projection rule

For a message `A -> B : Label(Payload)`:

- endpoint `A` gets an output to `B`;
- endpoint `B` gets an input from `A`; and
- every other role gets no local action for that node.

For an alt, the chooser gets an internal `select`, the informed peer gets an
external `offer`, and an uninvolved role gets the merge of all projected
continuations.

```python exec
from agentsparty.protocol import Nothing, Text, alt, msg, project_all, render
from agentsparty.kernel.role import roles

Writer, Reviewer, Reader = roles('Writer', 'Reviewer', 'Reader')
Draft = Text('Draft')
Approve = Nothing('Approve')
Reject = Nothing('Reject')
protocol = msg[Writer, Reviewer](Draft) >> alt[Reviewer, Writer](
    Approve >> msg[Writer, Reader](Text('Final')),
    Reject >> msg[Writer, Reader](Text('Rejected')),
)

for role, endpoint in project_all(protocol):
    print(role.name)
    print(render(endpoint))
```

`Final` lives inside the `Approve` branch and `Rejected` inside `Reject`.
A rejected draft never claims to be a final document.

## Projectability

Dropping an invisible alt is safe only when the remaining branch
continuations merge into one endpoint. If one branch asks a role to receive
and another asks it to send, that role would need information it never
received. `project` raises `ProjectionError` at that boundary, before any
participant or model exists.

```python exec
from agentsparty.kernel.errors import ProjectionError
from agentsparty.protocol import Nothing, Text, alt, msg, project
from agentsparty.kernel.role import roles

A, B, C = roles('A', 'B', 'C')
blind = alt[A, B](
    Nothing('Yes') >> msg[A, C]('Y', Text),
    Nothing('No') >> msg[C, A]('N', Text),
).close()
try:
    project(blind, C)
except ProjectionError as error:
    print(type(error).__name__, 'before runtime')
```

A successful projection gives each role a single local protocol consistent
with the global tree. A participant can still fail, a human can still walk
away, and an external API can still hang. The checked properties are listed
in [what you can rely on](/docs/start/what-you-can-rely-on).

Related: [Knowledge of alt](/docs/concepts/knowledge-of-alt),
[[agentsparty.protocol.project]], and [[agentsparty.protocol.project_all]].

