# Profiled (/docs/agentsparty/llm/profile/Profiled)

*inner*, asked only for what *profile* says it serves.

Pair a profile with a model where the two meet, not inside the adapter:
the same adapter class serves models with different capabilities, and a
fallback chain routinely mixes them.

## Attributes

<PyAttribute name={"inner"} type={"LanguageModel"} value={null} />

<PyAttribute name={"profile"} type={"Profile"} value={null} />

## Functions

<PyFunction name={"complete"} type={"(self, request) -> Answer"}>

*inner*'s answer to the adapted *request*.

<PySourceCode >

```python
async def complete(self, request: StructuredRequest) -> Answer:
    """*inner*'s answer to the adapted *request*.

    Args:
        request: The structured-output turn to answer.
    """
    return await self.inner.complete(self.profile.adapt(request))
```

</PySourceCode>

<div >

<PyParameter name={"request"} type={"StructuredRequest"} value={undefined}>

The structured-output turn to answer.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.Answer"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, inner, profile) -> None"}>

<div >

<PyParameter name={"inner"} type={"LanguageModel"} value={null} />
<PyParameter name={"profile"} type={"Profile"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
