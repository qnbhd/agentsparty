# Watch (/docs/agentsparty/tracing/queue/Watch)

A session being watched: events while it runs, and what it returned.

Two ways to read one run, and they do not compete:

- ``async for event in watch`` — every recorded event as it arrives;
- ``await watch`` — what the session returned.

Awaiting before iterating is **not** an error. ``QueueTracer`` is
unbounded and ``Tracer.record`` never blocks, so a session never waits for
its audience: awaiting first means you watch a recording instead of a
broadcast, and no event is lost. This is why agentsparty has no "result read too
early" failure and no ``is_completed`` flag.

One consumer per watch. Two iterators over the same watch would split the
events between them, because a queue hands each event to exactly one
taker; to feed two consumers, ``fanout`` two ``QueueTracer``s.

Construct one with `watching`, which also stops it. Constructing a
``Watch`` directly starts the session with nobody responsible for
cancelling it.

## Functions

<PyFunction name={"__init__"} type={"(self, session, tracer) -> None"}>

Run *session* as a task and read what it records into *tracer*.

<PySourceCode >

```python
def __init__(self, session: Awaitable[R], tracer: QueueTracer) -> None:
    """Run *session* as a task and read what it records into *tracer*.

    Args:
        session: The awaitable to watch — usually ``runtime.run()``.
        tracer: The sink *session* was built with.
    """
    self._task = asyncio.ensure_future(session)
    self._tracer = tracer
```

</PySourceCode>

<div >

<PyParameter name={"session"} type={"Awaitable[R]"} value={undefined}>

The awaitable to watch — usually ``runtime.run()``.

</PyParameter>
<PyParameter name={"tracer"} type={"QueueTracer"} value={undefined}>

The sink *session* was built with.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"select"} type={"(self, facet) -> AsyncIterator[Event]"}>

Only the events *facet* watches, in the order they were recorded.

This one method is the industry's five channel projections plus
``interleave([...])``: the latter is ``select(a | b)``. Because a
facet is a set, ``select(~MODEL)`` — "everything but the model
chatter" — is expressible too, which no surveyed framework offers.

<PySourceCode >

```python
def select(self, facet: Facet) -> AsyncIterator[Event]:
    """Only the events *facet* watches, in the order they were recorded.

    This one method is the industry's five channel projections plus
    ``interleave([...])``: the latter is ``select(a | b)``. Because a
    facet is a set, ``select(~MODEL)`` — "everything but the model
    chatter" — is expressible too, which no surveyed framework offers.

    Args:
        facet: The side of the session to watch.
    """
    return (event async for event in self if event.signal in facet)
```

</PySourceCode>

<div >

<PyParameter name={"facet"} type={"Facet"} value={undefined}>

The side of the session to watch.

</PyParameter>

</div>

<PyFunctionReturn type={"collections.abc.AsyncIterator[agentsparty.tracing.types.Event]"} />

</PyFunction>
