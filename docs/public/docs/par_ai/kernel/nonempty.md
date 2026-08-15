# nonempty (/docs/agentsparty/kernel/nonempty/index)

Non-empty containers: ``NonEmptyTuple`` (static) and ``NonEmptyMap`` (composition).

Direction rule: a non-empty container appears where the library is the
producer — in ADT fields the user reads, and in parameters the runtime
passes to the user's implementation (protocol parameters are
contravariant, so implementations declaring a wider ``Mapping`` keep
satisfying a protocol declaring ``NonEmptyMap``). It never appears in a
parameter the user fills: user-facing construction stays on the widest
reasonable built-in.

<PyAttribute name={"NonEmptyTuple"} type={"TypeAlias"} value={"'tuple[T, *tuple[T, ...]]'"} />

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"EmptyError"} href={"/docs/agentsparty/kernel/nonempty/EmptyError"} />
<Card title={"NonEmptyMap"} href={"/docs/agentsparty/kernel/nonempty/NonEmptyMap"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"ne_tuple"} type={"(head, *tail) -> NonEmptyTuple[T]"}>

Build a ``NonEmptyTuple``. Calling it with no arguments is a static error.

<PySourceCode >

```python
def ne_tuple(head: T, /, *tail: T) -> NonEmptyTuple[T]:
    """Build a ``NonEmptyTuple``. Calling it with no arguments is a static error."""
    return (head, *tail)
```

</PySourceCode>

<div >

<PyParameter name={"head"} type={"T"} value={null} />
<PyParameter name={"tail"} type={"T"} value={"()"} />

</div>

<PyFunctionReturn type={"agentsparty.kernel.nonempty.NonEmptyTuple[agentsparty.kernel.nonempty.T]"} />

</PyFunction>
<PyFunction name={"is_nonempty_tuple"} type={"(value) -> TypeGuard[NonEmptyTuple[T]]"}>

Narrow ``tuple[T, ...]`` to ``NonEmptyTuple[T]``.

<PySourceCode >

```python
def is_nonempty_tuple(value: tuple[T, ...], /) -> TypeGuard[NonEmptyTuple[T]]:
    """Narrow ``tuple[T, ...]`` to ``NonEmptyTuple[T]``."""
    return len(value) > 0
```

</PySourceCode>

<div >

<PyParameter name={"value"} type={"tuple[T, ...]"} value={null} />

</div>

<PyFunctionReturn type={"typing.TypeGuard[agentsparty.kernel.nonempty.NonEmptyTuple[agentsparty.kernel.nonempty.T]]"} />

</PyFunction>

</Tab>

</Tabs>
