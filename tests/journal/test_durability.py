"""Decision is durable before delivery (invariant 2)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from agentsparty.journal import MemoryJournal
from agentsparty.kernel.role import Role, roles
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.runtime import AgentRuntime
from tests._helpers import RAW_BY_CODEC
from tests.journal.conftest import Peer, session


@dataclass
class FailingReceiver:
    """Offers fail on the k-th delivery (1-based)."""

    role: Role
    endpoint_contract: EndpointType
    fail_at: int
    offers: int = 0
    received: list[Envelope] = field(default_factory=list)
    recalled: list[Envelope] = field(default_factory=list)
    cancelled: list[Cancelled] = field(default_factory=list)

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        branch = min(branches.values(), key=lambda candidate: candidate.label)
        raw = RAW_BY_CODEC[branch.payload.name]
        return Chosen(branch=branch, payload=branch.payload.decode(raw), raw=raw)

    async def offer(self, envelope: Envelope) -> None:
        self.offers += 1
        if self.offers == self.fail_at:
            raise RuntimeError('crash during offer')
        self.received.append(envelope)

    async def recall(self, envelope: Envelope) -> None:
        self.recalled.append(envelope)

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled.append(notice)


async def test_crash_mid_offer_keeps_the_decision() -> None:
    A, B = roles('A', 'B')
    proto = (
        msg[A, B]('First', Text) >> msg[A, B]('Second', Text) >> msg[A, B]('Third', Text)
    ).close()
    journal = MemoryJournal()
    sender = Peer(A, project(proto, A))
    receiver = FailingReceiver(B, project(proto, B), fail_at=2)
    with pytest.raises(RuntimeError, match='crash during offer'):
        await AgentRuntime(proto, [sender, receiver], journal=journal).run()

    assert journal.script().length == 2

    continuous, _ = await session(proto, MemoryJournal())
    resumed, peers = await session(proto, journal)
    assert resumed == continuous
    # First two steps replayed (no select for those), third was live for A.
    by_role = {peer.role.name: peer for peer in peers}
    assert by_role['A'].selects == 1
    assert by_role['B'].selects == 0


async def test_crash_on_first_offer_still_records_step_one() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Only', Text).close()
    journal = MemoryJournal()
    sender = Peer(A, project(proto, A))
    receiver = FailingReceiver(B, project(proto, B), fail_at=1)
    with pytest.raises(RuntimeError, match='crash during offer'):
        await AgentRuntime(proto, [sender, receiver], journal=journal).run()
    assert journal.script().length == 1
    assert journal.script().decisions[0].label == Label('Only')
