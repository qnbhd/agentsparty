"""Language-model contract types shared with the protocol layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Protocol, TypeAlias

from agentsparty._utils.assertions import require_nonnegative

__all__ = [
    'EFFORTS',
    'LEAST_EFFORT',
    'NO_USAGE',
    'Answer',
    'ChatRole',
    'Effort',
    'LanguageModel',
    'Message',
    'ModelId',
    'StructuredRequest',
    'Usage',
]

Effort: TypeAlias = Literal['none', 'minimal', 'low', 'medium', 'high']
ChatRole: TypeAlias = Literal['user', 'assistant', 'system']

EFFORTS: Final[tuple[Effort, ...]] = ('none', 'minimal', 'low', 'medium', 'high')
"""Every reasoning effort, from least to greatest.

Kept next to :data:`Effort` on purpose: the alias and its enumeration are two
halves of one fact, and a plan that separates them lets them drift.
"""

LEAST_EFFORT: Final[Effort] = EFFORTS[0]
"""The effort every model is assumed to serve; see :class:`~agentsparty.llm.profile.Profile`."""


@dataclass(frozen=True, slots=True)
class ModelId:
    """Which model produced an answer: a provider and a name inside it.

    Rendered as ``provider:name`` — the notation every surveyed framework uses
    for the same purpose. agentsparty *parses* that notation; it does not resolve it.
    Resolving a name to a class needs a dynamic registry, which this project
    forbids: you construct the adapter yourself and pass it its client.
    """

    provider: str
    name: str

    def __post_init__(self) -> None:
        """Reject a name that would not survive a round trip.

        A colon inside *provider* would re-split in the wrong place, so
        ``ModelId.parse(str(m)) == m`` would stop holding.

        Raises:
            ValueError: if either part is empty or *provider* contains ``":"``.
        """
        if not self.provider or not self.name:
            raise ValueError(f'a model id needs both parts, got {self!r}')
        if ':' in self.provider:
            raise ValueError(f"a provider may not contain ':', got {self.provider!r}")

    def __str__(self) -> str:
        """The ``provider:name`` rendering."""
        return f'{self.provider}:{self.name}'

    @classmethod
    def parse(cls, text: str) -> ModelId:
        """The model id written as ``provider:name`` in *text*.

        Only the first colon separates: ``"openrouter:anthropic/claude"`` and
        ``"ollama:llama3:70b"`` both parse the way you would read them.

        Args:
            text: The ``provider:name`` rendering to read.

        Raises:
            ValueError: if *text* carries no separator.
        """
        provider, separator, name = text.partition(':')
        if not separator:
            raise ValueError(f"a model id must read 'provider:name', got {text!r}")
        return cls(provider, name)


def _nonnegative(usage: Usage) -> None:
    """Reject a negative token count in *usage*."""
    counts = (
        usage.input_tokens,
        usage.output_tokens,
        usage.cached_input_tokens,
        usage.reasoning_tokens,
    )
    for count in counts:
        require_nonnegative('token count', count)


@dataclass(frozen=True, slots=True)
class Usage:
    """What one completion was billed.

    Bills add up: :data:`NO_USAGE` changes nothing when added, and the order
    the parts were added in does not matter — the same shape as
    :class:`~agentsparty.kernel.budget.Spent`.

    Two fields name a *part of* another field rather than a separate charge:
    ``cached_input_tokens`` are input tokens served from the provider's cache,
    and ``reasoning_tokens`` are output tokens spent thinking. Neither is added
    into :attr:`total_tokens` a second time.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0

    def __post_init__(self) -> None:
        """Reject a bill that does not add up.

        Raises:
            ValueError: if a count is negative or a part exceeds its whole.
        """
        _nonnegative(self)
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError(
                f'cached input tokens ({self.cached_input_tokens}) exceed input '
                f'tokens ({self.input_tokens})',
            )
        if self.reasoning_tokens > self.output_tokens:
            raise ValueError(
                f'reasoning tokens ({self.reasoning_tokens}) exceed output '
                f'tokens ({self.output_tokens})',
            )

    def __add__(self, other: Usage) -> Usage:
        """The total of this bill and *other*.

        The two "part of" invariants are preserved by summation, so a total of
        valid bills is a valid bill.

        Args:
            other: The bill to add.
        """
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cached_input_tokens + other.cached_input_tokens,
            self.reasoning_tokens + other.reasoning_tokens,
        )

    @property
    def total_tokens(self) -> int:
        """Input plus output; the parts-of fields are already inside those."""
        return self.input_tokens + self.output_tokens


NO_USAGE: Final = Usage()
"""The empty bill: what a provider that reports no usage is recorded as."""


@dataclass(frozen=True, slots=True)
class Answer:
    """One completion: the text, who produced it, and what it cost.

    ``usage`` defaults to :data:`NO_USAGE` because a provider that reports no
    token counts is a real case, and the empty bill is the honest way to say
    so: adding it to a total changes nothing.
    """

    text: str
    model: ModelId
    usage: Usage = NO_USAGE


@dataclass(frozen=True, slots=True)
class Message:
    """One chat message: a role plus its text content."""

    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class StructuredRequest:
    """One structured-output turn: history plus the schema the reply obeys."""

    instructions: str
    messages: tuple[Message, ...]
    schema_name: str
    schema: dict[str, object]
    effort: Effort


class LanguageModel(Protocol):
    """A chat model that answers with JSON matching a requested schema.

    Schemas are built and payloads are validated by the protocol layer, so an
    implementation only carries the request to a provider, translates the
    provider's failures into :class:`~agentsparty.kernel.errors.ModelError`, and returns
    what it got back.
    """

    async def complete(self, request: StructuredRequest) -> Answer:
        """Return the model's answer for *request*.

        Args:
            request: The structured-output turn to answer.

        Raises:
            ModelUnavailable: if another attempt may succeed.
            ModelRefused: if this request will not be served however often it
                is asked.
        """
        ...
