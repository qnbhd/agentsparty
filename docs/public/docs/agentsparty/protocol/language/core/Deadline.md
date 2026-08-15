# Deadline (/docs/agentsparty/protocol/language/core/Deadline)

A strictly positive wall-clock window for one alt.

## Attributes

<PyAttribute name={"duration"} type={"timedelta"} value={null} />

## Functions

<PyFunction name={"total_seconds"} type={"(self) -> float"}>

Return the window in seconds for the scheduler.

<PySourceCode >

```python
def total_seconds(self) -> float:
    """Return the window in seconds for the scheduler."""
    return self.duration.total_seconds()
```

</PySourceCode>

<PyFunctionReturn type={"float"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, duration) -> None"}>

<div >

<PyParameter name={"duration"} type={"timedelta"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
