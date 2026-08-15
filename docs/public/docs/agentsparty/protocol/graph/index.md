# graph (/docs/agentsparty/protocol/graph/index)

Neutral graph views of global and endpoint protocol ASTs.

The graph deliberately contains semantics only.  Coordinates, colours and
renderer-specific fields belong to documentation clients.

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"ProtocolGraph"} href={"/docs/agentsparty/protocol/graph/ProtocolGraph"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"to_graph"} type={"(protocol, role=None) -> ProtocolGraph"}>

Return a neutral graph for a global protocol or one endpoint.

A role-aware global graph receives one ``gap`` edge when the role's first
actions differ across an unobserved alt.  This is deliberately a graph
fact, so visual clients cannot accidentally turn a missing signal into a
colour-only annotation.

<PySourceCode >

```python
def to_graph(
    protocol: SessionType | EndpointType | Fragment[SessionType] | Fragment[EndpointType],
    role: Role | None = None,
) -> ProtocolGraph:
    """Return a neutral graph for a global protocol or one endpoint.

    A role-aware global graph receives one ``gap`` edge when the role's first
    actions differ across an unobserved alt.  This is deliberately a graph
    fact, so visual clients cannot accidentally turn a missing signal into a
    colour-only annotation.
    """
    pre(expr=protocol is not None, message='protocol is required')
    value = _as_protocol(protocol)
    builder = _Builder()

    # Build the requested view from the AST, preserving role and branch data.
    match value:
        case EndpointEnd() | EndpointVar() | EndpointBranch() | EndpointSelect() | EndpointRec():
            pre(expr=role is not None, message='role is required for an endpoint graph')
            subject = cast(Role, role)
            _endpoint_node(value, builder, subject)
            roles = [subject.name]
        case (
            SessionEnd()
            | SessionVar()
            | Interaction()
            | SendTo()
            | RecvFrom()
            | SessionRec()
            | Parallel()
        ):
            _global_node(value, builder, role, None)
            roles = [item.name for item in participants(value)]
        case _:  # pragma: no cover
            assert_never(value)

    safe_assert(expr=bool(builder.nodes), message='a protocol graph must have a root node')
    result: ProtocolGraph = {'nodes': builder.nodes, 'edges': builder.edges, 'roles': roles}
    root_id = result['nodes'][0]['id']
    post(expr=root_id == 'n1', message='graph ids must start at n1')
    return result
```

</PySourceCode>

<div >

<PyParameter name={"protocol"} type={"SessionType | EndpointType | Fragment[SessionType] | Fragment[EndpointType]"} value={null} />
<PyParameter name={"role"} type={"Role | None"} value={"None"} />

</div>

<PyFunctionReturn type={"agentsparty.protocol.graph.ProtocolGraph"} />

</PyFunction>

</Tab>

</Tabs>
