# Codec (/docs/agentsparty/protocol/core/Codec)

Everything the protocol knows about a branch payload — as data.

``decode`` must be pure: journalled sessions replay a payload by decoding
the raw form again, and that has to yield the same value.

## Attributes

<PyAttribute name={"name"} type={"str"} value={null} />

<PyAttribute name={"schema"} type={"Mapping[str, object]"} value={null} />

<PyAttribute name={"decode"} type={"Callable[[RawValue], T_co]"} value={null} />

<PyAttribute name={"carries_value"} type={"bool"} value={"True"} />

## Functions

<PyFunction name={"__init__"} type={"(self, name, schema, decode, carries_value=True) -> None"}>

<div >

<PyParameter name={"name"} type={"str"} value={null} />
<PyParameter name={"schema"} type={"Mapping[str, object]"} value={null} />
<PyParameter name={"decode"} type={"Callable[[RawValue], T_co]"} value={null} />
<PyParameter name={"carries_value"} type={"bool"} value={"True"} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
