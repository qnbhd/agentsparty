# Add a alt (/docs/learn/add-a-alt)

# 2 — Add a alt

The Writer sends a draft; now a Reviewer decides between `Approve` and
`Reject`. A alt is a labelled set of continuations: the first role
argument is the chooser, the second receives the branch label.

## Extend the protocol

```python exec
from agentsparty.protocol import Nothing, Text, case, alt, msg, render
from agentsparty.kernel.role import roles

Writer, Reviewer = roles('Writer', 'Reviewer')
# Draft carries content; Approve and Reject carry only the branch decision.
Draft = Text('Draft')
Approve = Nothing('Approve')
Reject = Text('Reject')
protocol = msg[Writer, Reviewer](Draft) >> alt[Reviewer, Writer](
    Approve, Reject
)
print(render(protocol))
```

Two things changed from step 1: a Reviewer joined the Writer's conversation,
and the Reviewer owns a alt toward the Writer. The `>>` operator sequences
the draft before the alt.

The protocol is still one value with two branches — rendered before anything
runs:

<DiagAddAChoice />

## Run the approved path

```python compile
from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty.participant import says
from agentsparty.protocol import Nothing, Text, case, alt, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Writer, Reviewer = roles('Writer', 'Reviewer')
Draft = Text('Draft')
Approve = Nothing('Approve')
Reject = Text('Reject')
protocol = msg[Writer, Reviewer](Draft) >> alt[Reviewer, Writer](
    Approve, Reject
)
model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0))
trace = (
    Cast(protocol)
    .play(Writer, agent(model, 'draft'))
    .play(Reviewer, human(script(says(Approve))))
    .run_sync()
)
assert [e.label.name for e in trace] == ['Draft', 'Approve']
print([e.label.name for e in trace])
```

The runtime sequence is `select Draft → offer Draft → select Approve`. The
model authored the draft; the Reviewer (a human participant here) picked
`Approve`.

## The design question

The question is not "where do I put an if statement?". It is "which roles
must know the decision to follow the next step safely?". The `Reject` branch
currently sends nothing to anyone beyond the Reviewer's alt — and the next
step shows why that is a problem the projection catches.

Next: [knowledge of alt](/docs/learn/knowledge-of-alt).

