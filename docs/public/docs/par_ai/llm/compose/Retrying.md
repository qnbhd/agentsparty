# Retrying (/docs/agentsparty/llm/compose/Retrying)

*inner*, asked again while it says another attempt may succeed.

Only `ModelUnavailable` is retried, because that is
what the type means; `ModelRefused` is raised at
once. There is no backoff policy: the wait is exactly what the provider
asked for in ``Retry-After`` and nothing when it asked for nothing. A
guessed backoff is a number nobody measured; this project answers a retry
question with one integer.

## Attributes

<PyAttribute name={"inner"} type={"LanguageModel"} value={null} />

<PyAttribute name={"attempts"} type={"int"} value={"1"} />

<PyAttribute name={"sleep"} type={"Sleep"} value={"asyncio.sleep"} />

## Functions

<PyFunction name={"complete"} type={"(self, request) -> Answer"}>

The first answer *inner* gives, asking again while that may help.

<PySourceCode >

```python
async def complete(self, request: StructuredRequest) -> Answer:
    """The first answer *inner* gives, asking again while that may help.

    Args:
        request: The structured-output turn to answer.
    """
    return await self._ask(request, self.attempts)
```

</PySourceCode>

<div >

<PyParameter name={"request"} type={"StructuredRequest"} value={undefined}>

The structured-output turn to answer.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.Answer"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, inner, attempts=1, sleep=asyncio.sleep) -> None"}>

<div >

<PyParameter name={"inner"} type={"LanguageModel"} value={null} />
<PyParameter name={"attempts"} type={"int"} value={"1"} />
<PyParameter name={"sleep"} type={"Sleep"} value={"asyncio.sleep"} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
