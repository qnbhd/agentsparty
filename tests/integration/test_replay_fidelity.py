"""Law 1: agent context is the same after a resume as after an uninterrupted run."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from hypothesis import given, settings

from agentsparty.agent import Agent
from agentsparty.brief import line
from agentsparty.journal.memory import MemoryJournal
from agentsparty.journal.types import ROOT_TRACK, StepIndex
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role, roles
from agentsparty.llm import Answer, ModelId, StructuredRequest
from agentsparty.machine import Machine, View
from agentsparty.participant import Cancelled, Choice, Envelope, Participant
from agentsparty.protocol import Label, Text, alt, case, msg, participants, project
from agentsparty.protocol.language.endpoint import EndpointBranchCase, EndpointEnd, EndpointType
from agentsparty.protocol.session import SessionType
from agentsparty.runtime import AgentRuntime
from agentsparty.toolbox import Toolbox, _Idle, tool
from tests._helpers import DeterministicPeer, ScriptedModel
from tests.journal.conftest import is_projectable
from tests.protocol.strategies import branching_protocols, linear_protocols

STUB = ModelId('stub', 'v1')


def _agent_role(proto: SessionType) -> Role:
    return min(participants(proto), key=lambda role: role.name)


async def _run_and_capture_last(
    proto: SessionType,
    agent_role: Role,
    journal: MemoryJournal,
) -> tuple[tuple, int]:
    """Run once; return (last model request messages, number of model calls)."""
    model = ScriptedModel()
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
    await AgentRuntime(proto, peers, journal=journal).run()
    if not model.requests:
        return (), 0
    return model.requests[-1].messages, len(model.requests)


async def _assert_resume_matches_live(proto: SessionType) -> None:
    if not is_projectable(proto):
        return
    roles_in = list(participants(proto))
    if not roles_in:
        return
    agent_role = _agent_role(proto)
    live_journal = MemoryJournal()
    live_messages, live_calls = await _run_and_capture_last(proto, agent_role, live_journal)
    if live_calls == 0:
        return
    script = live_journal.script()
    for n in range(script.length + 1):
        prefix_decisions = () if n == 0 else script.upto(StepIndex(ROOT_TRACK, n)).decisions
        prefix = MemoryJournal(prefix_decisions)
        resumed_messages, resumed_calls = await _run_and_capture_last(
            proto,
            agent_role,
            prefix,
        )
        if resumed_calls == 0:
            continue
        assert resumed_messages == live_messages, f'prefix n={n}: resumed messages differ from live'


@given(proto=linear_protocols(max_leaves=6))
@settings(deadline=None, max_examples=40)
async def test_agent_context_is_the_same_after_a_resume(proto: SessionType) -> None:
    """Law 1: every journal prefix yields the same last composition as live."""
    await _assert_resume_matches_live(proto)


@given(proto=branching_protocols(max_leaves=5))
@settings(deadline=None, max_examples=25)
async def test_agent_context_same_after_resume_branching(proto: SessionType) -> None:
    """Law 1 also holds for branching protocols once projectable."""
    await _assert_resume_matches_live(proto)


async def test_offer_and_recall_agree() -> None:
    """offer(e) and recall(e) leave equal observable state on Agent and Machine.

    Toolbox: live path is offer then select; replay path is offer then recall
    of the *answer*; both leave the toolbox waiting (idle).
    """
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    envelope = Envelope(A, B, Label('Hi'), 'hello')

    # Agent — offer and recall are the same transition:
    model = ScriptedModel()
    agent_offer = Agent(model=model, role=A, instructions='t', proto=proto)
    agent_recall = Agent(model=model, role=A, instructions='t', proto=proto)
    await agent_offer.offer(envelope)
    await agent_recall.recall(envelope)
    assert agent_offer.messages == agent_recall.messages

    # Machine — same:
    def decide(view: View) -> Choice:
        return Choice(min(view.offered), 'x')

    machine_offer = Machine(A, proto, decide)
    machine_recall = Machine(A, proto, decide)
    await machine_offer.offer(envelope)
    await machine_recall.recall(envelope)
    assert machine_offer.seen == machine_recall.seen

    # Toolbox — offer then select (live) and offer then recall of answer (replay)
    # both leave the slot idle:
    service = alt[A, B](case('Ask', Text) >> msg[B, A]('Reply', Text)).close()

    async def echo(value: str) -> Choice:
        return Choice(Label('Reply'), value)

    request = Envelope(A, B, Label('Ask'), 'q')
    answer = Envelope(B, A, Label('Reply'), 'q')

    live = Toolbox(B, service, [tool('Ask', Text, echo)])
    await live.offer(request)
    branches = NonEmptyMap.of_pairs(
        [(Label('Reply'), EndpointBranchCase(Label('Reply'), Text, EndpointEnd()))],
    )
    await live.select(A, branches)

    replayed = Toolbox(B, service, [tool('Ask', Text, echo)])
    await replayed.offer(request)
    await replayed.recall(answer)
    # both idle (same observable waiting state after the full live/replay path):
    assert isinstance(live._awaiting, _Idle)
    assert isinstance(replayed._awaiting, _Idle)


async def test_select_leaves_the_state_recall_would() -> None:
    """After select, messages equal a fresh agent after recall of the envelope."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    reply = json.dumps({'alt': {'label': 'Hi', 'payload': 'hello'}})
    model = _FixedModel(reply)
    agent = Agent(model=model, role=A, instructions='t', proto=proto)
    branches = NonEmptyMap.of_pairs(
        [(Label('Hi'), EndpointBranchCase(Label('Hi'), Text, EndpointEnd()))],
    )
    chosen = await agent.select(B, branches)
    envelope = Envelope(A, B, chosen.branch.label, chosen.payload)

    fresh = Agent(model=model, role=A, instructions='t', proto=proto)
    await fresh.recall(envelope)
    assert agent.messages == fresh.messages
    assert agent.messages == [line(A, envelope)]


@dataclass
class _FixedModel:
    reply: str
    requests: list[StructuredRequest] = field(default_factory=list)

    async def complete(self, request: StructuredRequest) -> Answer:
        self.requests.append(request)
        return Answer(self.reply, STUB)


async def test_a_refinement_is_checked_on_replay() -> None:
    """A refined codec is re-checked when a journalled raw is recalled."""
    from agentsparty.journal.types import ROOT_TRACK, Decision, StepIndex
    from agentsparty.kernel.errors import JournalError
    from agentsparty.protocol import refine

    A, B = roles('A', 'B')
    requirement = 'under 3 words'
    refined = refine(Text, requirement, lambda s: len(s.split()) < 3)
    proto = msg[A, B]('Hi', refined).close()

    # A journal recorded under the refined codec with a valid raw replays:
    good = MemoryJournal()
    good.append(
        Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('Hi'), refined.name, 'ok'),
    )

    @dataclass
    class Peer:
        role: Role
        endpoint_contract: EndpointType
        cancelled: list[Cancelled] = field(default_factory=list)

        async def select(self, receiver, branches):
            raise RuntimeError('peer should not select')

        async def offer(self, envelope: Envelope) -> None:
            pass

        async def recall(self, envelope: Envelope) -> None:
            pass

        async def cancel(self, notice: Cancelled) -> None:
            self.cancelled.append(notice)

    peer = Peer(B, project(proto, B))
    agent = Agent(model=ScriptedModel(), role=A, instructions='t', proto=proto)
    await AgentRuntime(proto, [agent, peer], journal=good).run()

    # A journal whose raw violates the refinement is refused in _recall:
    bad = MemoryJournal()
    bad.append(
        Decision(
            StepIndex(ROOT_TRACK, 1),
            A,
            B,
            Label('Hi'),
            refined.name,
            'one two three four',
        ),
    )
    agent2 = Agent(model=ScriptedModel(), role=A, instructions='t', proto=proto)
    with pytest.raises(JournalError, match=requirement):
        await AgentRuntime(proto, [agent2, Peer(B, project(proto, B))], journal=bad).run()
