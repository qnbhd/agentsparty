"""Stable structural encoding of a protocol for journal digests.

Human-facing :func:`~agentsparty.protocol.render.render` is not stable; this module
owns the bytes that define persistent protocol identity.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, Final

from typing_extensions import assert_never

from agentsparty._utils.assertions import post, pre
from agentsparty.protocol.language.core import Deadline, Label
from agentsparty.protocol.session import epart, free_vars, ipart
from agentsparty.protocol.session.types import (
    Interaction,
    Parallel,
    RecvFrom,
    SendTo,
    SessionBranchCase,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
)

_PREFIX = b'agentsparty/protocol-digest/1\0'
_JSON_SEP = (',', ':')
_TAG_KEY: Final = 'tag'


def canonical_protocol(proto: SessionType) -> bytes:
    r"""Encode *proto* as order-insensitive canonical digest bytes.

    Preconditions:
        *proto* is a closed well-formed session type (no free recursion vars).

    Postconditions:
        Result starts with ``b"agentsparty/protocol-digest/1\0"``.

    Invariant:
        Mapping-arm order and ``Parallel`` branch order do not affect the bytes.
    """
    pre(expr=not free_vars(proto), message='canonical_protocol requires a closed SessionType')
    body = json.dumps(
        _node(proto),
        sort_keys=True,
        separators=_JSON_SEP,
        ensure_ascii=True,
    ).encode('utf-8')
    result = _PREFIX + body
    post(expr=result.startswith(_PREFIX), message='canonical encoding carries version prefix')
    return result


def _node(proto: SessionType) -> dict[str, Any]:
    match proto:
        case SessionEnd():
            return {_TAG_KEY: 'end'}
        case SessionVar(name=name):
            return {_TAG_KEY: 'var', 'name': name}
        case SessionRec(name=name, body=body):
            return {_TAG_KEY: 'rec', 'name': name, 'body': _node(body)}
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _node_prefix(prefix)
        case Parallel(branches=branches):
            return _node_parallel(branches)
        case _:  # pragma: no cover
            assert_never(proto)


def _node_prefix(prefix: Interaction | SendTo | RecvFrom) -> dict[str, Any]:
    match prefix:
        case Interaction(sender=sender, receiver=receiver, branches=branches):
            tag = 'interaction'
        case SendTo(sender=sender, receiver=receiver, branches=branches):
            tag = 'send_to'
        case RecvFrom(sender=sender, receiver=receiver, branches=branches):
            tag = 'recv_from'
        case _:  # pragma: no cover
            assert_never(prefix)
    return {
        _TAG_KEY: tag,
        'sender': sender.name,
        'receiver': receiver.name,
        'arms': _arms(branches),
    }


def _node_parallel(branches: tuple[SessionType, ...]) -> dict[str, Any]:
    ordered = sorted(branches, key=_branch_order_key)
    return {_TAG_KEY: 'parallel', 'branches': [_node(branch) for branch in ordered]}


def _arms(branches: Mapping[Label, SessionBranchCase]) -> list[dict[str, Any]]:
    """Arms sorted by label name so mapping insertion order is irrelevant."""
    ordered = sorted(branches.values(), key=lambda arm: arm.label.name)
    return [_arm(arm) for arm in ordered]


def _arm(branch: SessionBranchCase) -> dict[str, Any]:
    return {
        'label': branch.label.name,
        'codec': branch.payload.name,
        'intent': branch.intent,
        'deadline': _deadline_us(branch.within),
        'continuation': _node(branch.continuation),
    }


def _deadline_us(within: Deadline | None) -> int | None:
    """Deadline as exact integer microseconds, or null when absent."""
    if within is None:
        return None
    return within.duration // timedelta(microseconds=1)


def _branch_order_key(branch: SessionType) -> tuple[str, ...]:
    """Same key as session parallel normalisation: sorted role names."""
    roles = ipart(branch) | epart(branch)
    return tuple(sorted(role.name for role in roles))
