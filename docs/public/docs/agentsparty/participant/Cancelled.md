# Cancelled (/docs/agentsparty/participant/Cancelled)

Why a session was rolled up before it reached ``end``.

Carries the failure as it was written down, not the live exception: a
participant cannot inspect an exception (its class is not a value this
project reads), so the only thing it could do with one is print it.
The caller of [`run`](/docs/agentsparty/runtime/AgentRuntime) still receives the
exception itself — a cancellation notifies, it does not swallow.

## Attributes

<PyAttribute name={"reason"} type={"str"} value={null} />

## Functions

<PyFunction name={"of"} type={"(cls, error) -> Cancelled"}>

The notice for a session that ended in *error*.

This is the boundary where an unknown exception becomes a domain value;
everything downstream — participants, signals, sinks — receives a
notice that needs no further inspection.

<PySourceCode >

```python
@classmethod
def of(cls, error: Exception) -> Cancelled:
    """The notice for a session that ended in *error*.

    This is the boundary where an unknown exception becomes a domain value;
    everything downstream — participants, signals, sinks — receives a
    notice that needs no further inspection.

    Args:
        error: The failure that ended the session.

    Returns:
        The notice to broadcast to every participant.
    """
    return cls(fault(error))
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"error"} type={"Exception"} value={undefined}>

The failure that ended the session.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.participant.Cancelled"}>

The notice to broadcast to every participant.

</PyFunctionReturn>

</PyFunction>

<PyFunction name={"__init__"} type={"(self, reason) -> None"}>

<div >

<PyParameter name={"reason"} type={"str"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
