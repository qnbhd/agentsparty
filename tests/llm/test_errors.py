"""Model failure types and OpenAI boundary translation."""

from __future__ import annotations

import math

import httpx
from hypothesis import given
from hypothesis import strategies as st
from openai import APIStatusError

from agentsparty.kernel.errors import ModelError, ModelRefused, ModelUnavailable
from agentsparty.llm.openai import _RETRYABLE, _retry_after, _translate


def _status_error(
    status_code: int,
    headers: dict[str, str] | None = None,
) -> APIStatusError:
    """A real SDK status error with *status_code* and *headers*."""
    response = httpx.Response(
        status_code,
        headers=headers or {},
        request=httpx.Request('POST', 'https://api.openai.com/v1/responses'),
    )
    return APIStatusError(f'status {status_code}', response=response, body=None)


@given(st.sampled_from(sorted(_RETRYABLE)))
def test_a_retryable_status_is_unavailable(code: int) -> None:
    error = _translate(_status_error(code))
    assert isinstance(error, ModelUnavailable)


@given(st.integers(100, 599).filter(lambda c: c not in _RETRYABLE))
def test_any_other_status_is_refused(code: int) -> None:
    error = _translate(_status_error(code))
    assert isinstance(error, ModelRefused)


def test_retry_after_seconds_are_read() -> None:
    assert math.isclose(_retry_after({'retry-after': '12'}), 12.0)
    error = _translate(_status_error(429, {'retry-after': '12'}))
    assert isinstance(error, ModelUnavailable)
    assert math.isclose(error.retry_after, 12.0)


def test_a_retry_after_date_is_no_hint() -> None:
    assert math.isclose(_retry_after({'retry-after': 'Wed, 21 Oct 2015 07:28:00 GMT'}), 0.0)
    assert math.isclose(_retry_after({}), 0.0)


def test_model_errors_share_a_parent() -> None:
    assert issubclass(ModelUnavailable, ModelError)
    assert issubclass(ModelRefused, ModelError)
    assert issubclass(ModelError, RuntimeError)
