from __future__ import annotations

from agentsparty.journal.types import Journal
from agentsparty.kernel.budget import Allowance
from agentsparty.kernel.errors import ProjectionError
from agentsparty.kernel.role import roles
from agentsparty.participant import Envelope
from agentsparty.protocol import Text, msg, participants, project
from agentsparty.protocol.session import SessionType
from agentsparty.runtime import AgentRuntime
from tests._helpers import DeterministicPeer

Peer = DeterministicPeer


def three_message_protocol() -> SessionType:
    """Return the short protocol shared by journal durability tests."""
    A, B = roles('A', 'B')
    return (
        msg[A, B]('First', Text) >> msg[A, B]('Second', Text) >> msg[A, B]('Third', Text)
    ).close()


def is_projectable(proto: SessionType) -> bool:
    """Whether every participant of *proto* has a local projection."""
    try:
        for role in participants(proto):
            project(proto, role)
    except ProjectionError:
        return False
    return True


async def session(
    proto: SessionType,
    journal: Journal,
    *,
    allowance: Allowance | None = None,
) -> tuple[list[Envelope], list[Peer]]:
    """Run *proto* with fresh deterministic peers over *journal*."""
    from agentsparty.kernel.budget import DEFAULT_ALLOWANCE

    peers = [Peer(role, project(proto, role)) for role in participants(proto)]
    chosen = DEFAULT_ALLOWANCE if allowance is None else allowance
    trace = await AgentRuntime(proto, peers, journal=journal, allowance=chosen).run()
    return trace, peers
