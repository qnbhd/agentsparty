"""OpenAI adapter: streaming complete records ModelStreamed and returns Answer."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field

from openai.types.responses import (
    Response,
    ResponseCompletedEvent,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
    ResponseUsage,
)

from agentsparty.llm.openai import OpenAIModel
from agentsparty.llm.types import Message, ModelId, StructuredRequest, Usage
from agentsparty.tracing import (
    MemoryTracer,
    ModelStreamed,
    counting_ids,
    new_scope,
    text_of,
    traced,
)

REQUEST = StructuredRequest(
    instructions='reply',
    messages=(Message('user', 'q'),),
    schema_name='Answer',
    schema={'type': 'object'},
    effort='none',
)


def _delta(text: str, seq: int) -> ResponseTextDeltaEvent:
    return ResponseTextDeltaEvent(
        type='response.output_text.delta',
        content_index=0,
        delta=text,
        item_id='tx_1',
        logprobs=[],
        output_index=0,
        sequence_number=seq,
    )


def _completed(usage: ResponseUsage | None, seq: int) -> ResponseCompletedEvent:
    return ResponseCompletedEvent(
        type='response.completed',
        sequence_number=seq,
        response=Response.model_construct(usage=usage, output=[]),
    )


def _usage(input_tokens: int = 1, output_tokens: int = 2) -> ResponseUsage:
    return ResponseUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        input_tokens_details=InputTokensDetails(cached_tokens=0, cache_write_tokens=0),
        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
    )


class _Stream:
    """Async iterator of prebuilt Responses stream events."""

    def __init__(self, events: Sequence[ResponseStreamEvent]) -> None:
        self._remaining = list(events)

    def __aiter__(self) -> AsyncIterator[ResponseStreamEvent]:
        return self

    async def __anext__(self) -> ResponseStreamEvent:
        if not self._remaining:
            raise StopAsyncIteration
        return self._remaining.pop(0)


@dataclass
class _Responses:
    """Stub of ``client.responses`` that always streams *events*."""

    events: Sequence[ResponseStreamEvent]
    last_kwargs: dict[str, object] = field(default_factory=dict)

    async def create(self, **kwargs: object) -> AsyncIterator[ResponseStreamEvent]:
        self.last_kwargs = kwargs
        return _Stream(self.events)


@dataclass
class _Client:
    """Duck-typed substitute for ``AsyncOpenAI`` used only in this test."""

    events: Sequence[ResponseStreamEvent]
    responses: _Responses = field(init=False)

    def __post_init__(self) -> None:
        self.responses = _Responses(self.events)


async def test_complete_streams_and_records_fragments() -> None:
    """OpenAIModel.complete drives stream=True, records deltas, returns whole text."""
    text = '{"ok": true}'
    client = _Client(
        [
            *[_delta(ch, i + 1) for i, ch in enumerate(text)],
            _completed(_usage(3, 4), len(text) + 1),
        ],
    )
    model = OpenAIModel('test-model', client)
    mem = MemoryTracer()

    with new_scope(mem, counting_ids()).enter():
        answer = await traced(model).complete(REQUEST)

    assert client.responses.last_kwargs.get('stream') is True
    assert answer.text == text
    assert answer.model == ModelId('openai', 'test-model')
    assert answer.usage == Usage(input_tokens=3, output_tokens=4)
    assert list(text_of(mem.events).values()) == [text]
    deltas = [delta for event in mem.events for delta in _streamed_delta(event.signal)]
    assert ''.join(deltas) == text
    assert deltas == list(text)


def _streamed_delta(signal: object) -> list[str]:
    match signal:
        case ModelStreamed(delta=delta):
            return [delta]
        case _:
            return []


async def test_complete_without_usage_still_assembles_text() -> None:
    """A completed event with no bill still yields the streamed answer."""
    client = _Client([_delta('hi', 1), _completed(None, 2)])
    model = OpenAIModel('m', client)
    answer = await model.complete(REQUEST)
    assert answer.text == 'hi'
    assert answer.usage == Usage()
