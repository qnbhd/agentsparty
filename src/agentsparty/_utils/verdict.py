"""Path-diagnosing verdict: a relation holds, or where and why it fails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from typing_extensions import assert_never


@dataclass(frozen=True, slots=True)
class Fits:
    """The relation holds; there is nothing to report."""


@dataclass(frozen=True, slots=True)
class Differs:
    """Where in the type the relation fails, and why."""

    trail: tuple[str, ...]
    reason: str


Verdict: TypeAlias = Fits | Differs
FITS: Fits = Fits()


def holds(verdict: Verdict) -> bool:
    """Whether *verdict* is a success.

    Args:
        verdict: The outcome of a path-diagnosing relation.

    Returns:
        ``True`` if the relation holds, ``False`` if it differs.
    """
    match verdict:
        case Fits():
            return True
        case Differs():
            return False
        case _:  # pragma: no cover
            assert_never(verdict)
