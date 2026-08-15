# Participant (/docs/agentsparty/participant/Participant)

Executor bound to a protocol role: Agent or Human.

## Attributes

<PyAttribute name={"role"} type={"Role"} value={null}>

The role this participant plays.

</PyAttribute>

<PyAttribute name={"endpoint_contract"} type={"EndpointType"} value={null}>

The endpoint protocol derived for this participant's role.

</PyAttribute>

## Functions

<PyFunction name={"select"} type={"(self, receiver, branches) -> Chosen[B]"}>

Pick one of *branches* and return the decoded alt for *receiver*.

<PySourceCode >

```python
async def select(
    self,
    receiver: Role,
    branches: NonEmptyMap[Label, B],
) -> Chosen[B]:
    """Pick one of *branches* and return the decoded alt for *receiver*.

    Args:
        receiver: The role that will receive the chosen message.
        branches: The labelled alts offered to this participant; never
            empty — a protocol interaction always declares at least one
            branch, so the guarantee lives in the type.

    Returns:
        The chosen branch together with its decoded payload.
    """
    ...
```

</PySourceCode>

<div >

<PyParameter name={"receiver"} type={"Role"} value={undefined}>

The role that will receive the chosen message.

</PyParameter>
<PyParameter name={"branches"} type={"NonEmptyMap[Label, B]"} value={undefined}>

The labelled alts offered to this participant; never
empty — a protocol interaction always declares at least one
branch, so the guarantee lives in the type.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.core.Chosen"}>

The chosen branch together with its decoded payload.

</PyFunctionReturn>

</PyFunction>

<PyFunction name={"offer"} type={"(self, envelope) -> None"}>

Deliver *envelope* to this participant.

<PySourceCode >

```python
async def offer(self, envelope: Envelope) -> None:
    """Deliver *envelope* to this participant.

    Args:
        envelope: The protocol message being delivered.
    """
    ...
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

Restore *envelope* as a message this participant sent earlier.

The dual of `offer`, called when a session resumes from a
journal: the alt was authored by an earlier process and must not be
authored again. Implementations restore what the participant knows, in
the form the runtime informs it of — not the original wording.

<PySourceCode >

```python
async def recall(self, envelope: Envelope) -> None:
    """Restore *envelope* as a message this participant sent earlier.

    The dual of :meth:`offer`, called when a session resumes from a
    journal: the alt was authored by an earlier process and must not be
    authored again. Implementations restore what the participant knows, in
    the form the runtime informs it of — not the original wording.

    Args:
        envelope: The protocol message this participant sent earlier.
    """
    ...
```

</PySourceCode>

<div >

<PyParameter name={"envelope"} type={"Envelope"} value={undefined}>

The protocol message this participant sent earlier.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"cancel"} type={"(self, notice) -> None"}>

Take note that the session is over and will not go on here.

Called once on every bound participant when a session ends anywhere
other than ``end``. Nothing will be asked of this participant again in
this session, so this is where it releases what it holds and returns to
the state it was constructed in — which makes cancelling twice the same
as cancelling once, and a cancelled participant reusable.

It must not raise. The failure that rolled the session up is the one
the caller has to see; a participant that raises here is recorded as
failed and the broadcast goes on without it.

<PySourceCode >

```python
async def cancel(self, notice: Cancelled) -> None:
    """Take note that the session is over and will not go on here.

    Called once on every bound participant when a session ends anywhere
    other than ``end``. Nothing will be asked of this participant again in
    this session, so this is where it releases what it holds and returns to
    the state it was constructed in — which makes cancelling twice the same
    as cancelling once, and a cancelled participant reusable.

    It must not raise. The failure that rolled the session up is the one
    the caller has to see; a participant that raises here is recorded as
    failed and the broadcast goes on without it.

    Args:
        notice: Why the session was rolled up.
    """
    ...
```

</PySourceCode>

<div >

<PyParameter name={"notice"} type={"Cancelled"} value={undefined}>

Why the session was rolled up.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
