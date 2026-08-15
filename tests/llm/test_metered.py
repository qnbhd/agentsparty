"""Metered totals receipts and refuses the next call, not the overrunning one."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.errors import TokenLimitError
from agentsparty.llm.compose import Fallback, Metered
from agentsparty.llm.types import Answer, Message, ModelId, StructuredRequest, Usage
from tests._helpers import usage_values

STUB = ModelId('stub', 'v1')
REQUEST = StructuredRequest(
    instructions='',
    messages=(Message('user', 'hi'),),
    schema_name='t',
    schema={'type': 'object'},
    effort='none',
)


@dataclass
class Answering:
    """A model that always answers with *answer*, counting calls."""

    answer: Answer
    calls: int = 0

    async def complete(self, request: StructuredRequest) -> Answer:
        self.calls += 1
        return self.answer


@given(st.lists(usage_values(), min_size=1, max_size=8))
async def test_the_meter_totals_what_it_saw(bills: list[Usage]) -> None:
    total = Usage()
    for bill in bills:
        total += bill
    answers = [Answer(f'a{i}', STUB, bill) for i, bill in enumerate(bills)]

    class Scripted:
        def __init__(self) -> None:
            self.index = 0

        async def complete(self, request: StructuredRequest) -> Answer:
            answer = answers[self.index]
            self.index += 1
            return answer

    meter = Metered(Scripted(), tokens=total.total_tokens + 1)
    for _ in bills:
        await meter.complete(REQUEST)
    assert meter.billed == total


async def test_a_spent_meter_begins_no_call() -> None:
    answer = Answer('x', STUB, Usage(input_tokens=5, output_tokens=5))
    inner = Answering(answer)
    meter = Metered(inner, tokens=10)
    await meter.complete(REQUEST)
    assert meter.billed.total_tokens == 10
    with pytest.raises(TokenLimitError):
        await meter.complete(REQUEST)
    assert inner.calls == 1


async def test_the_call_that_overran_is_not_refused() -> None:
    # Law 9 honesty: the overrunning call returns; the next one is refused.
    answer = Answer('x', STUB, Usage(input_tokens=8, output_tokens=2))
    inner = Answering(answer)
    meter = Metered(inner, tokens=5)
    result = await meter.complete(REQUEST)
    assert result == answer
    assert meter.billed.total_tokens == 10
    with pytest.raises(TokenLimitError):
        await meter.complete(REQUEST)
    assert inner.calls == 1


async def test_a_zero_meter_begins_nothing() -> None:
    inner = Answering(Answer('x', STUB))
    meter = Metered(inner, tokens=0)
    with pytest.raises(TokenLimitError):
        await meter.complete(REQUEST)
    assert inner.calls == 0


async def test_a_token_limit_is_not_a_model_failure() -> None:
    a = Answering(Answer('a', STUB))
    b = Answering(Answer('b', STUB))
    with pytest.raises(TokenLimitError):
        await Fallback(Metered(a, 0), b).complete(REQUEST)
    assert b.calls == 0


def test_negative_tokens_are_rejected() -> None:
    with pytest.raises(ValueError, match='non-negative'):
        Metered(Answering(Answer('x', STUB)), tokens=-1)
