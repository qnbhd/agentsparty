# BranchBody (/docs/agentsparty/choreography/chor/BranchBody)

Context manager for one arm of a `Parallel` split.

## Functions

<PyFunction name={"__init__"} type={"(self, parallel) -> None"}>

Prepare a recorder owned by a parallel split.

<PySourceCode >

```python
def __init__(self, parallel: Parallel) -> None:
    """Prepare a recorder owned by a parallel split."""
    self._parallel = parallel
    self._scope = _Scope()
```

</PySourceCode>

<div >

<PyParameter name={"parallel"} type={"Parallel"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
