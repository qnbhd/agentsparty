"""Law 5: model transformers are invisible to the protocol."""

from __future__ import annotations

from hypothesis import given, settings

from agentsparty.agent import Agent
from agentsparty.journal.memory import MemoryJournal
from agentsparty.journal.types import Decision
from agentsparty.kernel.role import Role
from agentsparty.llm import (
    NO_REASONING,
    Fallback,
    Profiled,
    Retrying,
    Unavailable,
)
from agentsparty.participant import Envelope, Participant
from agentsparty.protocol import participants, project
from agentsparty.protocol.session import SessionType
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing.memory import MemoryTracer
from tests._helpers import DeterministicPeer, ScriptedModel
from tests.journal.conftest import is_projectable
from tests.protocol.strategies import branching_protocols, linear_protocols


def _agent_role(proto: SessionType) -> Role:
    return min(participants(proto), key=lambda role: role.name)


async def _run(
    proto: SessionType,
    model,
) -> tuple[list[Envelope], tuple[Decision, ...], list[str]]:
    """Run *proto* with *model* on the agent role; return trace, journal, tracer names."""
    agent_role = _agent_role(proto)
    journal = MemoryJournal()
    tracer = MemoryTracer()
    agent: Agent[object] = Agent(
        model=model,
        role=agent_role,
        instructions='t',
        proto=proto,
    )
    peers: list[Participant] = [agent]
    peers.extend(
        DeterministicPeer(role, project(proto, role))
        for role in participants(proto)
        if role != agent_role
    )
    envelopes = await AgentRuntime(proto, peers, journal=journal, tracer=tracer).run()
    return list(envelopes), journal.script().decisions, tracer.names()


async def _assert_transformers_are_transparent(proto: SessionType) -> None:
    if not is_projectable(proto):
        return
    if not list(participants(proto)):
        return
    bare = ScriptedModel()
    bare_trace, bare_journal, bare_names = await _run(proto, bare)
    if 'model.called' not in bare_names:
        return

    slept: list[float] = []

    async def record_sleep(seconds: float) -> None:
        slept.append(seconds)

    wrapped = Fallback(
        Unavailable(),
        Retrying(Profiled(ScriptedModel(), NO_REASONING), sleep=record_sleep),
    )
    wrapped_trace, wrapped_journal, wrapped_names = await _run(proto, wrapped)

    assert bare_trace == wrapped_trace
    assert bare_journal == wrapped_journal
    # Tracer may differ (e.g. effort on ModelCalled) — that is Law 5's content.
    assert bare_names  # session ran
    assert wrapped_names


@given(proto=linear_protocols(max_leaves=5))
@settings(deadline=None, max_examples=30)
async def test_wrapping_the_model_changes_nothing_the_protocol_sees_linear(
    proto: SessionType,
) -> None:
    """Law 5: journal and envelope trace equal under nested transformers."""
    await _assert_transformers_are_transparent(proto)


@given(proto=branching_protocols(max_leaves=4))
@settings(deadline=None, max_examples=20)
async def test_wrapping_the_model_changes_nothing_the_protocol_sees_branching(
    proto: SessionType,
) -> None:
    """Law 5 for branching protocols once projectable."""
    await _assert_transformers_are_transparent(proto)
