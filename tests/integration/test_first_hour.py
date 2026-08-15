"""First-hour DX gates from plan 0009 (A1-A5, binding, budget, scripted model)."""

from __future__ import annotations

import json

import pytest

from agentsparty.agent import Agent
from agentsparty.human import Human, ScriptedHumanIo
from agentsparty.kernel.budget import Allowance
from agentsparty.kernel.errors import (
    ModelRefused,
    ProjectionError,
    RecursionLimitError,
    SelectionError,
    StepLimitError,
)
from agentsparty.kernel.role import roles
from agentsparty.llm import ScriptedLanguageModel
from agentsparty.participant import Choice
from agentsparty.protocol import Label, Text, alt, case, msg, project, rec, var
from agentsparty.runtime import AgentRuntime


def test_unclosed_fragment_works_at_boundary() -> None:
    """First-hour DX: a fragment need not be closed by hand at the boundary."""
    A, B = roles('A', 'B')
    fragment = msg[A, B]('X', Text) >> msg[B, A]('Y', Text)
    client = Human(A, fragment.close(), ScriptedHumanIo([Choice(Label('X'), 'x')]))
    server = Human(
        B,
        fragment.close(),
        ScriptedHumanIo([Choice(Label('Y'), 'y')]),
    )
    # AgentRuntime accepts the open fragment and closes it itself.
    trace = AgentRuntime(fragment, [client, server]).run_sync()
    assert [e.payload for e in trace] == ['x', 'y']


def test_projection_error_names_role_and_branch_labels() -> None:
    A, B, C = roles('A', 'B', 'C')
    proto = alt[A, B](
        case('Yes') >> msg[A, C]('Y', Text),
        case('No') >> msg[C, A]('N', Text),
    ).close()
    with pytest.raises(ProjectionError) as caught:
        project(proto, C)
    text = str(caught.value)
    assert "role 'C'" in text
    assert "'Yes'" in text
    assert "'No'" in text
    assert 'A -> B' in text
    assert 'branch' in text.lower()


def test_binding_missing_participant_names_roles() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    only_a = Human(A, proto, ScriptedHumanIo([Choice(Label('Hi'), 'x')]))
    with pytest.raises(ValueError, match=r'missing participants.*B'):
        AgentRuntime(proto, [only_a])


def test_binding_extra_participant_names_roles() -> None:
    A, B, C = roles('A', 'B', 'C')
    proto = msg[A, B]('Hi', Text).close()
    humans = [
        Human(A, proto, ScriptedHumanIo([Choice(Label('Hi'), 'x')])),
        Human(B, proto, ScriptedHumanIo([])),
        Human(C, proto, ScriptedHumanIo([])),
    ]
    with pytest.raises(ValueError, match=r'unexpected participants.*C'):
        AgentRuntime(proto, humans)


def test_binding_duplicate_participant_names_role() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a1 = Human(A, proto, ScriptedHumanIo([Choice(Label('Hi'), 'x')]))
    a2 = Human(A, proto, ScriptedHumanIo([Choice(Label('Hi'), 'y')]))
    b = Human(B, proto, ScriptedHumanIo([]))
    with pytest.raises(ValueError, match=r"duplicate participant for role 'A'"):
        AgentRuntime(proto, [a1, a2, b])


def test_scripted_human_unknown_label_is_selection_error() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    human = Human(A, proto, ScriptedHumanIo([Choice(Label('Nope'), 'x')]))
    peer = Human(B, proto, ScriptedHumanIo([]))
    with pytest.raises(SelectionError, match=r'chosen label Nope not on offer: Hi'):
        AgentRuntime(proto, [human, peer]).run_sync()


def test_scripted_human_exhausted_is_selection_error() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    human = Human(A, proto, ScriptedHumanIo([]))
    peer = Human(B, proto, ScriptedHumanIo([]))
    with pytest.raises(SelectionError, match=r'exhausted'):
        AgentRuntime(proto, [human, peer]).run_sync()


def test_step_limit_message_mentions_allowance() -> None:
    A, B = roles('A', 'B')
    proto = (msg[A, B]('One', Text) >> msg[A, B]('Two', Text)).close()
    a = Human(
        A,
        proto,
        ScriptedHumanIo([Choice(Label('One'), '1'), Choice(Label('Two'), '2')]),
    )
    b = Human(B, proto, ScriptedHumanIo([]))
    runtime = AgentRuntime(proto, [a, b], allowance=Allowance(steps=1))
    with pytest.raises(StepLimitError, match=r'step allowance exhausted'):
        runtime.run_sync()


def test_recursion_limit_message_mentions_unfolding() -> None:
    A, B = roles('A', 'B')
    body = msg[A, B]('Tick', Text) >> var('loop')
    proto = rec('loop', body).close()
    a = Human(A, proto, ScriptedHumanIo([Choice(Label('Tick'), '1')] * 5))
    b = Human(B, proto, ScriptedHumanIo([]))
    runtime = AgentRuntime(proto, [a, b], allowance=Allowance(unfoldings=1, steps=10))
    with pytest.raises(RecursionLimitError, match=r'unfolding allowance exhausted'):
        runtime.run_sync()


def test_run_sync_delivers_scripted_session() -> None:
    A, B = roles('A', 'B')
    proto = (msg[A, B]('Request', Text) >> msg[B, A]('Reply', Text)).close()
    client = Human(A, proto, ScriptedHumanIo([Choice(Label('Request'), 'ping')]))
    server = Human(B, proto, ScriptedHumanIo([Choice(Label('Reply'), 'pong')]))
    trace = AgentRuntime(proto, [client, server]).run_sync()
    assert [(e.sender.name, e.receiver.name, e.payload) for e in trace] == [
        ('A', 'B', 'ping'),
        ('B', 'A', 'pong'),
    ]


def test_scripted_language_model_drives_agent_without_network() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Note', Text).close()
    payload = json.dumps({'alt': {'label': 'Note', 'payload': 'hello'}})
    model = ScriptedLanguageModel([payload])
    agent = Agent(model, A, 'send the note', proto)
    peer = Human(B, proto, ScriptedHumanIo([]))
    trace = AgentRuntime(proto, [agent, peer]).run_sync()
    assert len(trace) == 1
    assert trace[0].payload == 'hello'
    assert model.requests  # completed was called


async def test_scripted_language_model_exhaustion_is_model_refused() -> None:
    model = ScriptedLanguageModel([])
    request = __import__(
        'agentsparty.llm',
        fromlist=['StructuredRequest'],
    ).StructuredRequest(
        instructions='x',
        messages=(),
        schema_name='Choice',
        schema={'type': 'object'},
        effort='none',
    )

    async def _call() -> None:
        await model.complete(request)

    with pytest.raises(ModelRefused, match=r'exhausted'):
        await _call()
