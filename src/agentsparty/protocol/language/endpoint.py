"""Endpoint types and DSL (``select``, ``offer``, ``send``, ``recv``).

This module is part of the public surface (extension tier): it is what
``declares=`` on a participant is built with. Its ``rec``, ``var`` and
``stop`` deliberately share their names with the session-level DSL in
``agentsparty.protocol`` — import the module, not the names::

    from agentsparty.protocol.language import endpoint

    tolerant = endpoint.offer(Lead, case('Sign', Text), case('Paused')).close()
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import partial
from typing import Any, TypeAlias

from typing_extensions import assert_never

from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import (
    Case,
    Codec,
    Deadline,
    Fragment,
    Label,
    Text,
    _bodies,
    _continuation,
    branches_map,
    case,
)


@dataclass(frozen=True, slots=True)
class EndpointEnd:
    """Endpoint protocol ending."""


@dataclass(frozen=True, slots=True)
class EndpointBranchCase:
    """One labelled alternative within an endpoint interaction."""

    label: Label
    payload: Codec[Any]
    continuation: EndpointType
    intent: str = ''
    within: Deadline | None = None


@dataclass(frozen=True, slots=True)
class EndpointBranch:
    """External alt: we react to a label :attr:`sender` picks."""

    sender: Role
    branches: NonEmptyMap[Label, EndpointBranchCase]


@dataclass(frozen=True, slots=True)
class EndpointSelect:
    """Internal alt: we pick a label to send to :attr:`receiver`."""

    receiver: Role
    branches: NonEmptyMap[Label, EndpointBranchCase]


@dataclass(frozen=True, slots=True)
class EndpointVar:
    """A free or bound recursion variable in an endpoint type."""

    name: str


@dataclass(frozen=True, slots=True)
class EndpointRec:
    """A recursive endpoint type ``μ name.body``."""

    name: str
    body: EndpointType


EndpointType: TypeAlias = EndpointEnd | EndpointBranch | EndpointSelect | EndpointRec | EndpointVar
EndpointFragment: TypeAlias = Fragment[EndpointType]

stop: Fragment[EndpointType] = Fragment.halt(EndpointEnd())


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


def _is_guarded(name: str, node: EndpointType) -> bool:
    """Whether every free occurrence of *name* in *node* sits under a prefix."""
    match node:
        case EndpointEnd():
            return True
        case EndpointVar(name=var_name):
            return var_name != name
        case EndpointBranch() | EndpointSelect():
            return True
        case EndpointRec(name=binder, body=body):
            if binder == name:
                return True
            return _is_guarded(name, body)
        case _:  # pragma: no cover
            assert_never(node)


def _subst(node: EndpointType, name: str, replacement: EndpointType) -> EndpointType:
    """Substitute *replacement* for free occurrences of *name* (shadowing-aware)."""
    match node:
        case EndpointEnd():
            return node
        case EndpointVar(name=var_name):
            return replacement if var_name == name else node
        case EndpointBranch() | EndpointSelect():
            return replace(
                node,
                branches=branches_map(
                    replace(
                        branch,
                        continuation=_subst(branch.continuation, name, replacement),
                    )
                    for branch in node.branches.values()
                ),
            )
        case EndpointRec(name=binder, body=body):
            if binder == name:
                return node
            return EndpointRec(binder, _subst(body, name, replacement))
        case _:  # pragma: no cover
            assert_never(node)


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


def var(name: str) -> EndpointFragment:
    """Recursion variable leaf ``t`` — absorbs the sequential tail, like ``stop``.

    Args:
        name: The recursion-variable name (must match an enclosing ``rec``).
    """
    return Fragment.halt(EndpointVar(name))


def _build_rec(name: str, body: EndpointFragment, tail: EndpointType) -> EndpointType:
    if name in free_vars(tail):
        raise ValueError(
            f'sequential tail after rec({name!r}, …) contains a free '
            f'var({name!r}) and would be captured; write it inside the body',
        )
    filled = body.fill(tail)
    if not _is_guarded(name, filled):
        raise ValueError(f'unguarded recursion variable {name!r} in rec body')
    return EndpointRec(name, filled)


def rec(name: str, body: EndpointFragment) -> EndpointFragment:
    """Create a recursive endpoint fragment ``μ name.body``."""
    return Fragment(partial(_build_rec, name, body), EndpointEnd())


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


def _endpoint_branches(
    alternatives: tuple[Case[EndpointType], ...],
    tail: EndpointType,
) -> NonEmptyMap[Label, EndpointBranchCase]:
    return branches_map(
        EndpointBranchCase(
            alternative.label,
            alternative.payload,
            _continuation(alternative.body, tail, EndpointEnd()),
            alternative.intent,
            alternative.within,
        )
        for alternative in alternatives
    )


__all__ = [
    'EndpointBranch',
    'EndpointBranchCase',
    'EndpointEnd',
    'EndpointFragment',
    'EndpointRec',
    'EndpointSelect',
    'EndpointType',
    'EndpointVar',
    'free_vars',
    'offer',
    'rec',
    'recv',
    'select',
    'send',
    'stop',
    'unfold',
    'var',
]
