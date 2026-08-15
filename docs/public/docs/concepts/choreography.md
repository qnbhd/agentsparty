# Choreography (/docs/concepts/choreography)

`@choreography` records the same session protocol from Python statements.
`c.say`, `c.decide`, `c.loop`, `c.times`, and `c.parallel` are the
operators. The result is an ordinary [[agentsparty.protocol.session.types.SessionType]],
and `equal_session` holds against the combinator twin.

<ChoreographyEquivalence />

Both spellings build the identical tree, so nothing downstream (`render`,
`project`, `Cast`) can tell which one produced it. Pick the facade that
reads better for the protocol at hand.

## say

```python exec
from agentsparty.choreography import Chor, choreography
from agentsparty.protocol import equal_session, msg, render
from agentsparty.kernel.role import roles

Writer, Reader = roles('Writer', 'Reader')


@choreography
def note(c: Chor) -> None:
    c.say(Writer, Reader, 'Note')


print(render(note()))
print(equal_session(note(), msg[Writer, Reader]('Note').close()))
```

## decide

`c.decide(chooser, informed)` is `alt`. Each `verdict.case` names a
labelled continuation.

```python exec
from agentsparty.choreography import Chor, choreography
from agentsparty.protocol import Nothing, Text, alt, equal_session, msg, render
from agentsparty.kernel.role import roles

Writer, Reviewer = roles('Writer', 'Reviewer')
Draft = Text('Draft')
Approve = Nothing('Approve')
Reject = Text('Reject')


@choreography
def review(c: Chor) -> None:
    c.say(Writer, Reviewer, Draft)
    with c.decide(Reviewer, Writer) as verdict:
        with verdict.case(Approve):
            pass
        with verdict.case(Reject):
            pass


combo = msg[Writer, Reviewer](Draft) >> alt[Reviewer, Writer](Approve, Reject)
print(render(review()))
print(equal_session(review(), combo.close()))
```

## loop and times

`c.loop(name)` is guarded recursion: `again()` jumps back to the binder.
`c.times(n)` unrolls a fixed number of copies.

```python exec
from agentsparty.choreography import Chor, choreography
from agentsparty.protocol import (
    Text,
    equal_session,
    msg,
    rec,
    render,
    repeat,
    var,
)
from agentsparty.kernel.role import roles

A, B = roles('A', 'B')


@choreography
def poll(c: Chor) -> None:
    with c.loop('Poll') as tick:
        c.say(A, B, 'Tick')
        tick.again()


@choreography
def three_ticks(c: Chor) -> None:
    for _ in c.times(3):
        c.say(A, B, 'Tick')


looped = rec('Poll', msg[A, B]('Tick', Text) >> var('Poll')).close()
unrolled = repeat(3, msg[A, B]('Tick', Text)).close()
print(equal_session(poll(), looped))
print(equal_session(three_ticks(), unrolled))
print(render(three_ticks()))
```

## parallel

`c.parallel()` opens tracks whose role sets must be disjoint. Each
`p.branch()` is one track.

```python exec
from agentsparty.choreography import Chor, choreography
from agentsparty.protocol import equal_session, msg, par, render
from agentsparty.kernel.role import roles

A, B, C, D = roles('A', 'B', 'C', 'D')


@choreography
def split(c: Chor) -> None:
    with c.parallel() as p:
        with p.branch():
            c.say(A, B, 'L')
        with p.branch():
            c.say(C, D, 'R')


combo = par(msg[A, B]('L'), msg[C, D]('R')).close()
print(equal_session(split(), combo))
print(render(split()))
```

Offline twins live under `examples/offline/*_chor.py`. The combinator
spelling of the same operators is on
[combinators](/docs/concepts/combinators). See
[[agentsparty.choreography.chor.choreography]].

