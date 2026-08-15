"""Fallback, Retrying, Unavailable compose as a monoid with left identity."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.errors import ModelError, ModelRefused, ModelUnavailable
from agentsparty.llm.compose import Fallback, Retrying, Unavailable, fallback
from agentsparty.llm.types import Answer, Message, ModelId, StructuredRequest

STUB = ModelId('stub', 'v1')
OK = Answer('ok', STUB)
REQUEST = StructuredRequest(
    instructions='',
    messages=(Message('user', 'hi'),),
    schema_name='t',
    schema={'type': 'object'},
    effort='none',
)


@dataclass
class Answering:
    """A model that always answers, counting how often it was asked."""

    answer: Answer
    calls: int = 0

    async def complete(self, request: StructuredRequest) -> Answer:
        self.calls += 1
        return self.answer


@dataclass
class Failing:
    """A model that always fails with *error*, counting how often it was asked."""

    error: ModelError
    calls: int = 0

    async def complete(self, request: StructuredRequest) -> Answer:
        self.calls += 1
        raise self.error


@dataclass
class Slept:
    """A sleep that records what it was asked to wait and returns at once."""

    waits: list[float] = field(default_factory=list)

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


async def _outcome(model) -> str | type[ModelError]:
    try:
        answer = await model.complete(REQUEST)
    except ModelError as exc:
        return type(exc)
    else:
        return answer.text


# Outcome is determined by success/failure of each leaf, not identity of
# nesting: (a ⊛ b) ⊛ c and a ⊛ (b ⊛ c) give the same result for any
# combination of answering vs failing models.


@given(a_ok=st.booleans(), b_ok=st.booleans(), c_ok=st.booleans())
async def test_fallback_is_associative(*, a_ok: bool, b_ok: bool, c_ok: bool) -> None:
    def leaf(*, ok: bool, tag: str):
        if ok:
            return Answering(Answer(tag, STUB))
        return Failing(ModelUnavailable(tag))

    a, b, c = (
        leaf(ok=a_ok, tag='a'),
        leaf(ok=b_ok, tag='b'),
        leaf(ok=c_ok, tag='c'),
    )
    left = Fallback(Fallback(a, b), c)
    right = Fallback(a, Fallback(b, c))
    assert await _outcome(left) == await _outcome(right)


@given(ok=st.booleans())
async def test_unavailable_is_a_left_identity(*, ok: bool) -> None:
    if ok:
        model = Answering(OK)
        answer = await Fallback(Unavailable(), model).complete(REQUEST)
        assert answer == OK
    else:
        model = Failing(ModelRefused('no'))
        with pytest.raises(ModelRefused, match='no'):
            await Fallback(Unavailable(), model).complete(REQUEST)
        # Right identity fails on failure: secondary masks primary's error.
        with pytest.raises(ModelUnavailable):
            await Fallback(model, Unavailable()).complete(REQUEST)


async def test_a_succeeding_model_shadows_the_rest() -> None:
    primary = Answering(OK)
    secondary = Answering(Answer('other', STUB))
    answer = await Fallback(primary, secondary).complete(REQUEST)
    assert answer == OK
    assert secondary.calls == 0


async def test_fallback_of_nothing_is_unavailable() -> None:
    with pytest.raises(ModelUnavailable, match='empty'):
        await fallback().complete(REQUEST)


def test_fallback_of_one_is_that_model() -> None:
    model = Answering(OK)
    assert fallback(model) is model


async def test_the_whole_chain_is_on_the_traceback() -> None:
    first = Failing(ModelUnavailable('first'))
    second = Failing(ModelRefused('second'))
    with pytest.raises(ModelRefused) as caught:
        await Fallback(first, second).complete(REQUEST)
    assert isinstance(caught.value.__cause__, ModelUnavailable)
    assert 'first' in str(caught.value.__cause__)


async def test_refusal_falls_through_but_is_not_retried() -> None:
    primary = Failing(ModelRefused('hard no'))
    secondary = Answering(OK)
    answer = await Fallback(primary, secondary).complete(REQUEST)
    assert answer == OK

    refused = Failing(ModelRefused('hard no'))
    with pytest.raises(ModelRefused):
        await Retrying(refused, attempts=3, sleep=Slept()).complete(REQUEST)
    assert refused.calls == 1


@given(st.integers(0, 5))
async def test_retrying_asks_attempts_plus_one_times(attempts: int) -> None:
    model = Failing(ModelUnavailable('down', retry_after=0.0))
    slept = Slept()
    with pytest.raises(ModelUnavailable):
        await Retrying(model, attempts=attempts, sleep=slept).complete(REQUEST)
    assert model.calls == attempts + 1
    assert len(slept.waits) == attempts


async def test_retrying_waits_exactly_what_was_asked() -> None:
    model = Failing(ModelUnavailable('busy', retry_after=3.0))
    slept = Slept()
    with pytest.raises(ModelUnavailable):
        await Retrying(model, attempts=1, sleep=slept).complete(REQUEST)
    assert slept.waits == [3.0]


async def test_a_succeeding_model_is_asked_once() -> None:
    model = Answering(OK)
    slept = Slept()
    answer = await Retrying(model, attempts=5, sleep=slept).complete(REQUEST)
    assert answer == OK
    assert model.calls == 1
    assert slept.waits == []


def test_negative_attempts_are_rejected() -> None:
    with pytest.raises(ValueError, match='non-negative'):
        Retrying(Answering(OK), attempts=-1)
