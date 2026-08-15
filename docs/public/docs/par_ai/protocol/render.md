# render (/docs/agentsparty/protocol/render/index)

Human-readable rendering of session and endpoint types.

Unstable format: suitable for diagrams and diagnostics, not for digests.

<PyAttribute name={"MICROSECONDS_PER_SECOND"} type={"Final"} value={"1000000"} />

<PyAttribute name={"SECONDS_PER_MINUTE"} type={"Final"} value={"60"} />

<PyAttribute name={"MINUTES_PER_HOUR"} type={"Final"} value={"60"} />

<PyAttribute name={"HOURS_PER_DAY"} type={"Final"} value={"24"} />

<PyAttribute name={"MICROSECONDS_PER_MINUTE"} type={"Final"} value={"SECONDS_PER_MINUTE * MICROSECONDS_PER_SECOND"} />

<PyAttribute name={"MICROSECONDS_PER_HOUR"} type={"Final"} value={"MINUTES_PER_HOUR * MICROSECONDS_PER_MINUTE"} />

<PyAttribute name={"MICROSECONDS_PER_DAY"} type={"Final"} value={"HOURS_PER_DAY * MICROSECONDS_PER_HOUR"} />

<Tabs items={["Functions"]}>

<Tab value={"Functions"}>

<PyFunction name={"render"} type={"(node, indent=0) -> str"}>

Render *node* as an indented text diagram.

An open session [`Fragment`](/docs/agentsparty/protocol/language/core/Fragment) is closed at this
boundary so callers need not write ``.close()`` only to print a diagram.

<PySourceCode >

```python
def render(
    node: SessionType | EndpointType | Fragment[SessionType],
    indent: int = 0,
) -> str:
    """Render *node* as an indented text diagram.

    An open session :class:`~agentsparty.protocol.language.core.Fragment` is closed at this
    boundary so callers need not write ``.close()`` only to print a diagram.

    Args:
        node: The protocol to render, or a session fragment that will be closed.
        indent: Number of two-space levels to indent the root.

    Returns:
        The rendered text, one line per protocol node.
    """
    match node:
        case Fragment() as fragment:
            return render(cast(SessionType, fragment.close()), indent=indent)
        case _:
            return _render_node(node, indent)
```

</PySourceCode>

<div >

<PyParameter name={"node"} type={"SessionType | EndpointType | Fragment[SessionType]"} value={undefined}>

The protocol to render, or a session fragment that will be closed.

</PyParameter>
<PyParameter name={"indent"} type={"int"} value={"0"}>

Number of two-space levels to indent the root.

</PyParameter>

</div>

<PyFunctionReturn type={"str"}>

The rendered text, one line per protocol node.

</PyFunctionReturn>

</PyFunction>

</Tab>

</Tabs>
