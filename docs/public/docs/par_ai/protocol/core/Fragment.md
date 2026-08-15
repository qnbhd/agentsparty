# Fragment (/docs/agentsparty/protocol/core/Fragment)

A protocol expression with a hole in its tail.

## Functions

<PyFunction name={"fill"} type={"(self, tail) -> P"}>

Close the hole with *tail* and return the completed protocol.

<PySourceCode >

```python
def fill(self, tail: P) -> P:
    """Close the hole with *tail* and return the completed protocol.

    Args:
        tail: The continuation to close the hole with.
    """
    return self._fill(tail)
```

</PySourceCode>

<div >

<PyParameter name={"tail"} type={"P"} value={undefined}>

The continuation to close the hole with.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.core.P"} />

</PyFunction>

<PyFunction name={"close"} type={"(self) -> P"}>

Close the hole with the fragment's own end.

<PySourceCode >

```python
def close(self) -> P:
    """Close the hole with the fragment's own end."""
    return self._fill(self._end)
```

</PySourceCode>

<PyFunctionReturn type={"agentsparty.protocol.language.core.P"} />

</PyFunction>

<PyFunction name={"identity"} type={"(cls, end) -> Fragment[P]"}>

A fragment that passes *tail* through unchanged.

<PySourceCode >

```python
@classmethod
def identity(cls, end: P) -> Fragment[P]:
    """A fragment that passes *tail* through unchanged.

    Args:
        end: The fragment's end value.
    """
    return cls(lambda tail: tail, end)
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"end"} type={"P"} value={undefined}>

The fragment's end value.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.core.Fragment[agentsparty.protocol.language.core.P]"} />

</PyFunction>

<PyFunction name={"halt"} type={"(cls, end) -> Fragment[P]"}>

A fragment that ignores its tail and yields ``end`` (``stop``).

<PySourceCode >

```python
@classmethod
def halt(cls, end: P) -> Fragment[P]:
    """A fragment that ignores its tail and yields ``end`` (``stop``)."""
    return cls(lambda _tail: end, end)
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"end"} type={"P"} value={null} />

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.core.Fragment[agentsparty.protocol.language.core.P]"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, _fill, _end) -> None"}>

<div >

<PyParameter name={"_fill"} type={"Callable[[P], P]"} value={null} />
<PyParameter name={"_end"} type={"P"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
