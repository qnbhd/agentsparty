# ModelId (/docs/agentsparty/llm/types/ModelId)

Which model produced an answer: a provider and a name inside it.

Rendered as ``provider:name`` — the notation every surveyed framework uses
for the same purpose. agentsparty *parses* that notation; it does not resolve it.
Resolving a name to a class needs a dynamic registry, which this project
forbids: you construct the adapter yourself and pass it its client.

## Attributes

<PyAttribute name={"provider"} type={"str"} value={null} />

<PyAttribute name={"name"} type={"str"} value={null} />

## Functions

<PyFunction name={"parse"} type={"(cls, text) -> ModelId"}>

The model id written as ``provider:name`` in *text*.

Only the first colon separates: ``"openrouter:anthropic/claude"`` and
``"ollama:llama3:70b"`` both parse the way you would read them.

<PySourceCode >

```python
@classmethod
def parse(cls, text: str) -> ModelId:
    """The model id written as ``provider:name`` in *text*.

    Only the first colon separates: ``"openrouter:anthropic/claude"`` and
    ``"ollama:llama3:70b"`` both parse the way you would read them.

    Args:
        text: The ``provider:name`` rendering to read.

    Raises:
        ValueError: if *text* carries no separator.
    """
    provider, separator, name = text.partition(':')
    if not separator:
        raise ValueError(f"a model id must read 'provider:name', got {text!r}")
    return cls(provider, name)
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"text"} type={"str"} value={undefined}>

The ``provider:name`` rendering to read.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.ModelId"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, provider, name) -> None"}>

<div >

<PyParameter name={"provider"} type={"str"} value={null} />
<PyParameter name={"name"} type={"str"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
