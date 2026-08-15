# Answer (/docs/agentsparty/llm/types/Answer)

One completion: the text, who produced it, and what it cost.

``usage`` defaults to `NO_USAGE` because a provider that reports no
token counts is a real case, and the empty bill is the honest way to say
so: adding it to a total changes nothing.

## Attributes

<PyAttribute name={"text"} type={"str"} value={null} />

<PyAttribute name={"model"} type={"ModelId"} value={null} />

<PyAttribute name={"usage"} type={"Usage"} value={"NO_USAGE"} />

## Functions

<PyFunction name={"__init__"} type={"(self, text, model, usage=NO_USAGE) -> None"}>

<div >

<PyParameter name={"text"} type={"str"} value={null} />
<PyParameter name={"model"} type={"ModelId"} value={null} />
<PyParameter name={"usage"} type={"Usage"} value={"NO_USAGE"} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
