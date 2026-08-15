# Protocol notation (/docs/reference/protocol-notation)

# Protocol notation

`render` prints a compact multiparty session-type notation.

| Form | Meaning |
| --- | --- |
| `A -> B : Label(type)` | message with payload |
| alt block `A -> B` with labelled cases | alt by A toward B |
| `alt[A, B]` | shorthand for `alt[A, B] ( case, …)` |
| `!` / `?` on endpoints | send / receive after projection |
| `rec X. ...` / `X` | recursion binder / variable |
| parallel blocks | independent tracks |

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

Multiparty Session Types is the theory name; product docs use **global
choreography** and **endpoint protocol** in ordinary prose first. The two
DSLs that build these types are the
[choreography](/docs/concepts/choreography) spelling and the
[combinator](/docs/concepts/combinators) facade; see
[[agentsparty.protocol.render]] for the rendering API. In the combinator facade, `alt[A, B]` is shorthand for
`alt[A, B] ( …)`: the same alt with the roles moved into a subscript.

