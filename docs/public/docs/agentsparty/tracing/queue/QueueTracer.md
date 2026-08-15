# QueueTracer (/docs/agentsparty/tracing/queue/QueueTracer)

Tracer that publishes events to an unbounded queue for a consumer.

The counterpart of the industry's ``agent.iter()`` and ``streamevents``.
It observes only. agentsparty offers no hook that edits a step before it runs,
because the protocol routes the session: a consumer that could rewrite a
node would be routing it, and the whole point of a choreography is that it
was decided before anyone was asked.

## Functions

<PyFunction name={"__init__"} type={"(self) -> None"}>

Create a sink with an empty queue.

<PySourceCode >

```python
def __init__(self) -> None:
    """Create a sink with an empty queue."""
    self._queue: asyncio.Queue[Event] = asyncio.Queue()
```

</PySourceCode>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"record"} type={"(self, event) -> None"}>

Publish *event*.

The queue is unbounded, so this never blocks and never raises, as the
``Tracer`` contract requires.

<PySourceCode >

```python
def record(self, event: Event) -> None:
    """Publish *event*.

    The queue is unbounded, so this never blocks and never raises, as the
    ``Tracer`` contract requires.

    Args:
        event: The event to publish.
    """
    self._queue.put_nowait(event)
```

</PySourceCode>

<div >

<PyParameter name={"event"} type={"Event"} value={undefined}>

The event to publish.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"take"} type={"(self) -> Event"}>

The next published event, waiting for one if the queue is empty.

<PySourceCode >

```python
async def take(self) -> Event:
    """The next published event, waiting for one if the queue is empty."""
    return await self._queue.get()
```

</PySourceCode>

<PyFunctionReturn type={"agentsparty.tracing.types.Event"} />

</PyFunction>

<PyFunction name={"pending"} type={"(self) -> int"}>

How many published events have not been taken yet.

<PySourceCode >

```python
def pending(self) -> int:
    """How many published events have not been taken yet."""
    return self._queue.qsize()
```

</PySourceCode>

<PyFunctionReturn type={"int"} />

</PyFunction>
