# Fanout (/docs/agentsparty/tracing/types/Fanout)

Tracer that forwards every event to each of `tracers`, in order.

## Attributes

<PyAttribute name={"tracers"} type={"tuple[Tracer, ...]"} value={null} />

## Functions

<PyFunction name={"record"} type={"(self, event) -> None"}>

Forward *event* to every wrapped tracer.

<PySourceCode >

```python
def record(self, event: Event) -> None:
    """Forward *event* to every wrapped tracer.

    Args:
        event: The event to forward.
    """
    for tracer in self.tracers:
        tracer.record(event)
```

</PySourceCode>

<div >

<PyParameter name={"event"} type={"Event"} value={undefined}>

The event to forward.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, tracers) -> None"}>

<div >

<PyParameter name={"tracers"} type={"tuple[Tracer, ...]"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
