"""Agent select uses selection_codec once."""

from __future__ import annotations

import json

from hypothesis import given

from agentsparty.agent import Agent
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import roles
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol import Label, Nothing, Text, msg
from agentsparty.protocol.language.core import selection_codec
from agentsparty.protocol.language.endpoint import EndpointBranchCase, EndpointEnd
from tests._helpers import ReplyingModel, cancellable_envelopes


@given(
    envelopes=cancellable_envelopes(),
)
async def test_cancel_returns_an_agent_to_its_initial_memory(
    envelopes: list[Envelope],
) -> None:
    """L8-a: a cancelled agent holds the brief it started with, twice or once."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    agent = Agent(model=ReplyingModel('{}'), role=A, instructions='t', proto=proto)
    initial = agent.messages
    for envelope in envelopes:
        await agent.offer(envelope)
    notice = Cancelled('StepLimitError: no budget')
    await agent.cancel(notice)
    assert agent.messages == initial
    await agent.cancel(notice)
    assert agent.messages == initial


async def test_agent_select_returns_chosen() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    reply = json.dumps({'alt': {'label': 'Hi', 'payload': 'hello'}})
    model = ReplyingModel(reply)
    agent = Agent(model=model, role=A, instructions='t', proto=proto)
    branches = NonEmptyMap.of_pairs(
        [(Label('Hi'), EndpointBranchCase(Label('Hi'), Text, EndpointEnd()))],
    )
    chosen = await agent.select(B, branches)
    assert chosen.branch.label == Label('Hi')
    assert chosen.payload == 'hello'
    assert model.requests[0].schema == dict(selection_codec(branches).schema)


def test_selection_schema_single_arm() -> None:
    branches = NonEmptyMap.of_pairs(
        [(Label('Quit'), EndpointBranchCase(Label('Quit'), Nothing, EndpointEnd()))],
    )
    # Single-arm alt is not wrapped in anyOf — wire shape from golden capture.
    expected = {
        'type': 'object',
        'properties': {
            'alt': {
                'type': 'object',
                'properties': {
                    'label': {'type': 'string', 'enum': ['Quit']},
                    'payload': {'type': 'null'},
                },
                'required': ['label', 'payload'],
                'additionalProperties': False,
            },
        },
        'required': ['alt'],
        'additionalProperties': False,
    }
    assert dict(selection_codec(branches).schema) == expected


async def test_the_prompt_lists_intents() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Design', Text).close()
    reply = json.dumps({'alt': {'label': 'Design', 'payload': 'ok'}})
    model = ReplyingModel(reply)
    agent = Agent(model=model, role=A, instructions='t', proto=proto)
    branches = NonEmptyMap.of_pairs(
        [
            (
                Label('Design'),
                EndpointBranchCase(Label('Design'), Text, EndpointEnd(), 'a diagram'),
            ),
            (Label('Ok'), EndpointBranchCase(Label('Ok'), Nothing, EndpointEnd())),
        ],
    )
    await agent.select(B, branches)
    prompt = model.requests[0].messages[-1].content
    assert '- Design: a diagram' in prompt
    assert '- Ok' in prompt
    assert '- Ok:' not in prompt  # bare label, no empty intent suffix


async def test_the_prompt_is_still_not_remembered() -> None:
    A, B = roles('A', 'B')
    intent = 'a PlantUML component diagram'
    proto = msg[A, B]('Design', Text, intent).close()
    reply = json.dumps({'alt': {'label': 'Design', 'payload': 'ok'}})
    model = ReplyingModel(reply)
    agent = Agent(model=model, role=A, instructions='t', proto=proto)
    branches = NonEmptyMap.of_pairs(
        [
            (
                Label('Design'),
                EndpointBranchCase(Label('Design'), Text, EndpointEnd(), intent),
            ),
        ],
    )
    await agent.select(B, branches)
    remembered = '\n'.join(message.content for message in agent.messages)
    assert intent not in remembered
