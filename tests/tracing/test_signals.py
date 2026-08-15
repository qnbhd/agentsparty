"""Describe totality and stable names for every signal kind."""

from __future__ import annotations

from agentsparty.kernel.role import roles
from agentsparty.llm import Answer, ModelId
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol import Label, Text, msg
from agentsparty.tracing.signals import (
    Delivered,
    Failed,
    ModelAnswered,
    ModelCalled,
    ModelCorrected,
    ModelStreamed,
    Recalled,
    Selected,
    SessionCancelled,
    SessionFinished,
    SessionStarted,
    Signal,
    StepStarted,
    ToolAnswered,
    ToolCalled,
    Unfolded,
    describe,
)

STUB = ModelId('stub', 'v1')


def all_signal_instances() -> list[tuple[Signal, str]]:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    envelope = Envelope(sender=A, receiver=B, label=Label('Hi'), payload='yo')
    return [
        (SessionStarted(proto, (A, B)), 'session.started'),
        (SessionFinished(1), 'session.finished'),
        (SessionCancelled(Cancelled('StepLimitError: no budget')), 'session.cancelled'),
        (StepStarted(A, B, (Label('Hi'),)), 'step.started'),
        (Selected(Label('Hi'), 'yo'), 'step.selected'),
        (Recalled(Label('Hi'), 'yo'), 'step.recalled'),
        (Delivered(envelope), 'step.delivered'),
        (Unfolded('t', 3), 'session.unfolded'),
        (ModelCalled('agent_alt', 'low', 1), 'model.called'),
        (ModelAnswered(Answer('{"ok": true}', STUB)), 'model.answered'),
        (ModelStreamed('ok'), 'model.streamed'),
        (ModelCorrected('bad payload'), 'model.corrected'),
        (ToolCalled(Label('search')), 'tool.called'),
        (ToolAnswered(Label('hits')), 'tool.answered'),
        (Failed('ValueError: boom'), 'failed'),
    ]


def test_describe_totality_and_stable_names() -> None:
    """Every signal kind yields a non-empty stable name."""
    for signal, expected_name in all_signal_instances():
        description = describe(signal)
        assert description.name
        assert description.name == expected_name
        for value in description.fields.values():
            str(value)
            repr(value)


def test_describe_flattens_roles_and_labels() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    started = describe(SessionStarted(proto, (A, B)))
    assert started.fields['participants'] == 'A,B'
    assert 'A' in str(started.fields['protocol'])

    step = describe(StepStarted(A, B, (Label('Hi'), Label('Bye'))))
    assert step.fields['sender'] == 'A'
    assert step.fields['receiver'] == 'B'
    assert step.fields['offered'] == 'Hi,Bye'
