"""What a provider actually serves, and how a request is retracted onto it."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from agentsparty.llm.types import (
    EFFORTS,
    LEAST_EFFORT,
    Answer,
    Effort,
    LanguageModel,
    StructuredRequest,
)


@dataclass(frozen=True, slots=True)
class Profile:
    """The reasoning efforts a model serves.

    :data:`~agentsparty.llm.types.EFFORTS` is a chain — a total order from ``none``
    to ``high`` — and a profile names a subset of it. :meth:`floor` retracts
    any requested effort onto that subset by taking the greatest served effort
    that does not exceed it, so a request is **never** upgraded to something
    more expensive than what was asked for.

    Requiring :data:`~agentsparty.llm.types.LEAST_EFFORT` to be served is what
    makes the retraction total: there is always something to fall back to, so
    no caller ever has to check whether adaptation succeeded. This is the whole
    of what the industry spends a dictionary of capability flags on.
    """

    efforts: frozenset[Effort]

    @classmethod
    def of(cls, *extra: Effort) -> Profile:
        """Build a profile that always serves the least effort."""
        return cls(frozenset((LEAST_EFFORT, *extra)))

    def __post_init__(self) -> None:
        """Reject a profile that cannot serve the least effort.

        Raises:
            ValueError: if :data:`~agentsparty.llm.types.LEAST_EFFORT` is missing.
        """
        if LEAST_EFFORT not in self.efforts:
            raise ValueError(
                f'a profile must serve {LEAST_EFFORT!r}, got {sorted(self.efforts)}',
            )

    def floor(self, effort: Effort) -> Effort:
        """The greatest served effort that does not exceed *effort*.

        Args:
            effort: The effort that was asked for.

        Returns:
            The effort that will actually be sent.
        """
        wanted = EFFORTS[: EFFORTS.index(effort) + 1]
        # total by construction: LEAST_EFFORT is served and heads every slice.
        return next(e for e in reversed(wanted) if e in self.efforts)

    def adapt(self, request: StructuredRequest) -> StructuredRequest:
        """*request* with its effort retracted onto what this profile serves.

        Args:
            request: The turn about to be sent.
        """
        served = self.floor(request.effort)
        if served == request.effort:
            return request
        return replace(request, effort=served)


EVERY_EFFORT: Final = Profile.of(*EFFORTS[1:])
"""A profile that serves the whole chain; the identity of retraction."""

NO_REASONING: Final = Profile.of()
"""A profile for a model that does not reason: every request retracts to the
least effort, so a model asked for ``"high"`` is never sent a parameter it
would reject."""


@dataclass(frozen=True, slots=True)
class Profiled:
    """*inner*, asked only for what *profile* says it serves.

    Pair a profile with a model where the two meet, not inside the adapter:
    the same adapter class serves models with different capabilities, and a
    fallback chain routinely mixes them.
    """

    inner: LanguageModel
    profile: Profile

    async def complete(self, request: StructuredRequest) -> Answer:
        """*inner*'s answer to the adapted *request*.

        Args:
            request: The structured-output turn to answer.
        """
        return await self.inner.complete(self.profile.adapt(request))


__all__ = ['EVERY_EFFORT', 'NO_REASONING', 'Profile', 'Profiled']
