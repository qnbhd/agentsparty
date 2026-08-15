# Observable session (/docs/learn/observable-session)

# 7 — Observable session

The workflow works. Now it is slow, and you need to know why. A tracer is an
observation stream: it records what happened without changing how the session
runs. It does not choose a branch and it does not store replay data — the
journal remains the source for decisions, the tracer explains the run.

## Attach a tracer

```python compile
from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty.protocol import Text, case, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast
from agentsparty.tracing import MemoryTracer

A, B = roles('A', 'B')
# Attach a tracer to observe the run without changing its protocol.
protocol = msg[A, B](Text('Note'))
tracer = MemoryTracer()
model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0))
# The tracer receives events while the OpenAI-backed session runs.
Cast(protocol).play(A, agent(model, 'n')).play(B, human(script())).run_sync(
    tracer=tracer
)
assert tracer.events
print('events', len(tracer.events))
```

The protocol, the bindings, and the run are identical to step 1 — the tracer
was an extra argument. That is the property that matters: observability is
added, never bought by changing the choreography.

## Facets

Events carry a facet that says which layer produced them: runtime, protocol,
model, or tool. "Which facet explains the latency or failure?" is the
question a tracer answers without replaying the session or reading the
journal. `StreamTracer` delivers events as they happen; `MemoryTracer`
collects them for assertions.

The complete step is `docs/examples/tutorial/05_observable_session.py`.

## Where the tutorial leaves you

The same system now has a alt with an observable outcome, typed payloads,
a human participant, a durable journal, and a tracer — every step was a diff,
not a rewrite. The concepts behind these steps are explained in
[Concepts](/docs/concepts/protocol-first), and each individual task has its
own page under [How-to](/docs/how-to/overview).

