"""Usage monoid, ModelId equivalence, Effort enumeration."""

from __future__ import annotations

from typing import get_args

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.llm.types import (
    EFFORTS,
    NO_USAGE,
    Effort,
    ModelId,
    Usage,
)


@st.composite
def usages(draw: st.DrawFn) -> Usage:
    """Any bill that adds up."""
    input_tokens = draw(st.integers(0, 10_000))
    output_tokens = draw(st.integers(0, 10_000))
    return Usage(
        input_tokens,
        output_tokens,
        draw(st.integers(0, input_tokens)),
        draw(st.integers(0, output_tokens)),
    )


@given(a=usages(), b=usages(), c=usages())
def test_usage_is_a_commutative_monoid(a: Usage, b: Usage, c: Usage) -> None:
    assert a + b == b + a
    assert (a + b) + c == a + (b + c)
    assert a + NO_USAGE == a
    assert NO_USAGE + a == a


@given(a=usages(), b=usages())
def test_usage_is_closed_under_addition(a: Usage, b: Usage) -> None:
    total = a + b
    assert isinstance(total, Usage)
    assert total.input_tokens == a.input_tokens + b.input_tokens
    assert total.cached_input_tokens <= total.input_tokens
    assert total.reasoning_tokens <= total.output_tokens


@given(a=usages(), b=usages())
def test_total_counts_each_token_once(a: Usage, b: Usage) -> None:
    assert (a + b).total_tokens == a.total_tokens + b.total_tokens


@st.composite
def model_ids(draw: st.DrawFn) -> ModelId:
    """Any ModelId that survives construction."""
    provider = draw(st.from_regex(r'[A-Za-z0-9._-]{1,20}', fullmatch=True))
    name = draw(st.from_regex(r'[A-Za-z0-9._/-]{1,40}', fullmatch=True))
    return ModelId(provider, name)


@given(model_ids())
def test_model_id_round_trips(model: ModelId) -> None:
    assert ModelId.parse(str(model)) == model


def test_model_id_rejects_a_colon_in_the_provider() -> None:
    with pytest.raises(ValueError, match='provider may not contain'):
        ModelId('open:ai', 'gpt')


def test_usage_rejects_a_part_larger_than_its_whole() -> None:
    with pytest.raises(ValueError, match='cached input'):
        Usage(input_tokens=1, cached_input_tokens=2)
    with pytest.raises(ValueError, match='reasoning'):
        Usage(output_tokens=1, reasoning_tokens=2)


def test_efforts_enumerate_the_alias() -> None:
    # typing.get_args is the only way to prove the alias and its enumeration
    # still name the same fact; they are two halves that must not drift.
    assert set(EFFORTS) == set(get_args(Effort))
