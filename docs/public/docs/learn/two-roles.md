# Two roles (/docs/learn/two-roles)

# 1 — Two roles

The system starts with the smallest useful conversation: a Writer sends a
draft to a Reader. You declare the message, bind a participant to each role,
and run the session with an OpenAI model.

## Declare the message

```python exec
from agentsparty.protocol import Text, case, msg, render
from agentsparty.kernel.role import roles

Writer, Reader = roles('Writer', 'Reader')
# Draft is the only label the Writer may author, with a text payload.
Draft = Text('Draft')
protocol = msg[Writer, Reader](Draft)
print(render(protocol))
```

The protocol is a value. `render` shows the whole conversation; `msg`
declares one message edge `Writer -> Reader : Draft(str)`.

The protocol is one value with a single message — rendered before anything
runs:

## Bind and run

```python compile
from openai import AsyncOpenAI
from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty.protocol import Text, case, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Writer, Reader = roles('Writer', 'Reader')
protocol = msg[Writer, Reader](Text('Draft'))
model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0))
trace = (
    Cast(protocol)
    .play(Writer, agent(model, 'draft'))
    .play(Reader, human(script()))
    .run_sync()
)
assert [e.label.name for e in trace] == ['Draft']
print([e.label.name for e in trace])
```

Three pieces work together:

- `Cast(protocol)` projects the protocol into one endpoint per role;
- `.play(role, factory)` binds a participant implementation to each endpoint;
- `.run_sync()` executes the session and returns the delivered envelopes.

The model authored one answer and the runtime delivered exactly one envelope.
Had the protocol required a second authored message, the runtime would have
requested more work — the protocol still defines the required conversation.

## The diff so far

```text
two roles: Writer --Draft--> Reader
```

Next: [add a alt](/docs/learn/add-a-alt) — the Reviewer enters.
