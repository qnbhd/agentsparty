# Allowance (/docs/agentsparty/kernel/budget/Allowance)

What one [`run`](/docs/agentsparty/runtime/AgentRuntime) may spend.

``None`` in a field opts explicitly into an unbounded quantity.

Only quantities a session can refuse *before* paying are metered here. A
provider's token count is known after the request has been sent and billed;
a limit checked then is a receipt, not an allowance, so token and money
limits are deliberately absent.

An allowance bounds one run, not a session's lifetime: a resumed run
replays recorded decisions for free, exactly as recursion already does, so
that a long session stays resumable.

## Attributes

<PyAttribute name={"unfoldings"} type={"int | None"} value={"DEFAULT_UNFOLDINGS"} />

<PyAttribute name={"steps"} type={"int | None"} value={"None"} />

## Functions

<PyFunction name={"covers"} type={"(self, spent) -> bool"}>

Whether *spent* is still within this allowance.

<PySourceCode >

```python
def covers(self, spent: Spent) -> bool:
    """Whether *spent* is still within this allowance.

    Args:
        spent: The total spent so far.
    """
    return _within(spent.unfoldings, self.unfoldings) and _within(
        spent.steps,
        self.steps,
    )
```

</PySourceCode>

<div >

<PyParameter name={"spent"} type={"Spent"} value={undefined}>

The total spent so far.

</PyParameter>

</div>

<PyFunctionReturn type={"bool"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, unfoldings=DEFAULT_UNFOLDINGS, steps=None) -> None"}>

<div >

<PyParameter name={"unfoldings"} type={"int | None"} value={"DEFAULT_UNFOLDINGS"} />
<PyParameter name={"steps"} type={"int | None"} value={"None"} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
