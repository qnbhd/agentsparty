# signals (/docs/agentsparty/tracing/signals/index)

Domain signals: the closed catalogue of things a session can observe.

<PyAttribute name={"Signal"} type={"TypeAlias"} value={"_SessionSignal | _StepSignal | _ModelSignal | _ToolSignal"}>

Closed union of every domain signal the runtime can emit.

</PyAttribute>

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"SessionStarted"} href={"/docs/agentsparty/tracing/signals/SessionStarted"} />
<Card title={"SessionFinished"} href={"/docs/agentsparty/tracing/signals/SessionFinished"} />
<Card title={"SessionCancelled"} href={"/docs/agentsparty/tracing/signals/SessionCancelled"} />
<Card title={"StepStarted"} href={"/docs/agentsparty/tracing/signals/StepStarted"} />
<Card title={"Selected"} href={"/docs/agentsparty/tracing/signals/Selected"} />
<Card title={"Recalled"} href={"/docs/agentsparty/tracing/signals/Recalled"} />
<Card title={"Delivered"} href={"/docs/agentsparty/tracing/signals/Delivered"} />
<Card title={"Unfolded"} href={"/docs/agentsparty/tracing/signals/Unfolded"} />
<Card title={"Forked"} href={"/docs/agentsparty/tracing/signals/Forked"} />
<Card title={"ModelCalled"} href={"/docs/agentsparty/tracing/signals/ModelCalled"} />
<Card title={"ModelAnswered"} href={"/docs/agentsparty/tracing/signals/ModelAnswered"} />
<Card title={"ModelStreamed"} href={"/docs/agentsparty/tracing/signals/ModelStreamed"} />
<Card title={"ToolCalled"} href={"/docs/agentsparty/tracing/signals/ToolCalled"} />
<Card title={"ToolAnswered"} href={"/docs/agentsparty/tracing/signals/ToolAnswered"} />
<Card title={"ModelCorrected"} href={"/docs/agentsparty/tracing/signals/ModelCorrected"} />
<Card title={"Failed"} href={"/docs/agentsparty/tracing/signals/Failed"} />
<Card title={"Description"} href={"/docs/agentsparty/tracing/signals/Description"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"describe"} type={"(signal) -> Description"}>

Render *signal* as a stable name plus flat, printable fields.

<PySourceCode >

```python
def describe(signal: Signal) -> Description:
    """Render *signal* as a stable name plus flat, printable fields.

    Args:
        signal: The signal to describe.

    Returns:
        The signal's stable name and its fields, in declaration order.
    """
    match signal:
        case SessionStarted() | SessionFinished() | SessionCancelled() | Unfolded() | Forked():
            return _describe_session(signal)
        case StepStarted() | Selected() | Recalled() | Delivered():
            return _describe_step(signal)
        case ModelCalled() | ModelAnswered() | ModelStreamed() | ModelCorrected():
            return _describe_model(signal)
        case ToolCalled() | ToolAnswered() | Failed():
            return _describe_tool(signal)
        case _:  # pragma: no cover
            assert_never(signal)
```

</PySourceCode>

<div >

<PyParameter name={"signal"} type={"Signal"} value={undefined}>

The signal to describe.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.tracing.signals.Description"}>

The signal's stable name and its fields, in declaration order.

</PyFunctionReturn>

</PyFunction>

</Tab>

</Tabs>
