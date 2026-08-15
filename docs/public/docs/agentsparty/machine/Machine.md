# Machine (/docs/agentsparty/machine/Machine)

Participant whose alts are computed rather than authored.

The third kind of participant, beside ``Agent`` (a model authors) and
``Human`` (a person authors). Its memory is the messages it has taken part
in, in order — messages it received and messages it sent, so that a live
run and a replayed run leave it in the same state.

## Attributes

<PyAttribute name={"endpoint_contract"} type={"EndpointType"} value={"associate(declares, proto, role)"} />

<PyAttribute name={"seen"} type={"tuple[Envelope, ...]"} value={null}>

The messages this machine took part in, in order.

</PyAttribute>

## Functions

<PyFunction name={"__init__"} type={"(self, role, proto, decide, declares=None) -> None"}>

Bind *role* to *proto* and drive it with *decide*.

<PySourceCode >

```python
def __init__(
    self,
    role: Role,
    proto: SessionType,
    decide: Decide,
    declares: EndpointType | None = None,
) -> None:
    """Bind *role* to *proto* and drive it with *decide*.

    Args:
        role: The role this machine plays.
        proto: The choreography; projected locally on construction.
        decide: The pure function that picks a branch and its raw payload.
        declares: An optional endpoint contract; defaults to the projection.

    Raises:
        ConformanceError: if *declares* is not a subtype of the projection.
    """
    self.role = role
    self.endpoint_contract: EndpointType = associate(declares, proto, role)
    self._decide = decide
    self._seen: list[Envelope] = []
```

</PySourceCode>

<div >

<PyParameter name={"role"} type={"Role"} value={undefined}>

The role this machine plays.

</PyParameter>
<PyParameter name={"proto"} type={"SessionType"} value={undefined}>

The choreography; projected locally on construction.

</PyParameter>
<PyParameter name={"decide"} type={"Decide"} value={undefined}>

The pure function that picks a branch and its raw payload.

</PyParameter>
<PyParameter name={"declares"} type={"EndpointType | None"} value={"None"}>

An optional endpoint contract; defaults to the projection.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"at"} type={"(cls, role, endpoint, decide) -> Machine"}>

Bind *role* under a ready *endpoint* (cast entry).

<PySourceCode >

```python
@classmethod
def at(cls, role: Role, endpoint: EndpointType, decide: Decide) -> Machine:
    """Bind *role* under a ready *endpoint* (cast entry).

    Args:
        role: The role this machine plays.
        endpoint: The projected endpoint for *role*.
        decide: The pure function that picks a branch and its raw payload.
    """
    machine = object.__new__(cls)
    machine.role = role
    machine.endpoint_contract = endpoint
    machine._decide = decide
    machine._seen = []
    return machine
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"role"} type={"Role"} value={undefined}>

The role this machine plays.

</PyParameter>
<PyParameter name={"endpoint"} type={"EndpointType"} value={undefined}>

The projected endpoint for *role*.

</PyParameter>
<PyParameter name={"decide"} type={"Decide"} value={undefined}>

The pure function that picks a branch and its raw payload.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.machine.Machine"} />

</PyFunction>

<PyFunction name={"select"} type={"(self, receiver, branches) -> Chosen[B]"}>

Compute a alt and remember it as a message this machine sent.

<PySourceCode >

```python
async def select(
    self,
    receiver: Role,
    branches: NonEmptyMap[Label, B],
) -> Chosen[B]:
    """Compute a alt and remember it as a message this machine sent.

    Args:
        receiver: The role that will receive the chosen message.
        branches: The labelled alts offered here.

    Returns:
        The chosen branch together with its decoded payload.

    Raises:
        SelectionError: if ``decide`` names a label that is not on offer.
    """
    offered = branches
    # ask the decision function:
    labels = ne_tuple(*sorted(offered))
    alt = self._decide(View(self.seen, receiver, labels))
    # decode at the boundary, so `decode(raw) == payload` holds by construction:
    branch = chosen_branch(offered, alt.label)
    payload = branch.payload.decode(alt.payload)
    # remember what we sent, exactly as `recall` would on replay:
    self._seen.append(Envelope(self.role, receiver, alt.label, payload))
    return Chosen(branch=branch, payload=payload, raw=alt.payload)
```

</PySourceCode>

<div >

<PyParameter name={"receiver"} type={"Role"} value={undefined}>

The role that will receive the chosen message.

</PyParameter>
<PyParameter name={"branches"} type={"NonEmptyMap[Label, B]"} value={undefined}>

The labelled alts offered here.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.core.Chosen"}>

The chosen branch together with its decoded payload.

</PyFunctionReturn>

</PyFunction>

<PyFunction name={"offer"} type={"(self, envelope) -> None"}>

Remember *envelope* as a message this machine received.

<PySourceCode >

```python
async def offer(self, envelope: Envelope) -> None:
    """Remember *envelope* as a message this machine received.

    Args:
        envelope: The protocol message being delivered.
    """
    self._seen.append(envelope)
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

Remember *envelope* as a message this machine sent earlier.

<PySourceCode >

```python
async def recall(self, envelope: Envelope) -> None:
    """Remember *envelope* as a message this machine sent earlier.

    Args:
        envelope: The protocol message this machine sent earlier.
    """
    self._seen.append(envelope)
```

</PySourceCode>

<div >

<PyParameter name={"envelope"} type={"Envelope"} value={undefined}>

The protocol message this machine sent earlier.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"cancel"} type={"(self, notice) -> None"}>

Forget the session: a cancelled machine has seen nothing.

<PySourceCode >

```python
async def cancel(self, notice: Cancelled) -> None:
    """Forget the session: a cancelled machine has seen nothing.

    Args:
        notice: Why the session was rolled up.
    """
    self._seen.clear()
    post(expr=not self.seen, message='a cancelled machine must remember nothing')
```

</PySourceCode>

<div >

<PyParameter name={"notice"} type={"Cancelled"} value={undefined}>

Why the session was rolled up.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
