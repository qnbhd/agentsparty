# BranchCodec (/docs/agentsparty/protocol/language/core/BranchCodec)

A labelled branch that carries a payload codec and an intent.

## Attributes

<PyAttribute name={"payload"} type={"Codec[Any]"} value={null}>

The codec for this branch's payload.

</PyAttribute>

<PyAttribute name={"intent"} type={"str"} value={null}>

What the sender is asked to produce on this branch; ``""`` if unsaid.

</PyAttribute>
