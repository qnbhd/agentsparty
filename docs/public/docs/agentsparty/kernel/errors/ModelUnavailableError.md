# ModelUnavailableError (/docs/agentsparty/kernel/errors/ModelUnavailableError)

Raised when a model would not answer but another attempt may succeed.

Rate limits, timeouts, dropped connections and server faults. The provider
sometimes says how long to wait; `retry_after` carries that answer,
and ``0`` means it said nothing.

## Functions

<PyFunction name={"__init__"} type={"(self, message, retry_after=0) -> None"}>

Record *message* and how long the provider asked for.

<PySourceCode >

```python
def __init__(self, message: str, retry_after: float = 0) -> None:
    """Record *message* and how long the provider asked for.

    Args:
        message: What went wrong.
        retry_after: Seconds the provider asked the caller to wait.
    """
    super().__init__(message)
    self.retry_after = retry_after
```

</PySourceCode>

<div >

<PyParameter name={"message"} type={"str"} value={undefined}>

What went wrong.

</PyParameter>
<PyParameter name={"retry_after"} type={"float"} value={"0"}>

Seconds the provider asked the caller to wait.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
