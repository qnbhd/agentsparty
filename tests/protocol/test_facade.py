"""Facade A: Case-as-declaration, codec_of/record, Cast, fragment boundaries."""

from __future__ import annotations

import json

import pytest

from agentsparty.agent import agent
from agentsparty.human import Human, ScriptedHumanIo, human, script
from agentsparty.kernel.role import roles
from agentsparty.llm import ScriptedLanguageModel
from agentsparty.machine import View, machine
from agentsparty.participant import Choice, says
from agentsparty.protocol import (
    Integer,
    Label,
    Nothing,
    Text,
    case,
    codec_of,
    equal_session,
    list_of,
    msg,
    project,
    project_all,
    record,
    render,
)
from agentsparty.runtime import AgentRuntime, Cast
from agentsparty.toolbox import Toolbox, reply, service, tool_for


def test_msg_accepts_case_without_restating_codec() -> None:
    A, B = roles('A', 'B')
    Hi = case('Hi', Text, 'a greeting')
    assert equal_session(
        msg[A, B](Hi).close(),
        msg[A, B]('Hi', Text, 'a greeting').close(),
    )


def test_tool_and_reply_accept_case() -> None:
    A, B = roles('A', 'B')
    Measure = case('Measure', Text)
    Length = case('Length', Integer)
    proto = (msg[A, B](Measure) >> msg[B, A](Length)).close()

    async def measure(draft: str) -> Choice:
        return reply(Length, len(draft))

    box = Toolbox(B, proto, [tool_for(Measure, measure)])
    assert box.role is B


def test_says_builds_alt_from_case() -> None:
    Hi = case('Hi', Text)
    assert says(Hi, 'hello') == Choice(Label('Hi'), 'hello')
    assert says('Hi', 'hello') == Choice(Label('Hi'), 'hello')


def test_codec_of_primitives_and_containers() -> None:
    assert codec_of(str) is Text
    assert codec_of(int) is Integer
    assert codec_of(None) is Nothing
    assert codec_of(list[str]).name == list_of(Text).name
    assert codec_of(Text) is Text


def test_codec_of_rejects_unknown_annotation() -> None:
    with pytest.raises(TypeError, match=r'unsupported annotation'):
        codec_of(complex)


def test_case_accepts_annotation_via_codec_of() -> None:
    A, B = roles('A', 'B')
    assert equal_session(
        msg[A, B](case('Hi', str)).close(),
        msg[A, B](case('Hi', Text)).close(),
    )


def test_record_is_closed_object() -> None:
    Component = record('Component', name=str, code=str)
    assert Component.schema['additionalProperties'] is False
    assert Component.schema['required'] == ['name', 'code']
    value = Component.decode({'name': 'hero', 'code': 'div'})
    assert value == {'name': 'hero', 'code': 'div'}


def test_record_rejects_missing_field() -> None:
    Component = record('Component', name=str, code=str)
    with pytest.raises(Exception, match=r'missing'):
        Component.decode({'name': 'hero'})


def test_unclosed_fragment_works_at_runtime_boundary() -> None:
    A, B = roles('A', 'B')
    fragment = msg[A, B]('Hi', Text)
    a = Human(A, fragment.close(), ScriptedHumanIo([Choice(Label('Hi'), 'x')]))
    b = Human(B, fragment.close(), ScriptedHumanIo([]))
    trace = AgentRuntime(fragment, [a, b]).run_sync()
    assert trace[0].payload == 'x'


def test_unclosed_fragment_works_at_render_and_project() -> None:
    A, B = roles('A', 'B')
    fragment = msg[A, B]('Hi', Text)
    assert 'Hi' in render(fragment)
    project(fragment, A)
    assert len(project_all(fragment)) == 2


def test_cast_play_run_totality() -> None:
    A, B = roles('A', 'B')
    Hi = case('Hi', Text)
    Ack = case('Ack', Text)
    proto = msg[A, B](Hi) >> msg[B, A](Ack)
    cast = (
        Cast(proto)
        .play(A, human(script(says(Hi, 'ping'))))
        .play(B, human(script(says(Ack, 'pong'))))
    )
    trace = cast.run_sync()
    assert [e.payload for e in trace] == ['ping', 'pong']


def test_cast_rejects_unknown_role() -> None:
    A, B, C = roles('A', 'B', 'C')
    proto = msg[A, B]('Hi', Text).close()
    with pytest.raises(ValueError, match=r'not in the protocol'):
        Cast(proto).play(C, human(script()))


def test_cast_run_names_missing_roles() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    partial = Cast(proto).play(A, human(script(says('Hi', 'x'))))
    with pytest.raises(ValueError, match=r'missing participants.*B'):
        partial.run_sync()


def test_cast_with_agent_machine_service() -> None:
    User, Planner, Tools = roles('User', 'Planner', 'Tools')
    Ask = case('ask', Text)
    Search = case('search', Text)
    Hits = case('hits', list_of(Text))
    Answer = case('answer', Text)
    proto = (
        msg[User, Planner](Ask)
        >> msg[Planner, Tools](Search)
        >> msg[Tools, Planner](Hits)
        >> msg[Planner, User](Answer)
    )

    async def search(query: str) -> Choice:
        return reply(Hits, [f'{query}-1'])

    def decide(view: View) -> Choice:
        labels = {str(label) for label in view.offered}
        if 'search' in labels:
            return says(Search, 'mpst')
        return says(Answer, 'done')

    payload = json.dumps({'alt': {'label': 'ask', 'payload': 'what?'}})
    cast = (
        Cast(proto)
        .play(User, agent(ScriptedLanguageModel([payload]), 'ask'))
        .play(Planner, machine(decide))
        .play(Tools, service(tool_for(Search, search)))
    )
    trace = cast.run_sync()
    assert [e.label.name for e in trace] == ['ask', 'search', 'hits', 'answer']


def test_case_declaration_zero_repeated_string_labels() -> None:
    """Label-heavy offline shape: every message is a Case constant."""
    Editor, Bard, Meter = roles('Editor', 'Bard', 'Meter')
    Topic = case('Topic', Text, 'What the post is about.')
    Measure = case('Measure', Text, 'The draft to measure.')
    Length = case('Length', Integer, 'Character count.')
    proto = (
        msg[Editor, Bard](Topic) >> msg[Bard, Meter](Measure) >> msg[Meter, Bard](Length)
    ).close()
    # No string labels at use sites — only Case objects.
    assert 'Topic' in render(proto)

    async def measure(draft: str) -> Choice:
        return reply(Length, len(draft))

    Toolbox(Meter, proto, [tool_for(Measure, measure)])
    assert says(Topic, 'x').label.name == 'Topic'
