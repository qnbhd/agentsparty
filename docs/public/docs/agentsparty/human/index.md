# human (/docs/agentsparty/human/index)

Human-driven participants and the IO seams that drive them.

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"HumanIo"} href={"/docs/agentsparty/human/HumanIo"} />
<Card title={"CliHumanIo"} href={"/docs/agentsparty/human/CliHumanIo"} />
<Card title={"ScriptedHumanIo"} href={"/docs/agentsparty/human/ScriptedHumanIo"} />
<Card title={"Human"} href={"/docs/agentsparty/human/Human"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"script"} type={"(*answers) -> ScriptedHumanIo"}>

A scripted IO seam from ordered [`Choice`](/docs/agentsparty/participant/Choice) values.

<PySourceCode >

```python
def script(*answers: Choice) -> ScriptedHumanIo:
    """A scripted IO seam from ordered :class:`~agentsparty.participant.Choice` values.

    Args:
        *answers: Choices the human will make, in order.
    """
    return ScriptedHumanIo(list(answers))
```

</PySourceCode>

<div >

<PyParameter name={"answers"} type={"Choice"} value={"()"} />

</div>

<PyFunctionReturn type={"agentsparty.human.ScriptedHumanIo"} />

</PyFunction>
<PyFunction name={"human"} type={"(io) -> Callable[[Role, EndpointType], Participant]"}>

Casting factory: bind *io* when a role is played.

Returns a ``(role, endpoint) -> Human`` for [`play`](/docs/agentsparty/runtime/Cast).

<PySourceCode >

```python
def human(io: HumanIo) -> Callable[[Role, EndpointType], Participant]:
    """Casting factory: bind *io* when a role is played.

    Returns a ``(role, endpoint) -> Human`` for :meth:`~agentsparty.runtime.Cast.play`.

    Args:
        io: Where alts and messages are presented to the human.
    """
    return partial(_bind_human, io)
```

</PySourceCode>

<div >

<PyParameter name={"io"} type={"HumanIo"} value={undefined}>

Where alts and messages are presented to the human.

</PyParameter>

</div>

<PyFunctionReturn type={"collections.abc.Callable[[agentsparty.kernel.role.Role, agentsparty.protocol.EndpointType], agentsparty.participant.Participant]"} />

</PyFunction>

</Tab>

</Tabs>
