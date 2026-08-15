"""Optional per-branch wall-clock deadlines: surface, render, and runtime."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta

import pytest

from agentsparty.kernel.errors import DeadlineExceeded, ProjectionError
from agentsparty.kernel.role import Role, roles
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import Deadline, Label, Text, alt, case, msg, project, render
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointSelect, EndpointType
from agentsparty.runtime import AgentRuntime


@dataclass
class Stub:
    role: Role
    endpoint_contract: EndpointType
    alts: list[Choice] = field(default_factory=list)
    cancelled: list[Cancelled] = field(default_factory=list)
    delay: float = 0.0

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        if self.delay:
            await asyncio.sleep(self.delay)
        scripted = self.alts.pop(0)
        branch = branches[scripted.label]
        return Chosen(branch=branch, payload=scripted.payload, raw=scripted.payload)

    async def offer(self, envelope: Envelope) -> None:
        pass

    async def recall(self, envelope: Envelope) -> None:
        pass

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled.append(notice)


def test_within_survives_projection_and_render() -> None:
    """Deadline metadata projects, renders, and distinguishes signatures."""
    A, B = roles('A', 'B')
    window = Deadline(timedelta(seconds=30))
    proto = alt[A, B](case('Sign', Text, within=window), case('Cancel')).close()
    local = project(proto, A)
    assert isinstance(local, EndpointSelect)
    assert local.branches[Label('Sign')].within == window
    assert local.branches[Label('Cancel')].within is None
    drawn = render(proto)
    assert 'Sign(str) @30s' in drawn
    bare = alt[A, B](case('Sign', Text), case('Cancel')).close()
    assert render(bare) != drawn


def test_within_signature_preserves_fractional_precision() -> None:
    """Distinct positive windows must not collide in render / digest_of."""
    A, B = roles('A', 'B')
    half = render(
        msg[A, B]('Hi', Text, within=Deadline(timedelta(milliseconds=500))).close(),
    )
    almost = render(
        msg[A, B]('Hi', Text, within=Deadline(timedelta(milliseconds=999))).close(),
    )
    one = render(msg[A, B]('Hi', Text, within=Deadline(timedelta(seconds=1))).close())
    one_half = render(
        msg[A, B]('Hi', Text, within=Deadline(timedelta(milliseconds=1500))).close(),
    )
    assert '@0.5s' in half
    assert '@0.999s' in almost
    assert '@1s' in one
    assert '@1.5s' in one_half
    assert half != almost
    assert one != one_half
    # Sub-microsecond truncation is not the point — microsecond identity is.
    us = render(
        msg[A, B]('Hi', Text, within=Deadline(timedelta(microseconds=1))).close(),
    )
    assert '@0.000001s' in us


def test_merge_rejects_disagreement_on_deadline() -> None:
    """Full merge treats deadline like payload/intent: mismatch is illegal."""
    A, B, C = roles('A', 'B', 'C')
    # Observer C merges two continuations that both offer the same label from B
    # with disagreeing deadlines — construct via project of a bad global.
    # Global: A->B alt, both arms then B->C with same label different within.
    left = msg[B, C]('Reply', Text, within=Deadline(timedelta(seconds=1)))
    right = msg[B, C]('Reply', Text, within=Deadline(timedelta(seconds=5)))
    proto = alt[A, B](
        case('L') >> left,
        case('R') >> right,
    ).close()
    with pytest.raises(ProjectionError, match='deadline'):
        project(proto, C)


async def test_deadline_exceeded_cancels_every_participant() -> None:
    """Slow select raises DeadlineExceeded and cancel-broadcasts."""
    A, B, C = roles('A', 'B', 'C')
    proto = (
        msg[A, B]('Hi', Text, within=Deadline(timedelta(milliseconds=50)))
        >> msg[A, C]('Also', Text)
    ).close()
    a = Stub(
        A,
        project(proto, A),
        alts=[Choice(Label('Hi'), 'yo')],
        delay=0.5,
    )
    b = Stub(B, project(proto, B))
    c = Stub(C, project(proto, C))
    runtime = AgentRuntime(proto, [a, b, c])
    with pytest.raises(DeadlineExceeded) as caught:
        await runtime.run()
    assert 'A' in str(caught.value)
    for participant in (a, b, c):
        assert len(participant.cancelled) == 1
        assert participant.cancelled[0].reason.startswith('DeadlineExceeded')


async def test_protocol_without_deadline_is_unchanged() -> None:
    """No within on any branch: select is not timed; session finishes."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    trace = await AgentRuntime(proto, [a, b]).run()
    assert len(trace) == 1
    assert a.cancelled == []
    assert b.cancelled == []


def test_case_rejects_non_positive_within() -> None:
    with pytest.raises(ValueError, match='positive'):
        Deadline(timedelta(0))
    with pytest.raises(ValueError, match='positive'):
        Deadline(timedelta(seconds=-1))
