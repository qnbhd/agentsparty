# Chosen (/docs/agentsparty/protocol/core/Chosen)

Selected branch, its decoded payload, and the raw form behind it.

Invariant: ``branch.payload.decode(raw) == payload``. The raw form is what
the participant authored — model JSON, a typed line, a scripted value — and
it is what a journal records, so a later process can decode the same
payload from the codec the protocol declares.

## Attributes

<PyAttribute name={"branch"} type={"B"} value={null} />

<PyAttribute name={"payload"} type={"object"} value={null} />

<PyAttribute name={"raw"} type={"RawValue"} value={null} />

## Functions

<PyFunction name={"__init__"} type={"(self, branch, payload, raw) -> None"}>

<div >

<PyParameter name={"branch"} type={"B"} value={null} />
<PyParameter name={"payload"} type={"object"} value={null} />
<PyParameter name={"raw"} type={"RawValue"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
