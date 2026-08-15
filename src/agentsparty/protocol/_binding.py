"""Bind a participant's declared endpoint to a global protocol projection."""

from __future__ import annotations

from agentsparty._utils.assertions import pre
from agentsparty.kernel.role import Role
from agentsparty.protocol._conformance import _refuse, _relate
from agentsparty.protocol.language.endpoint import EndpointType, free_vars
from agentsparty.protocol.session import project
from agentsparty.protocol.session.types import SessionType


def associate(
    declared: EndpointType | None,
    proto: SessionType,
    role: Role,
) -> EndpointType:
    """The endpoint type *role* is bound with, checked against *proto*.

    A participant is allowed to be a *subtype* of the projection, never an
    unrelated type. Saying nothing means "exactly the projection", which needs
    no check.

    Args:
        declared: The endpoint type the participant claims, or ``None`` to take
            the projection of *proto* on *role*.
        proto: The choreography the participant is bound to.
        role: The role the participant plays.

    Returns:
        The declared type when it fits, otherwise the projection.

    Raises:
        ConformanceError: if *declared* is not a subtype of the projection.
    """
    projected = project(proto, role)
    if declared is None:
        return projected
    pre(expr=not free_vars(declared), message='a declared endpoint type must be closed')
    _refuse(_relate(declared, projected, (), ()), role)
    return declared
