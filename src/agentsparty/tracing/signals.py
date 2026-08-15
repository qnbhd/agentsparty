"""Domain signals: the closed catalogue of things a session can observe."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias

from typing_extensions import assert_never

from agentsparty.kernel.role import Role
from agentsparty.llm.types import Answer, Effort
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol.language.core import Label
from agentsparty.protocol.render import render
from agentsparty.protocol.session.types import SessionType

__all__ = [
    'Delivered',
    'Description',
    'Failed',
    'Forked',
    'ModelAnswered',
    'ModelCalled',
    'ModelCorrected',
    'ModelStreamed',
    'Recalled',
    'Selected',
    'SessionCancelled',
    'SessionFinished',
    'SessionStarted',
    'Signal',
    'StepStarted',
    'ToolAnswered',
    'ToolCalled',
    'Unfolded',
    'describe',
]


@dataclass(frozen=True, slots=True)
class SessionStarted:
    """A runtime began executing a choreography; opens the session span."""

    protocol: SessionType
    participants: tuple[Role, ...]


@dataclass(frozen=True, slots=True)
class SessionFinished:
    """The choreography reached ``end``; terminates the session span."""

    messages: int


@dataclass(frozen=True, slots=True)
class SessionCancelled:
    """The session ended anywhere other than ``end``; every participant heard.

    The second way a session span can terminate, and the sibling of
    :class:`SessionFinished`: exactly one of the two closes a session.
    ``Failed`` is not that terminator — it says a span's body raised, which is
    true of model and tool spans too, and says nothing about the participants.
    """

    notice: Cancelled


@dataclass(frozen=True, slots=True)
class StepStarted:
    """One interaction node is about to run; opens a step span."""

    sender: Role
    receiver: Role
    offered: tuple[Label, ...]


@dataclass(frozen=True, slots=True)
class Selected:
    """The sender picked a branch and produced its payload."""

    label: Label
    payload: object


@dataclass(frozen=True, slots=True)
class Recalled:
    """A recorded alt was replayed from a journal; nobody was asked."""

    label: Label
    payload: object


@dataclass(frozen=True, slots=True)
class Delivered:
    """The receiver accepted the envelope; terminates the step span."""

    envelope: Envelope


@dataclass(frozen=True, slots=True)
class Unfolded:
    """A recursion binder was unfolded once; point event in the session span."""

    name: str
    remaining: int | None


@dataclass(frozen=True, slots=True)
class Forked:
    """The session split into independent tracks; a point event."""

    branches: int


@dataclass(frozen=True, slots=True)
class ModelCalled:
    """A language-model call started; opens a model span."""

    schema_name: str
    effort: Effort
    messages: int


@dataclass(frozen=True, slots=True)
class ModelAnswered:
    """The model returned its answer; terminates the model span."""

    answer: Answer


@dataclass(frozen=True, slots=True)
class ModelStreamed:
    """A fragment of the model's answer arrived; a point event in a model span.

    Emitted by an adapter that reads a provider's stream. It is an
    observation and nothing else: the protocol still sees one answer, decoded
    once, because half a JSON payload decodes to nothing.
    """

    delta: str


@dataclass(frozen=True, slots=True)
class ToolCalled:
    """A toolbox started running a tool; opens a tool span."""

    tool: Label


@dataclass(frozen=True, slots=True)
class ToolAnswered:
    """The tool named the reply branch it answers with; ends the tool span."""

    reply: Label


@dataclass(frozen=True, slots=True)
class ModelCorrected:
    """A model answer would not decode and the model was asked again."""

    error: str


@dataclass(frozen=True, slots=True)
class Failed:
    """The span's body raised; terminates any span."""

    error: str


_SessionSignal: TypeAlias = SessionStarted | SessionFinished | SessionCancelled | Unfolded | Forked
_StepSignal: TypeAlias = StepStarted | Selected | Recalled | Delivered
_ModelSignal: TypeAlias = ModelCalled | ModelAnswered | ModelStreamed | ModelCorrected
_ToolSignal: TypeAlias = ToolCalled | ToolAnswered | Failed
Signal: TypeAlias = _SessionSignal | _StepSignal | _ModelSignal | _ToolSignal
"""Closed union of every domain signal the runtime can emit."""


@dataclass(frozen=True, slots=True)
class Description:
    """A signal rendered as a stable name plus flat, printable fields."""

    name: str
    fields: Mapping[str, object]


# Every name produced below is classified into a facet in agentsparty.tracing.facet.
# A new signal that is not classified there fails tests/tracing/test_facet.py.
def describe(signal: Signal) -> Description:
    """Render *signal* as a stable name plus flat, printable fields.

    Args:
        signal: The signal to describe.

    Returns:
        The signal's stable name and its fields, in declaration order.
    """
    match signal:
        case SessionStarted() | SessionFinished() | SessionCancelled() | Unfolded() | Forked():
            return _describe_session(signal)
        case StepStarted() | Selected() | Recalled() | Delivered():
            return _describe_step(signal)
        case ModelCalled() | ModelAnswered() | ModelStreamed() | ModelCorrected():
            return _describe_model(signal)
        case ToolCalled() | ToolAnswered() | Failed():
            return _describe_tool(signal)
        case _:  # pragma: no cover
            assert_never(signal)


def _describe_session(signal: _SessionSignal) -> Description:
    match signal:
        case SessionStarted(protocol=protocol, participants=participants):
            return Description(
                'session.started',
                {
                    'protocol': render(protocol),
                    'participants': ','.join(role.name for role in participants),
                },
            )
        case SessionFinished(messages=messages):
            return Description('session.finished', {'messages': messages})
        case SessionCancelled(notice=notice):
            return Description('session.cancelled', {'reason': notice.reason})
        case Unfolded(name=name, remaining=remaining):
            return Description(
                'session.unfolded',
                {'name': name, 'remaining': remaining},
            )
        case Forked(branches=branches):
            return Description('session.forked', {'branches': branches})
        case _:  # pragma: no cover
            assert_never(signal)


def _describe_step(signal: _StepSignal) -> Description:
    match signal:
        case StepStarted(sender=sender, receiver=receiver, offered=offered):
            return Description(
                'step.started',
                {
                    'sender': sender.name,
                    'receiver': receiver.name,
                    'offered': ','.join(str(label) for label in offered),
                },
            )
        case Selected(label=label, payload=payload):
            return Description(
                'step.selected',
                {'label': str(label), 'payload': payload},
            )
        case Recalled(label=label, payload=payload):
            return Description(
                'step.recalled',
                {'label': str(label), 'payload': payload},
            )
        case Delivered(envelope=envelope):
            return Description(
                'step.delivered',
                {
                    'sender': envelope.sender.name,
                    'receiver': envelope.receiver.name,
                    'label': str(envelope.label),
                    'payload': envelope.payload,
                },
            )
        case _:  # pragma: no cover
            assert_never(signal)


def _describe_model(signal: _ModelSignal) -> Description:
    match signal:
        case ModelCalled(schema_name=schema_name, effort=effort, messages=messages):
            return Description(
                'model.called',
                {'schema': schema_name, 'effort': effort, 'messages': messages},
            )
        case ModelAnswered(answer=answer):
            # Description is for a human reader. Session-level aggregation
            # (usage_of) reads Usage from the signal itself, not from here.
            return Description(
                'model.answered',
                {
                    'text': answer.text,
                    'model': str(answer.model),
                    'input_tokens': answer.usage.input_tokens,
                    'output_tokens': answer.usage.output_tokens,
                },
            )
        case ModelStreamed(delta=delta):
            return Description('model.streamed', {'delta': delta})
        case ModelCorrected(error=error):
            return Description('model.corrected', {'error': error})
        case _:  # pragma: no cover
            assert_never(signal)


def _describe_tool(signal: _ToolSignal) -> Description:
    match signal:
        case ToolCalled(tool=tool):
            return Description('tool.called', {'tool': str(tool)})
        case ToolAnswered(reply=reply):
            return Description('tool.answered', {'reply': str(reply)})
        case Failed(error=error):
            return Description('failed', {'error': error})
        case _:  # pragma: no cover
            assert_never(signal)
