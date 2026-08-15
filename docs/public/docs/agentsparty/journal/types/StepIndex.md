# StepIndex (/docs/agentsparty/journal/types/StepIndex)

Where a decision sits: which track, and which position within it.

Ordering is the *canonical* order — track-major, then position. It is a
linear extension of the causal order, not the causal order itself: two
steps on different tracks compare, but neither happened before the other.

## Attributes

<PyAttribute name={"track"} type={"Track"} value={null} />

<PyAttribute name={"position"} type={"int"} value={null} />

## Functions

<PyFunction name={"next"} type={"(self) -> StepIndex"}>

The position of the next message on the same track.

<PySourceCode >

```python
def next(self) -> StepIndex:
    """The position of the next message on the same track."""
    return StepIndex(self.track, self.position + 1)
```

</PySourceCode>

<PyFunctionReturn type={"agentsparty.journal.types.StepIndex"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, track, position) -> None"}>

<div >

<PyParameter name={"track"} type={"Track"} value={null} />
<PyParameter name={"position"} type={"int"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
