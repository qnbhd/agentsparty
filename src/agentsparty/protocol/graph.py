"""Neutral graph views of global and endpoint protocol ASTs.

The graph deliberately contains semantics only.  Coordinates, colours and
renderer-specific fields belong to documentation clients.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypedDict, cast

from typing_extensions import Required, assert_never

from agentsparty._utils.assertions import post, pre, safe_assert
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Codec, Fragment
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    EndpointVar,
)
from agentsparty.protocol.session import participants
from agentsparty.protocol.session.types import (
    Interaction,
    Parallel,
    RecvFrom,
    SendTo,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
)

__all__ = ['GraphEdge', 'GraphNode', 'ProtocolGraph', 'to_graph']

_CHOICE = 'alt'
_SEQUENCE = 'sequence'


# These keys are part of the public JSON graph schema.
GraphNode = TypedDict(
    'GraphNode',
    {
        'id': Required[str],
        'kind': str,  # noqa: WPS226
        'from': str,  # noqa: WPS226
        'to': str,  # noqa: WPS226
        'label': str,
        'codec': str,
        'branch': str,  # noqa: WPS226
        'selector': str,
        'peer': str,
        'cases': list[str],
        'direction': str,
        'role': str,
    },
    total=False,
)


GraphEdge = TypedDict(
    'GraphEdge',
    {
        'from': str,
        'to': str,
        'kind': str,
        'label': str,
        'case': str,
        'role': str,
    },
    total=False,
)


class ProtocolGraph(TypedDict):
    """JSON-compatible graph returned by :func:`to_graph`."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    roles: list[str]


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[GraphNode] = []
        self.edges: list[GraphEdge] = []
        self._next_id = 1

    def node(self, kind: str, **fields: object) -> str:
        node_id = f'n{self._next_id}'
        self._next_id += 1
        node = cast(GraphNode, {'id': node_id, 'kind': kind, **fields})
        self.nodes.append(node)
        return node_id

    def edge(self, source: str, target: str, kind: str, **fields: object) -> None:
        edge = cast(GraphEdge, {'from': source, 'to': target, 'kind': kind, **fields})
        self.edges.append(edge)


def _label(value: object) -> str:
    return str(value)


def _branch_labels(branches: Iterable[Any]) -> list[str]:
    return [_label(branch.label) for branch in branches]


def _message_participants(sender: Role, receiver: Role) -> dict[str, str]:
    return {'from': sender.name, 'to': receiver.name}


def _codec(codec: object) -> str:
    names = {'str': 'TEXT', 'int': 'INT', 'float': 'NUMBER', 'bool': 'FLAG'}
    match codec:
        case Codec(name=name):
            return names.get(name, name.upper())
        case _:
            return str(codec).upper()


def _branches(node: Interaction | SendTo | RecvFrom) -> list[object]:
    return list(node.branches.values())


def _local_signature(node: SessionType, focus: Role) -> tuple[str, str] | None:  # noqa: C901, WPS231
    """Return the first action a role must take in a branch."""
    pending = [node]
    while pending:
        current = pending.pop()
        match current:
            case SessionEnd() | SessionVar():
                continue
            case SessionRec(body=body):
                pending.append(body)
            case Parallel(branches=branches):
                pending.extend(reversed(branches))
            case (
                Interaction(sender=sender, receiver=receiver, branches=branches)
                | SendTo(sender=sender, receiver=receiver, branches=branches)
                | RecvFrom(sender=sender, receiver=receiver, branches=branches)
            ):
                if sender == focus:
                    return ('!', receiver.name)
                if receiver == focus:
                    return ('?', sender.name)
                pending.extend(reversed([branch.continuation for branch in branches.values()]))
            case _:  # pragma: no cover
                assert_never(current)
    return None


def _global_interaction_message(
    item: Any,
    sender: Role,
    receiver: Role,
    builder: _Builder,
    focus: Role | None,
    branch: str | None,
) -> str:
    message = builder.node(
        'message',
        **_message_participants(sender, receiver),
        label=_label(item.label),
        codec=_codec(item.payload),
        branch=branch,
    )
    continuation = _global_node(item.continuation, builder, focus)
    builder.edge(message, continuation, _SEQUENCE)
    _add_silence(builder, message, sender, receiver, focus)
    return message


def _global_interaction_node(
    sender: Role,
    receiver: Role,
    branches: Any,
    builder: _Builder,
    focus: Role | None,
    branch: str | None,
) -> str:
    ordered = list(branches.values())
    if len(ordered) == 1:
        return _global_interaction_message(ordered[0], sender, receiver, builder, focus, branch)
    alt = _global_alt_node(sender, receiver, ordered, builder, focus)
    _add_gap(builder, alt, ordered, focus)
    return alt


def _external_direction(node: SendTo | RecvFrom) -> str:
    match node:
        case SendTo():
            return '!'
        case RecvFrom():
            return '?'
        case _:
            assert_never(node)


def _global_alt_node(
    sender: Role,
    receiver: Role,
    branches: list[Any],
    builder: _Builder,
    focus: Role | None,
) -> str:
    """Build the shared multi-branch graph node and its continuation edges."""
    pre(expr=len(branches) > 1, message='a alt node needs multiple branches')
    labels = _branch_labels(branches)
    alt = builder.node(
        _CHOICE,
        selector=sender.name,
        peer=receiver.name,
        cases=labels,
    )
    for label, branch_item in zip(labels, branches, strict=True):
        builder.edge(
            alt,
            _global_node(branch_item.continuation, builder, focus, label),
            'branch',
            case=label,
        )
    safe_assert(expr=alt.startswith('n'), message='alt nodes use graph ids')
    return alt


def _global_external_message(
    item: Any,
    sender: Role,
    receiver: Role,
    builder: _Builder,
    focus: Role | None,
    branch: str | None,
    direction: str,
) -> str:
    message = builder.node(
        'message',
        **_message_participants(sender, receiver),
        label=_label(item.label),
        codec=_codec(item.payload),
        direction=direction,
        branch=branch,
    )
    continuation = _global_node(item.continuation, builder, focus)
    builder.edge(message, continuation, _SEQUENCE)
    return message


def _global_parallel_node(
    branches: Iterable[SessionType],
    builder: _Builder,
    focus: Role | None,
) -> str:
    ordered = tuple(branches)
    root = builder.node(
        'parallel',
        cases=list(map(str, range(len(ordered)))),
    )
    for index, child in enumerate(ordered):
        child_id = _global_node(child, builder, focus)
        builder.edge(root, child_id, 'branch', case=str(index))
    return root


def _global_node(  # noqa: C901
    node: SessionType,
    builder: _Builder,
    focus: Role | None,
    branch: str | None = None,
) -> str:
    """Build one global subtree and return its entry node id."""
    match node:
        case SessionEnd():
            result = builder.node('end', branch=branch)
        case SessionVar(name=name):
            result = builder.node('var', label=name)
        case SessionRec(name=name, body=body):
            root = builder.node('rec', label=name)
            body_id = _global_node(body, builder, focus)
            builder.edge(root, body_id, _SEQUENCE)
            result = root
        case Parallel(branches=branches):
            result = _global_parallel_node(branches, builder, focus)
        case Interaction(sender=sender, receiver=receiver, branches=branches):
            result = _global_interaction_node(sender, receiver, branches, builder, focus, branch)
        case (
            SendTo(sender=sender, receiver=receiver, branches=branches)
            | RecvFrom(
                sender=sender,
                receiver=receiver,
                branches=branches,
            )
        ) as external:
            result = _global_external_node(
                sender,
                receiver,
                branches,
                builder,
                focus,
                branch,
                _external_direction(external),
            )
        case _:  # pragma: no cover
            assert_never(node)
    return result


def _global_external_node(
    sender: Role,
    receiver: Role,
    branches: Any,
    builder: _Builder,
    focus: Role | None,
    branch: str | None,
    direction: str,
) -> str:
    ordered = list(branches.values())
    if len(ordered) == 1:
        return _global_external_message(
            ordered[0], sender, receiver, builder, focus, branch, direction
        )
    return _global_alt_node(sender, receiver, ordered, builder, focus)


def _add_silence(
    builder: _Builder,
    message: str,
    sender: Role,
    receiver: Role,
    focus: Role | None,
) -> None:
    if focus is not None and focus not in {sender, receiver}:
        observer = builder.node('observation', role=focus.name, label='silent')
        builder.edge(message, observer, 'silence', role=focus.name)


def _add_gap(
    builder: _Builder,
    alt: str,
    branches: Iterable[Any],
    focus: Role | None,
) -> None:
    if focus is None:
        return
    cases = list(branches)
    signatures = [_local_signature(item.continuation, focus) for item in cases]
    if len(signatures) < 2 or len(set(signatures)) == 1:
        return
    unknown = builder.node('unknown', role=focus.name, label='???')
    builder.edge(alt, unknown, 'gap', role=focus.name, label='?')


def _endpoint_node(node: EndpointType, builder: _Builder, role: Role) -> str:  # noqa: C901
    match node:
        case EndpointEnd():
            return builder.node('end')
        case EndpointVar(name=name):
            return builder.node('var', label=name)
        case EndpointRec(name=name, body=body):
            root = builder.node('rec', label=name)
            child = _endpoint_node(body, builder, role)
            builder.edge(root, child, _SEQUENCE)
            return root
        case EndpointSelect(receiver=receiver, branches=branches):
            ordered = list(branches.values())
            alt = builder.node(
                _CHOICE,
                selector=role.name,
                peer=receiver.name,
                cases=_branch_labels(ordered),
            )
            for branch_item in ordered:
                child = _endpoint_node(branch_item.continuation, builder, role)
                builder.edge(alt, child, 'branch', case=_label(branch_item.label))
            return alt
        case EndpointBranch(sender=sender, branches=branches):
            ordered = list(branches.values())
            alt = builder.node(
                _CHOICE,
                selector=sender.name,
                peer=role.name,
                cases=_branch_labels(ordered),
            )
            for branch_item in ordered:
                child = _endpoint_node(branch_item.continuation, builder, role)
                builder.edge(alt, child, 'branch', case=_label(branch_item.label))
            return alt
        case _:  # pragma: no cover
            assert_never(node)


def _as_protocol(value: object) -> SessionType | EndpointType:
    match value:
        case Fragment() as fragment:
            return cast(SessionType | EndpointType, fragment.close())
        case _:
            return cast(SessionType | EndpointType, value)


def to_graph(
    protocol: SessionType | EndpointType | Fragment[SessionType] | Fragment[EndpointType],
    role: Role | None = None,
) -> ProtocolGraph:
    """Return a neutral graph for a global protocol or one endpoint.

    A role-aware global graph receives one ``gap`` edge when the role's first
    actions differ across an unobserved alt.  This is deliberately a graph
    fact, so visual clients cannot accidentally turn a missing signal into a
    colour-only annotation.
    """
    pre(expr=protocol is not None, message='protocol is required')
    value = _as_protocol(protocol)
    builder = _Builder()

    # Build the requested view from the AST, preserving role and branch data.
    match value:
        case EndpointEnd() | EndpointVar() | EndpointBranch() | EndpointSelect() | EndpointRec():
            pre(expr=role is not None, message='role is required for an endpoint graph')
            subject = cast(Role, role)
            _endpoint_node(value, builder, subject)
            roles = [subject.name]
        case (
            SessionEnd()
            | SessionVar()
            | Interaction()
            | SendTo()
            | RecvFrom()
            | SessionRec()
            | Parallel()
        ):
            _global_node(value, builder, role, None)
            roles = [item.name for item in participants(value)]
        case _:  # pragma: no cover
            assert_never(value)

    safe_assert(expr=bool(builder.nodes), message='a protocol graph must have a root node')
    result: ProtocolGraph = {'nodes': builder.nodes, 'edges': builder.edges, 'roles': roles}
    root_id = result['nodes'][0]['id']
    post(expr=root_id == 'n1', message='graph ids must start at n1')
    return result
