# Boundary (/docs/agentsparty/protocol/session/Boundary)

The roles a component owns; everything else it mentions is external.

Create with `owning` and then call `defining` with a
protocol fragment built from `msg` and `alt`::

    Search = owning(Retriever, Ranker)

    search = Search.defining(
        msg[Planner, Retriever]('Query', Text)
        >> msg[Retriever, Ranker]('Candidates', list_of(Text))
        >> msg[Ranker, Retriever]('Ranked', list_of(Text))
        >> msg[Retriever, Writer]('Passages', list_of(Text))
    )

``defining`` derives every prefix tag from *owns* and raises
`ValueError` when a role in *owns* does not appear in the body.

## Attributes

<PyAttribute name={"owns"} type={"frozenset[Role]"} value={null} />

## Functions

<PyFunction name={"defining"} type={"(self, body) -> SessionType"}>

Resolve the external boundary of *body* from `owns`.

<PySourceCode >

```python
def defining(self, body: Fragment[SessionType] | SessionType) -> SessionType:
    """Resolve the external boundary of *body* from :attr:`owns`.

    Args:
        body: An open fragment or closed session type whose every
            ``msg``/``alt`` prefix will be reclassified.

    Returns:
        A closed :class:`SessionType` with ``ipart(result) == self.owns``.

    Raises:
        ValueError: if a role in *owns* does not participate in *body*,
            or if a prefix mentions two roles and neither is owned.
    """
    resolved = _resolve_boundary(ensure_session(body), self.owns)
    _assert_interface(resolved, self.owns)
    return resolved
```

</PySourceCode>

<div >

<PyParameter name={"body"} type={"Fragment[SessionType] | SessionType"} value={undefined}>

An open fragment or closed session type whose every
``msg``/``alt`` prefix will be reclassified.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.session.types.SessionType"}>

A closed `SessionType` with ``ipart(result) == self.owns``.

</PyFunctionReturn>

</PyFunction>

<PyFunction name={"__init__"} type={"(self, owns) -> None"}>

<div >

<PyParameter name={"owns"} type={"frozenset[Role]"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
