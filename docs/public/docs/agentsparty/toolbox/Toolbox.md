# Toolbox (/docs/agentsparty/toolbox/Toolbox)

Participant that answers requests: one tool per label, dispatched.

The fourth kind of participant, beside ``Agent`` (a model authors),
``Human`` (a person authors) and ``Machine`` (a function of the whole
history computes). A toolbox is a function of the *request*: it keeps
nothing between requests and never reads the conversation. That is what
lets a tool be tested in one line, and what lets a resumed session skip the
effect instead of repeating it.

## Attributes

<PyAttribute name={"endpoint_contract"} type={"EndpointType"} value={"associate(declares, proto, role)"} />

## Functions

<PyFunction name={"__init__"} type={"(self, role, proto, tools, declares=None) -> None"}>

Bind *role* to *proto* and answer its requests with *tools*.

<PySourceCode >

```python
def __init__(
    self,
    role: Role,
    proto: SessionType,
    tools: Iterable[Tool[Any]],
    declares: EndpointType | None = None,
) -> None:
    """Bind *role* to *proto* and answer its requests with *tools*.

    Args:
        role: The role this toolbox plays. Its projection must be a
            service: never speaks first, answers every request it accepts
            right away, to the role that asked.
        proto: The choreography; projected locally on construction.
        tools: Exactly one tool per request the projection declares.
        declares: The endpoint type this participant claims to follow. It must
            be a subtype of the projection of *proto* on *role*: it
            may accept more labels than the choreography sends it, and send
            fewer than the choreography allows. Defaults to the projection
            itself.

    Raises:
        ValueError: if the projection is not a service, if the tools do not
            cover its requests exactly, or if a tool was written against a
            different payload codec than the protocol declares.
        ConformanceError: if *declares* is not a subtype of the projection.
    """
    self.role = role
    self.endpoint_contract: EndpointType = associate(declares, proto, role)
    self._tools = _match_tools(_requests(self.endpoint_contract), tools, role)
    self._awaiting: _Awaiting = _IDLE
```

</PySourceCode>

<div >

<PyParameter name={"role"} type={"Role"} value={undefined}>

The role this toolbox plays. Its projection must be a
service: never speaks first, answers every request it accepts
right away, to the role that asked.

</PyParameter>
<PyParameter name={"proto"} type={"SessionType"} value={undefined}>

The choreography; projected locally on construction.

</PyParameter>
<PyParameter name={"tools"} type={"Iterable[Tool[Any]]"} value={undefined}>

Exactly one tool per request the projection declares.

</PyParameter>
<PyParameter name={"declares"} type={"EndpointType | None"} value={"None"}>

The endpoint type this participant claims to follow. It must
be a subtype of the projection of *proto* on *role*: it
may accept more labels than the choreography sends it, and send
fewer than the choreography allows. Defaults to the projection
itself.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"at"} type={"(cls, role, endpoint, tools) -> Toolbox"}>

Bind *role* under a ready *endpoint* (cast entry).

<PySourceCode >

```python
@classmethod
def at(
    cls,
    role: Role,
    endpoint: EndpointType,
    tools: Iterable[Tool[Any]],
) -> Toolbox:
    """Bind *role* under a ready *endpoint* (cast entry).

    Args:
        role: The role this toolbox plays.
        endpoint: The projected endpoint for *role* (must be a service).
        tools: Exactly one tool per request the endpoint declares.
    """
    box = object.__new__(cls)
    box.role = role
    box.endpoint_contract = endpoint
    box._tools = _match_tools(_requests(endpoint), tools, role)
    box._awaiting = _IDLE
    return box
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"role"} type={"Role"} value={undefined}>

The role this toolbox plays.

</PyParameter>
<PyParameter name={"endpoint"} type={"EndpointType"} value={undefined}>

The projected endpoint for *role* (must be a service).

</PyParameter>
<PyParameter name={"tools"} type={"Iterable[Tool[Any]]"} value={undefined}>

Exactly one tool per request the endpoint declares.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.toolbox.Toolbox"} />

</PyFunction>

<PyFunction name={"select"} type={"(self, receiver, branches) -> Chosen[B]"}>

Answer the outstanding request and go back to waiting.

<PySourceCode >

```python
async def select(
    self,
    receiver: Role,
    branches: NonEmptyMap[Label, B],
) -> Chosen[B]:
    """Answer the outstanding request and go back to waiting.

    Args:
        receiver: The role that asked; it receives the answer.
        branches: The replies the protocol offers for this request.

    Returns:
        The chosen reply together with its decoded payload.

    Raises:
        SelectionError: if the tool names a reply that is not on offer.
    """
    offered = branches
    # take the request off the slot, so one request is answered once:
    pending = _outstanding(self._awaiting, self.role)
    self._awaiting = _IDLE
    # run the tool under its own span:
    answer = await self._answered(pending)
    # decode at the boundary, so `decode(raw) == payload` holds by construction:
    branch = chosen_branch(offered, answer.label)
    post(expr=self._awaiting == _IDLE, message='a toolbox must owe nothing after answering')
    return Chosen(
        branch=branch,
        payload=branch.payload.decode(answer.payload),
        raw=answer.payload,
    )
```

</PySourceCode>

<div >

<PyParameter name={"receiver"} type={"Role"} value={undefined}>

The role that asked; it receives the answer.

</PyParameter>
<PyParameter name={"branches"} type={"NonEmptyMap[Label, B]"} value={undefined}>

The replies the protocol offers for this request.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.core.Chosen"}>

The chosen reply together with its decoded payload.

</PyFunctionReturn>

</PyFunction>

<PyFunction name={"offer"} type={"(self, envelope) -> None"}>

Take *envelope* as the request to answer next.

<PySourceCode >

```python
async def offer(self, envelope: Envelope) -> None:
    """Take *envelope* as the request to answer next.

    Args:
        envelope: The protocol message being delivered.
    """
    role_name = self.role.name
    label = envelope.label
    pre(
        expr=self._awaiting == _IDLE,
        message=f'{role_name} was given {label} with an answer still owed',
    )
    self._awaiting = _Pending(envelope.label, envelope.payload)
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

Drop the request *envelope* answered; the tool is not run again.

A replayed session takes the answer from the journal, so the effect
that produced it happens exactly once — in the run that recorded it.

<PySourceCode >

```python
async def recall(self, envelope: Envelope) -> None:
    """Drop the request *envelope* answered; the tool is not run again.

    A replayed session takes the answer from the journal, so the effect
    that produced it happens exactly once — in the run that recorded it.

    Args:
        envelope: The answer this toolbox sent earlier.
    """
    self._awaiting = _IDLE
```

</PySourceCode>

<div >

<PyParameter name={"envelope"} type={"Envelope"} value={undefined}>

The answer this toolbox sent earlier.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"cancel"} type={"(self, notice) -> None"}>

Drop the request nobody will answer now.

A toolbox holds no resources of its own — a tool that owns a connection
owns it outside the protocol — so the whole of its state is the request
in its slot, and ``Tool`` has no ``cancel`` to call.

<PySourceCode >

```python
async def cancel(self, notice: Cancelled) -> None:
    """Drop the request nobody will answer now.

    A toolbox holds no resources of its own — a tool that owns a connection
    owns it outside the protocol — so the whole of its state is the request
    in its slot, and ``Tool`` has no ``cancel`` to call.

    Args:
        notice: Why the session was rolled up.
    """
    self._awaiting = _IDLE
    post(expr=self._awaiting == _IDLE, message='a cancelled toolbox must owe nothing')
```

</PySourceCode>

<div >

<PyParameter name={"notice"} type={"Cancelled"} value={undefined}>

Why the session was rolled up.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
