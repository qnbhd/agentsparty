# StreamTracer (/docs/agentsparty/tracing/stream/StreamTracer)

One indented line per event. Not thread-safe; span depths are never evicted.

## Functions

<PyFunction name={"__init__"} type={"(self, writer=None, limit=DEFAULT_LIMIT, *, flush=True) -> None"}>

Create a stream sink writing one indented line per event.

<PySourceCode >

```python
def __init__(
    self,
    writer: TextIO | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    flush: bool = True,
) -> None:
    """Create a stream sink writing one indented line per event.

    Args:
        writer: The text stream to write to; ``sys.stderr`` when unset.
        limit: Characters kept per field value, an ellipsis appended beyond.
        flush: Whether to flush the stream after every event.
    """
    require_positive('limit', limit)
    self._writer = writer
    self._limit = limit
    self._flush = flush
    self._depth: dict[SpanId, int] = {}
```

</PySourceCode>

<div >

<PyParameter name={"writer"} type={"TextIO | None"} value={"None"}>

The text stream to write to; ``sys.stderr`` when unset.

</PyParameter>
<PyParameter name={"limit"} type={"int"} value={"DEFAULT_LIMIT"}>

Characters kept per field value, an ellipsis appended beyond.

</PyParameter>
<PyParameter name={"flush"} type={"bool"} value={"True"}>

Whether to flush the stream after every event.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"record"} type={"(self, event) -> None"}>

Write *event* as one indented line to the stream.

<PySourceCode >

```python
def record(self, event: Event) -> None:
    """Write *event* as one indented line to the stream.

    Args:
        event: The event to record.
    """
    # Resolved per call so that a rebound sys.stderr (pytest) is honoured.
    out = sys.stderr if self._writer is None else self._writer
    line = self._format(event)
    out.write(f'{line}\n')
    if self._flush:
        out.flush()
```

</PySourceCode>

<div >

<PyParameter name={"event"} type={"Event"} value={undefined}>

The event to record.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
