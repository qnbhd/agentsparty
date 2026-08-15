"""Convert between single-subject sessions and endpoint protocols."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from typing_extensions import assert_never

from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Label, branches_map
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointBranchCase,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    EndpointVar,
)
from agentsparty.protocol.session.types import (
    RecvFrom,
    SendTo,
    SessionBranchCase,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
    SingleSubject,
)


def as_endpoint(node: SingleSubject) -> EndpointType:
    """Forget the single internal subject of *node*.

    Total on projections onto a singleton; an ``Interaction`` or ``Parallel``
    inside means the argument was not a single-subject view and raises
    ValueError.

    Args:
        node: A single-subject session type (typically ``project_onto(H, {r})``).

    Returns:
        The subject-implicit endpoint protocol.

    Raises:
        ValueError: if *node* contains an internal interaction.
    """
    match node:
        case SessionEnd():
            return EndpointEnd()
        case SessionVar(name=name):
            return EndpointVar(name)
        case SessionRec(name=name, body=body):
            return EndpointRec(name, as_endpoint(cast(SingleSubject, body)))
        case SendTo(receiver=receiver, branches=branches):
            return EndpointSelect(receiver, _to_endpoint_branches(branches))
        case RecvFrom(sender=sender, branches=branches):
            return EndpointBranch(sender, _to_endpoint_branches(branches))
        case _:  # pragma: no cover
            assert_never(node)


def as_session(subject: Role, node: EndpointType) -> SessionType:
    """Name the implicit subject of *node*.

    Args:
        subject: The role that owns *node*.
        node: A subject-implicit endpoint protocol.

    Returns:
        The session type with *subject* made explicit on every interface prefix.
    """
    match node:
        case EndpointEnd():
            return SessionEnd()
        case EndpointVar(name=name):
            return SessionVar(name)
        case EndpointRec(name=name, body=body):
            return SessionRec(name, as_session(subject, body))
        case EndpointSelect(receiver=receiver, branches=branches):
            return SendTo(subject, receiver, _from_endpoint_branches(subject, branches))
        case EndpointBranch(sender=sender, branches=branches):
            return RecvFrom(sender, subject, _from_endpoint_branches(subject, branches))
        case _:  # pragma: no cover
            assert_never(node)


def _to_endpoint_branches(
    branches: Mapping[Label, SessionBranchCase],
) -> NonEmptyMap[Label, EndpointBranchCase]:
    return branches_map(
        EndpointBranchCase(
            branch.label,
            branch.payload,
            as_endpoint(cast(SingleSubject, branch.continuation)),
            branch.intent,
            branch.within,
        )
        for branch in branches.values()
    )


def _from_endpoint_branches(
    subject: Role,
    branches: Mapping[Label, EndpointBranchCase],
) -> NonEmptyMap[Label, SessionBranchCase]:
    return branches_map(
        SessionBranchCase(
            branch.label,
            branch.payload,
            as_session(subject, branch.continuation),
            branch.intent,
            branch.within,
        )
        for branch in branches.values()
    )
