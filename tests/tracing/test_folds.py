"""Folds over recorded events: usage_of and text_of."""

from __future__ import annotations

from collections import defaultdict

from hypothesis import given
from hypothesis import strategies as st

from agentsparty.llm.types import Answer, Message, ModelId, StructuredRequest, Usage
from agentsparty.tracing._folds import text_of, usage_of
from agentsparty.tracing.memory import MemoryTracer
from agentsparty.tracing.model import traced
from agentsparty.tracing.scope import counting_ids, current, new_scope
from agentsparty.tracing.signals import ModelAnswered, ModelCalled, ModelStreamed
from agentsparty.tracing.types import Event, Span, SpanId
from tests._helpers import usage_values

STUB = ModelId('stub', 'v1')


def _event(signal, span_id: str = '1', seq: int = 0) -> Event:
    return Event(signal=signal, span=Span(id=SpanId(span_id)), seq=seq)


@st.composite
def model_ids(draw: st.DrawFn) -> ModelId:
    provider = draw(st.sampled_from(['openai', 'stub', 'local']))
    name = draw(st.from_regex(r'[a-z0-9-]{1,12}', fullmatch=True))
    return ModelId(provider, name)


@given(st.lists(st.tuples(model_ids(), usage_values()), max_size=12))
def test_usage_of_is_the_fold(pairs: list[tuple[ModelId, Usage]]) -> None:
    events = [_event(ModelAnswered(Answer('t', model, usage))) for model, usage in pairs]
    expected: dict[ModelId, Usage] = {}
    for model, usage in pairs:
        expected[model] = expected.get(model, Usage()) + usage
    assert usage_of(events) == expected


def test_usage_of_separates_models() -> None:
    a = ModelId('openai', 'a')
    b = ModelId('openai', 'b')
    events = [
        _event(ModelAnswered(Answer('1', a, Usage(input_tokens=1)))),
        _event(ModelAnswered(Answer('2', b, Usage(output_tokens=2)))),
        _event(ModelCalled('s', 'none', 0)),
    ]
    assert usage_of(events) == {
        a: Usage(input_tokens=1),
        b: Usage(output_tokens=2),
    }


def test_usage_of_nothing_is_empty() -> None:
    assert usage_of([]) == {}


@given(
    st.lists(
        st.tuples(
            st.from_regex(r's[1-9]', fullmatch=True),
            st.text(max_size=8),
        ),
        max_size=20,
    ),
)
def test_text_of_is_the_fold(pairs: list[tuple[str, str]]) -> None:
    """text_of is concatenation of fragments per span; empty input is {}."""
    events = [
        _event(ModelStreamed(fragment), span_id=span, seq=index)
        for index, (span, fragment) in enumerate(pairs)
    ]
    expected: dict[SpanId, str] = defaultdict(str)
    for span, fragment in pairs:
        expected[SpanId(span)] += fragment
    assert text_of(events) == dict(expected)


async def test_a_streaming_stub_is_honest() -> None:
    """Assembled fragments equal the answer text for that model span."""

    class StreamingStub:
        async def complete(self, request: StructuredRequest) -> Answer:
            text = '"ok"'
            for delta in text:
                current().record(ModelStreamed(delta))
            return Answer(text, STUB)

    mem = MemoryTracer()
    with new_scope(mem, counting_ids()).enter():
        answer = await traced(StreamingStub()).complete(
            StructuredRequest(
                '',
                (Message('user', 'q'),),
                't',
                {'type': 'string'},
                'none',
            ),
        )
    assert answer.text == '"ok"'
    assert list(text_of(mem.events).values()) == ['"ok"']
