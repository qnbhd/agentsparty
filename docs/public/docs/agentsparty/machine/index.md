# machine (/docs/agentsparty/machine/index)

Computed participant: a alt that is a function of what has been seen.

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"View"} href={"/docs/agentsparty/machine/View"} />
<Card title={"Decide"} href={"/docs/agentsparty/machine/Decide"} />
<Card title={"Machine"} href={"/docs/agentsparty/machine/Machine"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"machine"} type={"(decide) -> Callable[[Role, EndpointType], Participant]"}>

Casting factory: bind *decide* when a role is played.

Returns a ``(role, endpoint) -> Machine`` for [`play`](/docs/agentsparty/runtime/Cast).

<PySourceCode >

```python
def machine(decide: Decide) -> Callable[[Role, EndpointType], Participant]:
    """Casting factory: bind *decide* when a role is played.

    Returns a ``(role, endpoint) -> Machine`` for :meth:`~agentsparty.runtime.Cast.play`.

    Args:
        decide: The pure function that picks a branch and its raw payload.
    """
    return partial(_bind_machine, decide)
```

</PySourceCode>

<div >

<PyParameter name={"decide"} type={"Decide"} value={undefined}>

The pure function that picks a branch and its raw payload.

</PyParameter>

</div>

<PyFunctionReturn type={"collections.abc.Callable[[agentsparty.kernel.role.Role, agentsparty.protocol.EndpointType], agentsparty.participant.Participant]"} />

</PyFunction>

</Tab>

</Tabs>
