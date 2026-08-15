# Human (/docs/agentsparty/human/Human)

Peer participant driven by HumanIo (CLI or scripted).

## Attributes

<PyAttribute name={"endpoint_contract"} type={"EndpointType"} value={"associate(declares, proto, role)"} />

## Functions

<PyFunction name={"__init__"} type={"(self, role, proto, io, declares=None) -> None"}>

Bind *role* to *proto* and drive it through *io*.

<PySourceCode >

```python
def __init__(
    self,
    role: Role,
    proto: SessionType,
    io: HumanIo,
    declares: EndpointType | None = None,
) -> None:
    """Bind *role* to *proto* and drive it through *io*.

    Args:
        role: The role this human plays in the protocol.
        proto: The choreography; projected locally on construction.
        io: Where alts and messages are presented to the human.
        declares: An optional endpoint contract; defaults to the projection.

    Raises:
        ConformanceError: if *declares* is not a subtype of the projection.
    """
    self.role = role
    self.endpoint_contract: EndpointType = associate(declares, proto, role)
    self._io = io
```

</PySourceCode>

<div >

<PyParameter name={"role"} type={"Role"} value={undefined}>

The role this human plays in the protocol.

</PyParameter>
<PyParameter name={"proto"} type={"SessionType"} value={undefined}>

The choreography; projected locally on construction.

</PyParameter>
<PyParameter name={"io"} type={"HumanIo"} value={undefined}>

Where alts and messages are presented to the human.

</PyParameter>
<PyParameter name={"declares"} type={"EndpointType | None"} value={"None"}>

An optional endpoint contract; defaults to the projection.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"at"} type={"(cls, role, endpoint, io) -> Human"}>

Bind *role* under a ready *endpoint* (cast entry).

<PySourceCode >

```python
@classmethod
def at(cls, role: Role, endpoint: EndpointType, io: HumanIo) -> Human:
    """Bind *role* under a ready *endpoint* (cast entry).

    Args:
        role: The role this human plays.
        endpoint: The projected endpoint for *role*.
        io: Where alts and messages are presented.
    """
    human = object.__new__(cls)
    human.role = role
    human.endpoint_contract = endpoint
    human._io = io
    return human
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"role"} type={"Role"} value={undefined}>

The role this human plays.

</PyParameter>
<PyParameter name={"endpoint"} type={"EndpointType"} value={undefined}>

The projected endpoint for *role*.

</PyParameter>
<PyParameter name={"io"} type={"HumanIo"} value={undefined}>

Where alts and messages are presented.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.human.Human"} />

</PyFunction>

<PyFunction name={"select"} type={"(self, receiver, branches) -> Chosen[B]"}>

Delegate the alt to the underlying `HumanIo`.

<PySourceCode >

```python
async def select(
    self,
    receiver: Role,
    branches: NonEmptyMap[Label, B],
) -> Chosen[B]:
    """Delegate the alt to the underlying :class:`HumanIo`.

    Args:
        receiver: The role that will receive the chosen message.
        branches: The labelled alts offered to the human.

    Returns:
        The chosen branch together with its decoded payload.
    """
    return await self._io.choose(self.role, receiver, branches)
```

</PySourceCode>

<div >

<PyParameter name={"receiver"} type={"Role"} value={undefined}>

The role that will receive the chosen message.

</PyParameter>
<PyParameter name={"branches"} type={"NonEmptyMap[Label, B]"} value={undefined}>

The labelled alts offered to the human.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.core.Chosen"}>

The chosen branch together with its decoded payload.

</PyFunctionReturn>

</PyFunction>

<PyFunction name={"offer"} type={"(self, envelope) -> None"}>

Delegate the notification to the underlying `HumanIo`.

<PySourceCode >

```python
async def offer(self, envelope: Envelope) -> None:
    """Delegate the notification to the underlying :class:`HumanIo`.

    Args:
        envelope: The protocol message being delivered.
    """
    await self._io.notify(self.role, envelope)
```

</PySourceCode>

<div >

<PyParameter name={"envelope"} type={"Envelope"} value={undefined}>

The protocol message being delivered.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"recall"} type={"(self, envelope) -> None"}>

Delegate the reminder to the underlying `HumanIo`.

<PySourceCode >

```python
async def recall(self, envelope: Envelope) -> None:
    """Delegate the reminder to the underlying :class:`HumanIo`.

    Args:
        envelope: The protocol message this human sent earlier.
    """
    await self._io.recall(self.role, envelope)
```

</PySourceCode>

<div >

<PyParameter name={"envelope"} type={"Envelope"} value={undefined}>

The protocol message this human sent earlier.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"cancel"} type={"(self, notice) -> None"}>

Delegate the notice to the underlying `HumanIo`.

<PySourceCode >

```python
async def cancel(self, notice: Cancelled) -> None:
    """Delegate the notice to the underlying :class:`HumanIo`.

    Args:
        notice: Why the session was rolled up.
    """
    await self._io.cancel(self.role, notice)
```

</PySourceCode>

<div >

<PyParameter name={"notice"} type={"Cancelled"} value={undefined}>

Why the session was rolled up.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
