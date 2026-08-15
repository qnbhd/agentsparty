"""What one run of a session may spend, and what it has spent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from agentsparty._utils.assertions import require_nonnegative

DEFAULT_UNFOLDINGS: Final = 32
"""Unfoldings a run may perform when no allowance is given."""


@dataclass(frozen=True, slots=True)
class Spent:
    """What a run has spent so far.

    Totals add up in any order: :data:`NOTHING_SPENT` changes nothing when
    added, and the order the parts were added in does not matter.
    """

    unfoldings: int = 0
    steps: int = 0

    def __add__(self, other: Spent) -> Spent:
        """The total of this spend and *other*.

        Args:
            other: The spend to add.
        """
        return Spent(self.unfoldings + other.unfoldings, self.steps + other.steps)


NOTHING_SPENT: Final = Spent()
ONE_UNFOLDING: Final = Spent(unfoldings=1)
ONE_STEP: Final = Spent(steps=1)


@dataclass(frozen=True, slots=True)
class Allowance:
    """What one :meth:`~agentsparty.runtime.AgentRuntime.run` may spend.

    ``None`` in a field opts explicitly into an unbounded quantity.

    Only quantities a session can refuse *before* paying are metered here. A
    provider's token count is known after the request has been sent and billed;
    a limit checked then is a receipt, not an allowance, so token and money
    limits are deliberately absent.

    An allowance bounds one run, not a session's lifetime: a resumed run
    replays recorded decisions for free, exactly as recursion already does, so
    that a long session stays resumable.
    """

    unfoldings: int | None = DEFAULT_UNFOLDINGS
    steps: int | None = None

    def __post_init__(self) -> None:
        """Reject a negative allowance.

        Raises:
            ValueError: if a field is set and below zero.
        """
        _check('unfoldings', self.unfoldings)
        _check('steps', self.steps)

    def covers(self, spent: Spent) -> bool:
        """Whether *spent* is still within this allowance.

        Args:
            spent: The total spent so far.
        """
        return _within(spent.unfoldings, self.unfoldings) and _within(
            spent.steps,
            self.steps,
        )


def _check(field: str, limit: int | None) -> None:
    if limit is not None:
        require_nonnegative(f'{field} allowance', limit)


def _within(used: int, limit: int | None) -> bool:
    return limit is None or used <= limit


DEFAULT_ALLOWANCE: Final = Allowance()
UNBOUNDED: Final = Allowance(unfoldings=None, steps=None)

__all__ = [
    'DEFAULT_ALLOWANCE',
    'DEFAULT_UNFOLDINGS',
    'NOTHING_SPENT',
    'ONE_STEP',
    'ONE_UNFOLDING',
    'UNBOUNDED',
    'Allowance',
    'Spent',
]
