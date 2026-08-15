# MemoryTracer (/docs/agentsparty/tracing/memory/MemoryTracer)

Tracer that keeps every event in memory, in recording order.

## Attributes

<PyAttribute name={"events"} type={"list[Event]"} value={"[]"} />

## Functions

<PyFunction name={"__init__"} type={"(self) -> None"}>

Start with an empty log.

<PySourceCode >

```python
def __init__(self) -> None:
    """Start with an empty log."""
    self.events: list[Event] = []
```

</PySourceCode>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"record"} type={"(self, event) -> None"}>

Append *event* to `events`.

<PySourceCode >

```python
def record(self, event: Event) -> None:
    """Append *event* to :attr:`events`.

    Args:
        event: The event to keep.
    """
    self.events.append(event)
```

</PySourceCode>

<div >

<PyParameter name={"event"} type={"Event"} value={undefined}>

The event to keep.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"names"} type={"(self) -> list[str]"}>

The signal name of every recorded event, in order.

<PySourceCode >

```python
def names(self) -> list[str]:
    """The signal name of every recorded event, in order."""
    return [describe(event.signal).name for event in self.events]
```

</PySourceCode>

<PyFunctionReturn type={"list[str]"} />

</PyFunction>
