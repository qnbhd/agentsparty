# ModelStreamed (/docs/agentsparty/tracing/signals/ModelStreamed)

A fragment of the model's answer arrived; a point event in a model span.

Emitted by an adapter that reads a provider's stream. It is an
observation and nothing else: the protocol still sees one answer, decoded
once, because half a JSON payload decodes to nothing.

## Attributes

<PyAttribute name={"delta"} type={"str"} value={null} />

## Functions

<PyFunction name={"__init__"} type={"(self, delta) -> None"}>

<div >

<PyParameter name={"delta"} type={"str"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
