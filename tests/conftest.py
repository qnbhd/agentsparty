"""Shared scripted participant for runtime-level tests (ADR 0041)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from hypothesis import HealthCheck, settings

from agentsparty.kernel.role import Role
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import project
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.protocol.session import SessionType

settings.register_profile(
    'default',
    suppress_health_check=[HealthCheck.too_slow],
)


@dataclass
class Stub:
    """Scripted participant: plays *alts* in order and records everything."""

    role: Role
    endpoint_contract: EndpointType
    alts: list[Choice] = field(default_factory=list)
    received: list[Envelope] = field(default_factory=list)
    recalled: list[Envelope] = field(default_factory=list)
    cancelled: list[Cancelled] = field(default_factory=list)

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        scripted = self.alts.pop(0)
        branch = branches[scripted.label]
        return Chosen(branch=branch, payload=scripted.payload, raw=scripted.payload)

    async def offer(self, envelope: Envelope) -> None:
        self.received.append(envelope)

    async def recall(self, envelope: Envelope) -> None:
        self.recalled.append(envelope)

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled.append(notice)


def stub(proto: SessionType, role: Role, *alts: Choice) -> Stub:
    """A Stub bound to *role*'s projection of *proto*."""
    return Stub(role, project(proto, role), list(alts))
