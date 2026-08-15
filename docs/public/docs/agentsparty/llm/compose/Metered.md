# Metered (/docs/agentsparty/llm/compose/Metered)

*inner*, refusing to begin a call once *tokens* have been billed.

The one transformer here that is not a pure function of the model it
wraps, and necessarily so: a meter that forgot would not be a meter. Its
state is the receipts, and sharing one instance between several agents is
how several agents share one budget.

It bounds a process, not a session: a resumed run replays recorded
decisions without calling a model at all, so a fresh meter is correct —
the same rule [`Allowance`](/docs/agentsparty/kernel/budget/Allowance) already follows.

## Attributes

<PyAttribute name={"billed"} type={"Usage"} value={null}>

What has been billed through this meter so far.

</PyAttribute>

## Functions

<PyFunction name={"__init__"} type={"(self, inner, tokens) -> None"}>

Meter *inner* at *tokens* billed tokens.

<PySourceCode >

```python
def __init__(self, inner: LanguageModel, tokens: int) -> None:
    """Meter *inner* at *tokens* billed tokens.

    Args:
        inner: The model to meter.
        tokens: Total input plus output tokens after which no further call
            is begun.

    Raises:
        ValueError: if *tokens* is negative.
    """
    require_nonnegative('a token meter', tokens)
    self._inner = inner
    self._tokens = tokens
    self._billed = NO_USAGE
```

</PySourceCode>

<div >

<PyParameter name={"inner"} type={"LanguageModel"} value={undefined}>

The model to meter.

</PyParameter>
<PyParameter name={"tokens"} type={"int"} value={undefined}>

Total input plus output tokens after which no further call
is begun.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"complete"} type={"(self, request) -> Answer"}>

*inner*'s answer, if the meter still has room to begin the call.

<PySourceCode >

```python
async def complete(self, request: StructuredRequest) -> Answer:
    """*inner*'s answer, if the meter still has room to begin the call.

    Args:
        request: The structured-output turn to answer.

    Raises:
        TokenLimitError: if the meter is already spent.
    """
    if self._billed.total_tokens >= self._tokens:
        total_tokens = self._billed.total_tokens
        raise TokenLimitError(
            f'{total_tokens} tokens already billed through a meter of {self._tokens}',
        )
    answer = await self._inner.complete(request)
    self._billed += answer.usage
    return answer
```

</PySourceCode>

<div >

<PyParameter name={"request"} type={"StructuredRequest"} value={undefined}>

The structured-output turn to answer.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.Answer"} />

</PyFunction>
