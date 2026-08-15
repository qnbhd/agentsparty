"""Building one language model out of others.

Every type here is a ``LanguageModel`` that wraps ``LanguageModel``s. They
compose by nesting and nothing else: there is no registry, no ordering table
and no hook list, because the order *is* the nesting you wrote.

What may live here is decided by one rule: a transformer maps a request to an
answer to **that same request**. It may fail, and it may answer where the
model it wraps could not; it may not change the request in a way that cannot
be recomputed from the journal. That rule is what keeps this whole layer
invisible to the protocol — and it is also why conversation summarisation is
a role and not a wrapper.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import reduce
from typing import TypeAlias

from agentsparty._utils.assertions import require_nonnegative
from agentsparty.kernel.errors import ModelError, ModelUnavailable, TokenLimitError
from agentsparty.llm.types import NO_USAGE, Answer, LanguageModel, StructuredRequest, Usage

Sleep: TypeAlias = Callable[[float], Awaitable[None]]
"""How a transformer waits; a parameter so a test can supply its own."""

__all__ = ['Fallback', 'Metered', 'Retrying', 'Unavailable', 'fallback']


@dataclass(frozen=True, slots=True)
class _Answered:
    """A model that answered."""

    answer: Answer


@dataclass(frozen=True, slots=True)
class _Failed:
    """A model that would not answer, and why."""

    error: ModelError


async def _attempt(
    model: LanguageModel,
    request: StructuredRequest,
) -> _Answered | _Failed:
    """Ask *model* for *request*, reporting failure as a value."""
    try:
        return _Answered(await model.complete(request))
    except ModelError as exc:
        return _Failed(exc)


@dataclass(frozen=True, slots=True)
class Unavailable:
    """A model that never answers.

    The honest value for "no model configured": putting it in front of a
    fallback chain changes nothing.
    """

    reason: str = 'no model is configured'

    async def complete(self, request: StructuredRequest) -> Answer:
        """Never return.

        Args:
            request: Ignored.

        Raises:
            ModelUnavailable: always.
        """
        raise ModelUnavailable(self.reason)


@dataclass(frozen=True, slots=True)
class Fallback:
    """*primary*, falling back to *secondary* when it will not answer.

    Both kinds of failure fall through: a model that refuses this request is a
    reason to ask a different model, even though it is not a reason to ask the
    same one again.

    When both fail, *secondary*'s failure is raised **from** *primary*'s, so
    the whole chain is on the traceback in the order it was tried. agentsparty does
    not raise an exception group: the surveyed framework that does documents
    that every ``except ModelAPIError`` in user code silently stops matching.
    """

    primary: LanguageModel
    secondary: LanguageModel

    async def complete(self, request: StructuredRequest) -> Answer:
        """The first answer *primary* or *secondary* gives.

        Args:
            request: The structured-output turn to answer.

        Raises:
            ModelError: *secondary*'s failure, caused by *primary*'s, if
                neither answers.
        """
        match await _attempt(self.primary, request):
            case _Answered(answer=answer):
                return answer
            case _Failed(error=error):
                return await _after(self.secondary, request, error)


async def _after(
    model: LanguageModel,
    request: StructuredRequest,
    earlier: ModelError,
) -> Answer:
    """*model*'s answer, or its failure recorded as following *earlier*."""
    try:
        return await model.complete(request)
    except ModelError as exc:
        raise exc from earlier


def fallback(*models: LanguageModel) -> LanguageModel:
    """Try *models* in order until one answers.

    With no models this is :class:`Unavailable`; with one it is that model
    itself. Nesting order does not matter — the chain is just tried in the
    order given.

    Args:
        models: The models to try, most preferred first.
    """
    if not models:
        return Unavailable('an empty fallback chain')
    return reduce(Fallback, models)


@dataclass(frozen=True, slots=True)
class Retrying:
    """*inner*, asked again while it says another attempt may succeed.

    Only :class:`~agentsparty.kernel.errors.ModelUnavailable` is retried, because that is
    what the type means; :class:`~agentsparty.kernel.errors.ModelRefused` is raised at
    once. There is no backoff policy: the wait is exactly what the provider
    asked for in ``Retry-After`` and nothing when it asked for nothing. A
    guessed backoff is a number nobody measured; this project answers a retry
    question with one integer.
    """

    inner: LanguageModel
    attempts: int = 1
    sleep: Sleep = asyncio.sleep

    def __post_init__(self) -> None:
        """Reject a negative retry budget.

        Raises:
            ValueError: if :attr:`attempts` is below zero.
        """
        require_nonnegative('retry attempts', self.attempts)

    async def complete(self, request: StructuredRequest) -> Answer:
        """The first answer *inner* gives, asking again while that may help.

        Args:
            request: The structured-output turn to answer.
        """
        return await self._ask(request, self.attempts)

    async def _ask(self, request: StructuredRequest, left: int) -> Answer:
        """*inner*'s answer, with *left* further attempts available.

        Recursion depth is ``attempts + 1``, and *attempts* is validated as
        non-negative at construction, so unbounded recursion cannot arise.
        """
        match await _attempt(self.inner, request):
            case _Answered(answer=answer):
                return answer
            case _Failed(error=ModelUnavailable() as error) if left > 0:
                await self.sleep(error.retry_after)
                return await self._ask(request, left - 1)
            case _Failed(error=error):
                raise error


class Metered:
    """*inner*, refusing to begin a call once *tokens* have been billed.

    The one transformer here that is not a pure function of the model it
    wraps, and necessarily so: a meter that forgot would not be a meter. Its
    state is the receipts, and sharing one instance between several agents is
    how several agents share one budget.

    It bounds a process, not a session: a resumed run replays recorded
    decisions without calling a model at all, so a fresh meter is correct —
    the same rule :class:`~agentsparty.kernel.budget.Allowance` already follows.
    """

    def __init__(self, inner: LanguageModel, tokens: int) -> None:
        """Meter *inner* at *tokens* billed tokens.

        Args:
            inner: The model to meter.
            tokens: Total input plus output tokens after which no further call
                is begun.

        Raises:
            ValueError: if *tokens* is negative.
        """
        require_nonnegative('a token meter', tokens)
        self._inner = inner
        self._tokens = tokens
        self._billed = NO_USAGE

    @property
    def billed(self) -> Usage:
        """What has been billed through this meter so far."""
        return self._billed

    async def complete(self, request: StructuredRequest) -> Answer:
        """*inner*'s answer, if the meter still has room to begin the call.

        Args:
            request: The structured-output turn to answer.

        Raises:
            TokenLimitError: if the meter is already spent.
        """
        if self._billed.total_tokens >= self._tokens:
            total_tokens = self._billed.total_tokens
            raise TokenLimitError(
                f'{total_tokens} tokens already billed through a meter of {self._tokens}',
            )
        answer = await self._inner.complete(request)
        self._billed += answer.usage
        return answer
