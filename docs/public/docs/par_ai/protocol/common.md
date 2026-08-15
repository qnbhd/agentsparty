# common (/docs/agentsparty/protocol/common/index)

Compatibility facade for the pre-0015 ``protocol.common`` import path.

Algorithms live in [`analysis`](/docs/agentsparty/protocol/analysis), [`render`](/docs/agentsparty/protocol/render),
[`core`](/docs/agentsparty/protocol/language/core), and [`session`](/docs/agentsparty/protocol/session).
This module re-exports the previous public surface for one minor release and
must not be imported from production code under ``src/agentsparty``.

<Tabs items={["Functions"]}>

<Tab value={"Functions"}>

<PyFunction name={"participants"} type={"(node) -> list[Role]"}>

Every role mentioned by the protocol, in order of first appearance.

<PySourceCode >

```python
def participants(node: SessionType) -> list[Role]:
    """Every role mentioned by the protocol, in order of first appearance."""
    roles = (role for prefix in _walk(node) for role in (prefix.sender, prefix.receiver))
    return list(dict.fromkeys(roles))
```

</PySourceCode>

<div >

<PyParameter name={"node"} type={"SessionType"} value={null} />

</div>

<PyFunctionReturn type={"list[agentsparty.kernel.role.Role]"} />

</PyFunction>
<PyFunction name={"project"} type={"(node, subj) -> EndpointType"}>

Derive the endpoint protocol *subj* has to follow.

Validates well-formedness of *node* once at the root, then projects.
Implemented as the singleton special case of `project_onto`. An open
[`Fragment`](/docs/agentsparty/protocol/language/core/Fragment) is closed at this boundary.

<PySourceCode >

```python
def project(node: SessionType | Fragment[SessionType], subj: Role) -> EndpointType:
    """Derive the endpoint protocol *subj* has to follow.

    Validates well-formedness of *node* once at the root, then projects.
    Implemented as the singleton special case of :func:`project_onto`. An open
    :class:`~agentsparty.protocol.language.core.Fragment` is closed at this boundary.

    Args:
        node: A closed, guarded session protocol (choreography or a component),
            or a fragment that will be closed first.
        subj: The role whose endpoint view is required.

    Raises:
        ValueError: if *node* is open or unguarded.
        ProjectionError: if merge is undefined for an observer of a alt.
    """
    projected = project_onto(ensure_session(node), frozenset((subj,)))
    return as_endpoint(cast(SingleSubject, projected))
```

</PySourceCode>

<div >

<PyParameter name={"node"} type={"SessionType | Fragment[SessionType]"} value={undefined}>

A closed, guarded session protocol (choreography or a component),
or a fragment that will be closed first.

</PyParameter>
<PyParameter name={"subj"} type={"Role"} value={undefined}>

The role whose endpoint view is required.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.session._bridge.EndpointType"} />

</PyFunction>
<PyFunction name={"project_all"} type={"(node) -> list[tuple[Role, EndpointType]]"}>

Project *node* for every participant, in order of first appearance.

An open [`Fragment`](/docs/agentsparty/protocol/language/core/Fragment) is closed at this boundary.

<PySourceCode >

```python
def project_all(
    node: SessionType | Fragment[SessionType],
) -> list[tuple[Role, EndpointType]]:
    """Project *node* for every participant, in order of first appearance.

    An open :class:`~agentsparty.protocol.language.core.Fragment` is closed at this boundary.

    Args:
        node: The session protocol to project, or a fragment that will be closed.

    Returns:
        Pairs of ``(role, endpoint protocol)``, one per participant.
    """
    closed = ensure_session(node)
    return [(subject, project(closed, subject)) for subject in participants(closed)]
```

</PySourceCode>

<div >

<PyParameter name={"node"} type={"SessionType | Fragment[SessionType]"} value={undefined}>

The session protocol to project, or a fragment that will be closed.

</PyParameter>

</div>

<PyFunctionReturn type={"list"}>

Pairs of ``(role, endpoint protocol)``, one per participant.

</PyFunctionReturn>

</PyFunction>

</Tab>

</Tabs>
