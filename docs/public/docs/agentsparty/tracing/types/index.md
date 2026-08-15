# types (/docs/agentsparty/tracing/types/index)

The tracing contract: what a recorded event is and where it goes.

<PyAttribute name={"NULL_TRACER"} type={"Tracer"} value={"NoTracer()"}>

The tracer used when observability is not switched on.

</PyAttribute>

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"SpanId"} href={"/docs/agentsparty/tracing/types/SpanId"} />
<Card title={"Span"} href={"/docs/agentsparty/tracing/types/Span"} />
<Card title={"Event"} href={"/docs/agentsparty/tracing/types/Event"} />
<Card title={"Tracer"} href={"/docs/agentsparty/tracing/types/Tracer"} />
<Card title={"NoTracer"} href={"/docs/agentsparty/tracing/types/NoTracer"} />
<Card title={"Fanout"} href={"/docs/agentsparty/tracing/types/Fanout"} />
<Card title={"Mapped"} href={"/docs/agentsparty/tracing/types/Mapped"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"fanout"} type={"(*tracers) -> Tracer"}>

Combine *tracers* into one that forwards to all of them, in order.

<PySourceCode >

```python
def fanout(*tracers: Tracer) -> Tracer:
    """Combine *tracers* into one that forwards to all of them, in order.

    Args:
        *tracers: The sinks to feed; none means "discard everything".
    """
    return Fanout(tracers)
```

</PySourceCode>

<div >

<PyParameter name={"tracers"} type={"Tracer"} value={"()"} />

</div>

<PyFunctionReturn type={"agentsparty.tracing.types.Tracer"} />

</PyFunction>
<PyFunction name={"mapped"} type={"(transform, inner) -> Tracer"}>

Filter (return ``None``) or redact (return a new event) before *inner*.

<PySourceCode >

```python
def mapped(transform: Callable[[Event], Event | None], inner: Tracer) -> Tracer:
    """Filter (return ``None``) or redact (return a new event) before *inner*.

    Args:
        transform: Applied to every event; ``None`` drops it.
        inner: The sink that receives the surviving events.
    """
    return Mapped(transform, inner)
```

</PySourceCode>

<div >

<PyParameter name={"transform"} type={"Callable[[Event], Event | None]"} value={undefined}>

Applied to every event; ``None`` drops it.

</PyParameter>
<PyParameter name={"inner"} type={"Tracer"} value={undefined}>

The sink that receives the surviving events.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.tracing.types.Tracer"} />

</PyFunction>

</Tab>

</Tabs>
