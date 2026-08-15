# Typed payloads (/docs/learn/typed-payloads)

# 4 — Typed payloads

A branch label answers "which operation happened?". A payload codec answers
"what value is allowed on that operation?". Keep those concerns separate: the
protocol names the message and the codec parses its content before it reaches
the participant.

The workflow gains a Counter role that reports how many drafts passed review.
A plain `int` would accept negative counts. Refine the codec so the protocol
itself refuses them.

## Refine at the boundary

```python compile
from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty.protocol import Integer, case, msg, refine, render
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Counter, Display = roles('Counter', 'Display')
# Refine Integer so the protocol accepts only positive counts.
Positive = Integer.where('positive', lambda number: number > 0)
protocol = msg[Counter, Display](Positive('Count'))
print(render(protocol))
# The OpenAI model supplies a payload that satisfies the refinement.
model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0))
trace = (
    # The runtime decodes and validates the payload at the message boundary.
    Cast(protocol)
    .play(Counter, agent(model, 'send a positive count'))
    .play(Display, human(script()))
    .run_sync()
)
assert trace[0].payload == 3
print(trace[0].payload)
```

The `Positive` codec rejects zero and negative values during decode — try
sending `-1` and the runtime refuses at the boundary. Downstream code works
with an integer that satisfies the invariant instead of carrying an unchecked
`int` plus a comment that says "must be positive".

## The vocabulary

- `Text`, `Integer`, `Flag` — primitive codecs;
- `list_of`, `dict_of`, `optional`, `one_of` — containers;
- `refine(codec, name, predicate)` — add a runtime predicate;
- `case(label, codec)` — attach a codec to a message label.

`render` prints the declared codec, not an untyped Python value. The complete
step is `docs/examples/tutorial/02_typed_payloads.py`.

Next: [human review](/docs/learn/human-review).
