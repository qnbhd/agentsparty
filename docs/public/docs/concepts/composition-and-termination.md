# Composition and termination (/docs/concepts/composition-and-termination)

A protocol is rarely one linear exchange. You reuse a fragment, plug
components against a contract, or loop until a condition holds. These
operators differ by the shape they preserve; an `Allowance` is the runtime
bound that keeps a live run finite.

The primitive constructors (`>>`, `alt`, `rec` / `var`, `par`) are taught on
[combinators](/docs/concepts/combinators).

## Routines

A `Routine` is a named fragment with formal roles. `do` binds actual roles
and returns a fragment you can sequence further. The call expands into the
ordinary session tree.

```python exec
from agentsparty.protocol import Routine, Text, do, msg, render
from agentsparty.kernel.role import roles

Sender, Receiver = roles('Sender', 'Receiver')
review = Routine(
    'review',
    (Sender, Receiver),
    msg[Sender, Receiver](Text('Draft')),
)
Writer, Editor = roles('Writer', 'Editor')
print(render(do(review, Writer, Editor).close()))
```

`do` rejects an arity mismatch and rejects binding the same actual role to
two formal parameters.

## Composition

`compose(contract, components)` builds one session protocol from components that
fit a shared interface. Internal role sets must be disjoint. Roles in the
contract that no component owns stay served by the contract itself.

```python exec
from agentsparty.protocol import Text, compose, msg, owning, render
from agentsparty.kernel.role import roles

Brand, Analyst, Photo = roles('Brand', 'Analyst', 'Photo')
Product = Text('Product')
Copy = Text('Copy')
Post = Text('Post')
text = owning(Analyst).defining(
    msg[Brand, Analyst](Product) >> msg[Analyst, Photo](Copy),
)
image = owning(Photo).defining(
    msg[Analyst, Photo](Copy) >> msg[Photo, Brand](Post),
)
contract = (
    msg[Brand, Analyst](Product)
    >> msg[Analyst, Photo](Copy)
    >> msg[Photo, Brand](Post)
).close()
print(render(compose(contract, [text, image])))
```

The same call laid out in space: the contract sequence on top, one zone per
component below. `Brand` falls into no zone, so the contract keeps serving
it, and no role may appear in two zones at once.

<ComposeOwnershipMiniature />

See [[agentsparty.protocol.compose]] and [[agentsparty.protocol.owning]].

## Recursion and termination

`may_terminate` asks whether some finite path reaches `end`.
`must_terminate` asks whether every path does. A recursive protocol with an
exit branch satisfies the first predicate; a cycle with no exit satisfies
neither.

<TerminationMiniature />

Both panels carry the same back edge; only the left one also has an edge to
`end`. That single edge is the whole difference the two predicates report:

```python exec
from agentsparty.protocol import (
    Text,
    may_terminate,
    msg,
    must_terminate,
    rec,
    var,
)
from agentsparty.kernel.role import roles

A, B = roles('A', 'B')
finite = msg[A, B](Text('Done')).close()
looped = rec('X', msg[A, B](Text('Tick')) >> var('X')).close()
print('finite must_terminate:', must_terminate(finite))
print('looped may_terminate:', may_terminate(looped))
```

Neither predicate says a live participant will answer before a deadline.

## Budget

`Allowance` bounds protocol steps and recursion unfolds for one run.
Replayed journal decisions do not consume it. The first failure cancels
every bound participant. Three distinct limits produce three distinct
errors: [[agentsparty.kernel.errors.StepLimitError]],
[[agentsparty.kernel.errors.RecursionLimitError]], and
[[agentsparty.kernel.errors.TokenLimitError]].

```python exec
from agentsparty.kernel.budget import Allowance
from agentsparty.kernel.errors import StepLimitError
from agentsparty.machine import machine
from agentsparty.participant import says
from agentsparty.protocol import Text, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

A, B = roles('A', 'B')
Note = Text('Note')
protocol = msg[A, B](Note)

try:
    (
        Cast(protocol)
        .play(A, machine(lambda view: says(Note, 'hi')))
        .play(B, machine(lambda view: None))
        .run_sync(allowance=Allowance(steps=0))
    )
except StepLimitError as err:
    print(type(err).__name__)
```

Each bound has its own gauge and its own error; nothing collapses them into
a single "budget exceeded":

<AllowanceMiniature />

`Deadline` closes the current waiting window. See
[[agentsparty.kernel.budget.Allowance]].

