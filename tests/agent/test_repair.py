"""Bounded model repair: corrections stay out of brief and journal."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.agent import DEFAULT_REPAIR, NO_REPAIR, Agent, Repair
from agentsparty.journal.memory import MemoryJournal
from agentsparty.kernel.errors import PayloadError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role, roles
from agentsparty.llm import Answer, ModelId, StructuredRequest
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.protocol.language.endpoint import EndpointBranchCase, EndpointEnd, EndpointType
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing import MemoryTracer, ModelCorrected, SessionFinished, new_scope

STUB = ModelId('stub', 'v1')


@dataclass
class ScriptedReplies:
    """Model that returns answers from a fixed list, then the last one forever."""

    replies: list[str]
    requests: list[StructuredRequest] = field(default_factory=list)
    index: int = 0

    async def complete(self, request: StructuredRequest) -> Answer:
        self.requests.append(request)
        if self.index < len(self.replies):
            reply = self.replies[self.index]
            self.index += 1
            return Answer(reply, STUB)
        return Answer(self.replies[-1], STUB)


@dataclass
class AlwaysBad:
    """Model that always returns unusable text."""

    requests: list[StructuredRequest] = field(default_factory=list)

    async def complete(self, request: StructuredRequest) -> Answer:
        self.requests.append(request)
        return Answer('not-json', STUB)


def _valid_hi() -> str:
    return json.dumps({'alt': {'label': 'Hi', 'payload': 'hello'}})


def _agent(model, *, repair: Repair = DEFAULT_REPAIR) -> Agent:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    return Agent(model=model, role=A, instructions='t', proto=proto, repair=repair)


def _branches():
    return NonEmptyMap.of_pairs(
        [(Label('Hi'), EndpointBranchCase(Label('Hi'), Text, EndpointEnd()))],
    )


async def test_a_bad_answer_is_corrected_once() -> None:
    model = ScriptedReplies(['garbage', _valid_hi()])
    agent = _agent(model)
    _A, B = roles('A', 'B')
    chosen = await agent.select(B, _branches())
    assert chosen.payload == 'hello'
    assert len(model.requests) == 2
    second = model.requests[1].messages
    assert second[-2].role == 'assistant'
    assert second[-2].content == 'garbage'
    assert 'could not be used' in second[-1].content


@given(n=st.integers(0, 4))
async def test_repair_budget_is_respected(n: int) -> None:
    model = AlwaysBad()
    agent = _agent(model, repair=Repair(n))
    _A, B = roles('A', 'B')
    with pytest.raises(PayloadError):
        await agent.select(B, _branches())
    assert len(model.requests) == n + 1


async def test_no_repair_matches_todays_behaviour() -> None:
    model = AlwaysBad()
    agent = _agent(model, repair=NO_REPAIR)
    _A, B = roles('A', 'B')
    with pytest.raises(PayloadError):
        await agent.select(B, _branches())
    assert len(model.requests) == 1


async def test_repair_leaves_no_trace_in_the_brief() -> None:
    model = ScriptedReplies(['garbage', _valid_hi()])
    agent = _agent(model)
    _A, B = roles('A', 'B')
    before = list(agent.messages)
    await agent.select(B, _branches())
    after = agent.messages
    assert len(after) == len(before) + 1
    assert after[-1].role == 'assistant'
    assert 'Sent Hi' in after[-1].content
    assert 'garbage' not in str(after)
    assert 'could not be used' not in str(after)


async def test_repair_is_not_journalled() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    model = ScriptedReplies(['garbage', _valid_hi()])
    agent = Agent(model=model, role=A, instructions='t', proto=proto)
    journal = MemoryJournal()

    @dataclass
    class Peer:
        role: Role
        endpoint_contract: EndpointType
        received: list = field(default_factory=list)
        cancelled: list[Cancelled] = field(default_factory=list)

        async def select(self, receiver, branches):
            raise RuntimeError('peer should not select')

        async def offer(self, envelope: Envelope) -> None:
            self.received.append(envelope)

        async def recall(self, envelope: Envelope) -> None:
            pass

        async def cancel(self, notice: Cancelled) -> None:
            self.cancelled.append(notice)

    peer = Peer(B, project(proto, B))
    await AgentRuntime(proto, [agent, peer], journal=journal).run()
    assert journal.script().length == 1


def test_negative_repair_is_rejected() -> None:
    with pytest.raises(ValueError, match='non-negative'):
        Repair(-1)


async def test_model_corrected_is_traced() -> None:
    model = ScriptedReplies(['garbage', _valid_hi()])
    agent = _agent(model)
    _A, B = roles('A', 'B')
    mem = MemoryTracer()
    with new_scope(mem).open(SessionFinished(0)):
        await agent.select(B, _branches())
    corrected = [event.signal for event in mem.events if isinstance(event.signal, ModelCorrected)]
    assert len(corrected) == 1


def _refined_branches(requirement: str = 'under 3 words'):
    from agentsparty.protocol import refine

    refined = refine(Text, requirement, lambda s: len(s.split()) < 3)
    return NonEmptyMap.of_pairs(
        [(Label('Hi'), EndpointBranchCase(Label('Hi'), refined, EndpointEnd()))],
    )


def _alt(payload: str) -> str:
    return json.dumps({'alt': {'label': 'Hi', 'payload': payload}})


async def test_a_refinement_failure_is_repaired() -> None:
    requirement = 'under 3 words'
    model = ScriptedReplies([_alt('one two three four'), _alt('ok now')])
    agent = _agent(model)
    _A, B = roles('A', 'B')
    chosen = await agent.select(B, _refined_branches(requirement))
    assert chosen.payload == 'ok now'
    assert len(model.requests) == 2
    assert requirement in model.requests[1].messages[-1].content


async def test_a_refinement_failure_exhausts_the_budget() -> None:
    model = ScriptedReplies([_alt('one two three four')])
    agent = _agent(model, repair=NO_REPAIR)
    _A, B = roles('A', 'B')
    with pytest.raises(PayloadError, match='under 3 words'):
        await agent.select(B, _refined_branches())
    assert len(model.requests) == 1
