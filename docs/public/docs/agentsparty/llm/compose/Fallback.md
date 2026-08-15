# Fallback (/docs/agentsparty/llm/compose/Fallback)

*primary*, falling back to *secondary* when it will not answer.

Both kinds of failure fall through: a model that refuses this request is a
reason to ask a different model, even though it is not a reason to ask the
same one again.

When both fail, *secondary*'s failure is raised **from** *primary*'s, so
the whole chain is on the traceback in the order it was tried. agentsparty does
not raise an exception group: the surveyed framework that does documents
that every ``except ModelAPIError`` in user code silently stops matching.

## Attributes

<PyAttribute name={"primary"} type={"LanguageModel"} value={null} />

<PyAttribute name={"secondary"} type={"LanguageModel"} value={null} />

## Functions

<PyFunction name={"complete"} type={"(self, request) -> Answer"}>

The first answer *primary* or *secondary* gives.

<PySourceCode >

```python
async def complete(self, request: StructuredRequest) -> Answer:
    """The first answer *primary* or *secondary* gives.

    Args:
        request: The structured-output turn to answer.

    Raises:
        ModelError: *secondary*'s failure, caused by *primary*'s, if
            neither answers.
    """
    match await _attempt(self.primary, request):
        case _Answered(answer=answer):
            return answer
        case _Failed(error=error):
            return await _after(self.secondary, request, error)
```

</PySourceCode>

<div >

<PyParameter name={"request"} type={"StructuredRequest"} value={undefined}>

The structured-output turn to answer.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.Answer"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, primary, secondary) -> None"}>

<div >

<PyParameter name={"primary"} type={"LanguageModel"} value={null} />
<PyParameter name={"secondary"} type={"LanguageModel"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
