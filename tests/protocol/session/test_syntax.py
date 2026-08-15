"""The ``alt`` sugar: ``alt[X, Y](…)`` is ``alt[X, Y]( …)``."""

from __future__ import annotations

from itertools import starmap
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from agentsparty.kernel.role import Role, roles
from agentsparty.protocol import Case, case
from agentsparty.protocol.session import alt
from tests.protocol import strategies


@st.composite
def _case_arms(draw: st.DrawFn) -> list[Case[Any]]:
    """A list of one to three labelled cases with unique names and codecs."""
    count = draw(st.integers(1, 3))
    names = draw(
        st.lists(
            st.sampled_from(strategies.LABEL_NAMES),
            min_size=count,
            max_size=count,
            unique=True,
        ),
    )
    codecs = draw(st.lists(strategies.CODE, min_size=count, max_size=count))
    return list(starmap(case, zip(names, codecs, strict=True)))


@given(
    cases=_case_arms(),
    sender=strategies.ROLE,
    receiver=strategies.ROLE,
)
def test_alt_equals_alt(
    cases: list[Case[Any]],
    sender: Role,
    receiver: Role,
) -> None:
    """``alt[X, Y](…)`` builds exactly the alt ``alt[X, Y]( …)``."""
    assume(sender != receiver)
    assert (
        alt[sender, receiver](*cases).close()
        == alt[sender, receiver](
            *cases,
        ).close()
    )


def test_alt_rejects_self_talk() -> None:
    """``alt`` inherits ``alt``'s refusal of a role talking to itself."""
    A = roles('A')[0]
    with pytest.raises(ValueError, match='talk to itself'):
        alt[A, A](case('x'))
