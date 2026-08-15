# NonEmptyMap (/docs/agentsparty/nonempty/NonEmptyMap)

Immutable non-empty mapping by composition.

Construction only via ``of_pairs`` / ``of_mapping`` / ``check_pairs``.
Explicit ``__eq__`` / ``__hash__`` so structural protocol equality stays sound.

## Functions

<PyFunction name={"__init__"} type={"(self, data) -> None"}>

Wrap a non-empty *data* mapping; rejects an empty one.

<PySourceCode >

```python
def __init__(self, data: dict[K, V], /) -> None:
    """Wrap a non-empty *data* mapping; rejects an empty one."""
    if not data:
        raise EmptyError('NonEmptyMap cannot be empty')
    self._data = data
```

</PySourceCode>

<div >

<PyParameter name={"data"} type={"dict[K, V]"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"of_pairs"} type={"(cls, pairs) -> Self"}>

Build from an iterable of pairs; rejects empty or duplicate keys.

<PySourceCode >

```python
@classmethod
def of_pairs(cls, pairs: Iterable[tuple[K, V]], /) -> Self:
    """Build from an iterable of pairs; rejects empty or duplicate keys."""
    buffer: dict[K, V] = {}
    for key, value in pairs:
        if key in buffer:
            raise ValueError(f'duplicate key {key!r}')
        buffer[key] = value
    if not buffer:
        raise EmptyError('cannot build a NonEmptyMap from an empty iterable')
    return cls(buffer)
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"pairs"} type={"Iterable[tuple[K, V]]"} value={null} />

</div>

<PyFunctionReturn type={"typing_extensions.Self"} />

</PyFunction>

<PyFunction name={"of_mapping"} type={"(cls, mapping) -> Self"}>

Build from a mapping; rejects an empty one.

<PySourceCode >

```python
@classmethod
def of_mapping(cls, mapping: Mapping[K, V], /) -> Self:
    """Build from a mapping; rejects an empty one."""
    if not mapping:
        raise EmptyError('cannot build a NonEmptyMap from an empty mapping')
    return cls(dict(mapping))
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"mapping"} type={"Mapping[K, V]"} value={null} />

</div>

<PyFunctionReturn type={"typing_extensions.Self"} />

</PyFunction>

<PyFunction name={"check_pairs"} type={"(cls, pairs) -> Self | None"}>

Build from pairs, or return ``None`` when *pairs* is empty.

<PySourceCode >

```python
@classmethod
def check_pairs(cls, pairs: Iterable[tuple[K, V]], /) -> Self | None:
    """Build from pairs, or return ``None`` when *pairs* is empty."""
    buffer: dict[K, V] = {}
    for key, value in pairs:
        if key in buffer:
            raise ValueError(f'duplicate key {key!r}')
        buffer[key] = value
    if buffer:
        return cls(buffer)
    return None
```

</PySourceCode>

<div >

<PyParameter name={"cls"} type={null} value={null} />
<PyParameter name={"pairs"} type={"Iterable[tuple[K, V]]"} value={null} />

</div>

<PyFunctionReturn type={"typing_extensions.Self | None"} />

</PyFunction>
