# Protocol notation (/docs/reference/protocol-notation)

`render` prints a compact multiparty session-protocol notation.

## Grammar

| Form | Meaning |
| --- | --- |
| `A -> B : Label(type)` | message with payload |
| alt block `A -> B` with labelled cases | alt by A toward B |
| `alt[A, B]` | shorthand for `alt[A, B] ( case, …)` |
| `!` / `?` on endpoints | send / receive after projection |
| `rec X. ...` / `X` | recursion binder / variable |
| parallel blocks | independent tracks |

## What render prints

```python exec
from agentsparty.protocol import Nothing, Text, case, alt, msg, render
from agentsparty.kernel.role import roles

A, B = roles('A', 'B')
print(
    render(
        (
            msg[A, B]('Ping', Text) >> alt[B, A](Nothing('Ok'), Nothing('No'))
        ).close()
    )
)
```

## Where the notation comes from

The project takes its inspiration from
[Multiparty Session Types (MPST)](https://dl.acm.org/doi/10.1007/978-3-030-36987-3_5),
though the product docs say **global choreography** and **endpoint protocol**
in ordinary prose first. For related work on agent interaction protocols, see
[Global Types for Agent Interaction Protocols](https://dl.acm.org/doi/10.1145/3586031).

Two DSLs build these protocols: the
[choreography](/docs/concepts/choreography) spelling and the
[combinator](/docs/concepts/combinators) facade. In the combinator facade,
`alt[A, B]` is shorthand for `alt[A, B] ( …)`, the same alt with its roles
moved into a subscript. The rendering API itself is
[[agentsparty.protocol.render]].

