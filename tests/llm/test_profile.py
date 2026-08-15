"""Profile.floor is the right adjoint of the chain embedding."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.llm.profile import EVERY_EFFORT, NO_REASONING, Profile
from agentsparty.llm.types import EFFORTS, LEAST_EFFORT, Effort, Message, StructuredRequest


def rank(effort: Effort) -> int:
    return EFFORTS.index(effort)


@st.composite
def profiles(draw: st.DrawFn) -> Profile:
    """Any profile that serves the least effort."""
    extra = draw(st.frozensets(st.sampled_from(EFFORTS[1:])))
    return Profile(frozenset({LEAST_EFFORT}) | extra)


efforts = st.sampled_from(EFFORTS)


# floor is the right adjoint of the embedding of the served chain into EFFORTS:
# never exceeds, identity on served, monotone. The three property tests below
# are that statement, not three independent facts about the same function.


@given(profiles(), efforts)
def test_floor_never_exceeds_what_was_asked(profile: Profile, effort: Effort) -> None:
    assert rank(profile.floor(effort)) <= rank(effort)


@given(profiles(), efforts)
def test_floor_is_the_identity_on_served_efforts(
    profile: Profile,
    effort: Effort,
) -> None:
    if effort in profile.efforts:
        assert profile.floor(effort) == effort


@given(profiles(), efforts, efforts)
def test_floor_is_monotone(profile: Profile, e1: Effort, e2: Effort) -> None:
    if rank(e1) <= rank(e2):
        assert rank(profile.floor(e1)) <= rank(profile.floor(e2))


@given(profiles(), efforts)
def test_floor_is_idempotent(profile: Profile, effort: Effort) -> None:
    assert profile.floor(profile.floor(effort)) == profile.floor(effort)


@given(profiles(), efforts)
def test_floor_is_total(profile: Profile, effort: Effort) -> None:
    assert profile.floor(effort) in profile.efforts


def _request(effort: Effort) -> StructuredRequest:
    return StructuredRequest(
        instructions='',
        messages=(Message('user', 'hi'),),
        schema_name='t',
        schema={'type': 'object'},
        effort=effort,
    )


@given(efforts)
def test_every_effort_adapts_nothing(effort: Effort) -> None:
    request = _request(effort)
    assert EVERY_EFFORT.adapt(request) is request


@given(efforts)
def test_no_reasoning_flattens_everything(effort: Effort) -> None:
    assert NO_REASONING.adapt(_request(effort)).effort == LEAST_EFFORT


@given(profiles(), efforts)
def test_adapt_changes_only_the_effort(profile: Profile, effort: Effort) -> None:
    request = _request(effort)
    adapted = profile.adapt(request)
    assert adapted.instructions == request.instructions
    assert adapted.messages == request.messages
    assert adapted.schema_name == request.schema_name
    assert adapted.schema == request.schema
    assert adapted.effort == profile.floor(effort)


def test_a_profile_without_the_least_effort_is_rejected() -> None:
    with pytest.raises(ValueError, match='must serve'):
        Profile(frozenset({'high'}))  # type: ignore[arg-type]
