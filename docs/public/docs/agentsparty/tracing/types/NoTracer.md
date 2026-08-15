# NoTracer (/docs/agentsparty/tracing/types/NoTracer)

Tracer that discards every event; the runtime default.

## Functions

<PyFunction name={"record"} type={"(self, event) -> None"}>

Discard *event*.

<PySourceCode >

```python
def record(self, event: Event) -> None:
    """Discard *event*.

    Args:
        event: The event to discard.
    """
```

</PySourceCode>

<div >

<PyParameter name={"event"} type={"Event"} value={undefined}>

The event to discard.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
