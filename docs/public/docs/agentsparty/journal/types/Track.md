# Track (/docs/agentsparty/journal/types/Track)

Which independent branch of a protocol a decision belongs to.

The empty path is the session's root track; entering branch *index* of a
`Parallel` appends *index*. Parallel
branches own disjoint roles, so every role — and therefore every
participant — belongs to exactly one track, and a track's own decisions
are totally ordered whatever the scheduler does.

## Attributes

<PyAttribute name={"path"} type={"tuple[int, ...]"} value={null} />

## Functions

<PyFunction name={"branch"} type={"(self, index) -> Track"}>

The track of parallel branch *index* inside this one.

<PySourceCode >

```python
def branch(self, index: int) -> Track:
    """The track of parallel branch *index* inside this one.

    Args:
        index: Position of the branch in its parallel node.
    """
    pre(expr=index >= 0, message='a branch index counts from zero')
    return Track((*self.path, index))
```

</PySourceCode>

<div >

<PyParameter name={"index"} type={"int"} value={undefined}>

Position of the branch in its parallel node.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.journal.types.Track"} />

</PyFunction>

<PyFunction name={"under"} type={"(self, other) -> bool"}>

Whether this track is *other* or a branch nested inside it.

<PySourceCode >

```python
def under(self, other: Track) -> bool:
    """Whether this track is *other* or a branch nested inside it.

    Args:
        other: The candidate ancestor.
    """
    return self.path[: len(other.path)] == other.path
```

</PySourceCode>

<div >

<PyParameter name={"other"} type={"Track"} value={undefined}>

The candidate ancestor.

</PyParameter>

</div>

<PyFunctionReturn type={"bool"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, path) -> None"}>

<div >

<PyParameter name={"path"} type={"tuple[int, ...]"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
