# endpoint (/docs/agentsparty/protocol/language/endpoint/index)

Endpoint types and DSL (``select``, ``offer``, ``send``, ``recv``).

This module is part of the public surface (extension tier): it is what
``declares=`` on a participant is built with. Its ``rec``, ``var`` and
``stop`` deliberately share their names with the session-level DSL in
``agentsparty.protocol`` — import the module, not the names::

    from agentsparty.protocol.language import endpoint

    tolerant = endpoint.offer(Lead, case('Sign', Text), case('Paused')).close()

<PyAttribute name={"EndpointType"} type={"TypeAlias"} value={"EndpointEnd | EndpointBranch | EndpointSelect | EndpointRec | EndpointVar"} />

<PyAttribute name={"EndpointFragment"} type={"TypeAlias"} value={"Fragment[EndpointType]"} />

<PyAttribute name={"stop"} type={"Fragment[EndpointType]"} value={"Fragment.halt(EndpointEnd())"} />

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"EndpointEnd"} href={"/docs/agentsparty/protocol/language/endpoint/EndpointEnd"} />
<Card title={"EndpointBranchCase"} href={"/docs/agentsparty/protocol/language/endpoint/EndpointBranchCase"} />
<Card title={"EndpointBranch"} href={"/docs/agentsparty/protocol/language/endpoint/EndpointBranch"} />
<Card title={"EndpointSelect"} href={"/docs/agentsparty/protocol/language/endpoint/EndpointSelect"} />
<Card title={"EndpointVar"} href={"/docs/agentsparty/protocol/language/endpoint/EndpointVar"} />
<Card title={"EndpointRec"} href={"/docs/agentsparty/protocol/language/endpoint/EndpointRec"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"free_vars"} type={"(node) -> frozenset[str]"}>

Names of free recursion variables in *node*.

<PySourceCode >

```python
def free_vars(node: EndpointType) -> frozenset[str]:
    """Names of free recursion variables in *node*.

    Args:
        node: An endpoint protocol tree (possibly open).

    Returns:
        The set of recursion-variable names not bound by an enclosing ``μ``.
    """
    match node:
        case EndpointEnd():
            return frozenset()
        case EndpointVar(name=name):
            return frozenset((name,))
        case EndpointBranch(branches=branches) | EndpointSelect(branches=branches):
            return frozenset().union(
                *(free_vars(branch.continuation) for branch in branches.values()),
            )
        case EndpointRec(name=name, body=body):
            return free_vars(body) - {name}
        case _:  # pragma: no cover
            assert_never(node)
```

</PySourceCode>

<div >

<PyParameter name={"node"} type={"EndpointType"} value={undefined}>

An endpoint protocol tree (possibly open).

</PyParameter>

</div>

<PyFunctionReturn type={"frozenset"}>

The set of recursion-variable names not bound by an enclosing ``μ``.

</PyFunctionReturn>

</PyFunction>
<PyFunction name={"unfold"} type={"(node) -> EndpointType"}>

Unfold one recursion step, replacing the binder with the recursion itself.

No-op unless *node* is a ``Rec``. Requires a closed argument: open terms
are not capture-avoiding; do not call ``unfold`` on open protocols.

<PySourceCode >

```python
def unfold(node: EndpointType) -> EndpointType:
    """Unfold one recursion step, replacing the binder with the recursion itself.

    No-op unless *node* is a ``Rec``. Requires a closed argument: open terms
    are not capture-avoiding; do not call ``unfold`` on open protocols.

    Args:
        node: A closed endpoint protocol.

    Returns:
        The body of *node* with free occurrences of the binder replaced by
        *node* itself, or *node* unchanged when it is not a ``Rec``.
    """
    match node:
        case EndpointRec(name=name, body=body):
            return _subst(body, name, node)
        case _:
            return node
```

</PySourceCode>

<div >

<PyParameter name={"node"} type={"EndpointType"} value={undefined}>

A closed endpoint protocol.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.endpoint.EndpointType"}>

The body of *node* with free occurrences of the binder replaced by

</PyFunctionReturn>

</PyFunction>
<PyFunction name={"var"} type={"(name) -> EndpointFragment"}>

Recursion variable leaf ``t`` — absorbs the sequential tail, like ``stop``.

<PySourceCode >

```python
def var(name: str) -> EndpointFragment:
    """Recursion variable leaf ``t`` — absorbs the sequential tail, like ``stop``.

    Args:
        name: The recursion-variable name (must match an enclosing ``rec``).
    """
    return Fragment.halt(EndpointVar(name))
```

</PySourceCode>

<div >

<PyParameter name={"name"} type={"str"} value={undefined}>

The recursion-variable name (must match an enclosing ``rec``).

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.endpoint.EndpointFragment"} />

</PyFunction>
<PyFunction name={"rec"} type={"(name, body) -> EndpointFragment"}>

Create a recursive endpoint fragment ``μ name.body``.

<PySourceCode >

```python
def rec(name: str, body: EndpointFragment) -> EndpointFragment:
    """Create a recursive endpoint fragment ``μ name.body``."""
    return Fragment(partial(_build_rec, name, body), EndpointEnd())
```

</PySourceCode>

<div >

<PyParameter name={"name"} type={"str"} value={null} />
<PyParameter name={"body"} type={"EndpointFragment"} value={null} />

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.endpoint.EndpointFragment"} />

</PyFunction>
<PyFunction name={"select"} type={"(receiver, first, *rest) -> EndpointFragment"}>

Internal alt: we pick a label and send it to *receiver*.

<PySourceCode >

```python
def select(
    receiver: Role,
    first: Case[EndpointType],
    *rest: Case[EndpointType],
) -> EndpointFragment:
    """Internal alt: we pick a label and send it to *receiver*.

    Args:
        receiver: The role receiving the chosen message.
        first: The first labelled alternative we may pick from.
        *rest: The remaining labelled alternatives.
    """
    alternatives = _bodies((first, *rest))
    return Fragment(
        lambda tail: EndpointSelect(receiver, _endpoint_branches(alternatives, tail)),
        EndpointEnd(),
    )
```

</PySourceCode>

<div >

<PyParameter name={"receiver"} type={"Role"} value={undefined}>

The role receiving the chosen message.

</PyParameter>
<PyParameter name={"first"} type={"Case[EndpointType]"} value={undefined}>

The first labelled alternative we may pick from.

</PyParameter>
<PyParameter name={"rest"} type={"Case[EndpointType]"} value={"()"} />

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.endpoint.EndpointFragment"} />

</PyFunction>
<PyFunction name={"offer"} type={"(sender, first, *rest) -> EndpointFragment"}>

External alt: *sender* picks a label and we react to it.

<PySourceCode >

```python
def offer(
    sender: Role,
    first: Case[EndpointType],
    *rest: Case[EndpointType],
) -> EndpointFragment:
    """External alt: *sender* picks a label and we react to it.

    Args:
        sender: The role choosing the branch.
        first: The first labelled alternative we react to.
        *rest: The remaining labelled alternatives.
    """
    alternatives = _bodies((first, *rest))
    return Fragment(
        lambda tail: EndpointBranch(sender, _endpoint_branches(alternatives, tail)),
        EndpointEnd(),
    )
```

</PySourceCode>

<div >

<PyParameter name={"sender"} type={"Role"} value={undefined}>

The role choosing the branch.

</PyParameter>
<PyParameter name={"first"} type={"Case[EndpointType]"} value={undefined}>

The first labelled alternative we react to.

</PyParameter>
<PyParameter name={"rest"} type={"Case[EndpointType]"} value={"()"} />

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.endpoint.EndpointFragment"} />

</PyFunction>
<PyFunction name={"send"} type={"(receiver, label, payload=Text, intent='', *, within=None) -> EndpointFragment"}>

Send a single message labelled *label* with *payload* to *receiver*.

<PySourceCode >

```python
def send(
    receiver: Role,
    label: str | Label,
    payload: Codec[Any] = Text,
    intent: str = '',
    *,
    within: Deadline | None = None,
) -> EndpointFragment:
    """Send a single message labelled *label* with *payload* to *receiver*.

    Args:
        receiver: The role receiving the message.
        label: The message label.
        payload: The codec for the message payload; defaults to :data:`Text`.
        intent: What the sender is asked to produce; defaults to empty.
        within: Optional wall-clock deadline; see :func:`~agentsparty.protocol.language.core.case`.
    """
    return select(receiver, case(label, payload, intent=intent, within=within))
```

</PySourceCode>

<div >

<PyParameter name={"receiver"} type={"Role"} value={undefined}>

The role receiving the message.

</PyParameter>
<PyParameter name={"label"} type={"str | Label"} value={undefined}>

The message label.

</PyParameter>
<PyParameter name={"payload"} type={"Codec[Any]"} value={"Text"}>

The codec for the message payload; defaults to `Text`.

</PyParameter>
<PyParameter name={"intent"} type={"str"} value={"''"}>

What the sender is asked to produce; defaults to empty.

</PyParameter>
<PyParameter name={"within"} type={"Deadline | None"} value={"None"}>

Optional wall-clock deadline; see [`case`](/docs/agentsparty/protocol/language/core).

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.endpoint.EndpointFragment"} />

</PyFunction>
<PyFunction name={"recv"} type={"(sender, label, payload=Text, intent='', *, within=None) -> EndpointFragment"}>

Receive a single message labelled *label* with *payload* from *sender*.

<PySourceCode >

```python
def recv(
    sender: Role,
    label: str | Label,
    payload: Codec[Any] = Text,
    intent: str = '',
    *,
    within: Deadline | None = None,
) -> EndpointFragment:
    """Receive a single message labelled *label* with *payload* from *sender*.

    Args:
        sender: The role sending the message.
        label: The message label.
        payload: The codec for the message payload; defaults to :data:`Text`.
        intent: What the sender is asked to produce; defaults to empty.
        within: Optional wall-clock deadline; see :func:`~agentsparty.protocol.language.core.case`.
    """
    return offer(sender, case(label, payload, intent=intent, within=within))
```

</PySourceCode>

<div >

<PyParameter name={"sender"} type={"Role"} value={undefined}>

The role sending the message.

</PyParameter>
<PyParameter name={"label"} type={"str | Label"} value={undefined}>

The message label.

</PyParameter>
<PyParameter name={"payload"} type={"Codec[Any]"} value={"Text"}>

The codec for the message payload; defaults to `Text`.

</PyParameter>
<PyParameter name={"intent"} type={"str"} value={"''"}>

What the sender is asked to produce; defaults to empty.

</PyParameter>
<PyParameter name={"within"} type={"Deadline | None"} value={"None"}>

Optional wall-clock deadline; see [`case`](/docs/agentsparty/protocol/language/core).

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.protocol.language.endpoint.EndpointFragment"} />

</PyFunction>

</Tab>

</Tabs>
