"""OpenAI Responses API backend for :class:`~agentsparty.llm.LanguageModel`.

Extension tier: import from ``agentsparty.llm.openai`` (provider SDK dependency).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from typing import Final, Protocol

try:
    from openai import APIConnectionError, APIStatusError, AsyncStream
except ModuleNotFoundError as exc:  # pragma: no cover - exercised in install-smoke
    raise ModuleNotFoundError(
        'the OpenAI backend requires the openai package; '
        "install it with: pip install 'agentsparty[openai]'",
    ) from exc

from openai.types.responses import (
    EasyInputMessageParam,
    ResponseInputItemParam,
    ResponseInputParam,
    ResponseStreamEvent,
    ResponseUsage,
)

from agentsparty.kernel.errors import ModelError, ModelRefused, ModelUnavailable
from agentsparty.llm.types import (
    NO_USAGE,
    Answer,
    Message,
    ModelId,
    StructuredRequest,
    Usage,
)
from agentsparty.tracing.scope import current
from agentsparty.tracing.signals import ModelStreamed

_RETRYABLE: Final[frozenset[int]] = frozenset((408, 409, 429, 500, 502, 503, 504))
"""Status codes for which the provider is asking to be tried again."""

_TEXT_DELTA: Final = 'response.output_text.delta'
_COMPLETED: Final = 'response.completed'

Stream = AsyncStream[ResponseStreamEvent] | AsyncIterator[ResponseStreamEvent]


class OpenAIClient(Protocol):
    """What :class:`OpenAIModel` needs from an OpenAI-compatible client.

    Structural: any object whose ``responses.create`` starts a Responses-API
    stream. ``AsyncOpenAI`` satisfies this; so do the stubs in the tests.
    ``responses`` is a read-only property so it matches the SDK's
    ``cached_property`` (a writable Protocol attribute would reject it).
    """

    @property
    def responses(self) -> OpenAIResponses:
        """Surface with an async ``create(..., stream=True)`` method."""
        ...


class OpenAIResponses(Protocol):
    """Responses API surface needed by :class:`OpenAIModel`."""

    @property
    def create(self) -> Callable[..., Awaitable[Stream]]:
        """Create a streamed response."""
        ...


class OpenAIModel:
    """LanguageModel backed by the OpenAI Responses API.

    The client is any object that looks like ``AsyncOpenAI`` on the
    ``responses.create`` surface — OpenAI, OpenRouter, Azure, a local
    gateway, or a test stub. The model id is the provider string the client
    expects; this class does not interpret it.
    """

    def __init__(self, model: str, client: OpenAIClient) -> None:
        """Create a model wrapper for *model* served by *client*.

        Args:
            model: Provider model identifier (e.g. ``"gpt-4o"``,
                ``"poolside/laguna-xs-2.1"``). Passed through to the client.
            client: An OpenAI-compatible async client. Prefer
                ``AsyncOpenAI(max_retries=0, timeout=30.0)`` so SDK retries
                do not hide under :class:`~agentsparty.llm.compose.Retrying` /
                :class:`~agentsparty.llm.compose.Fallback`, and a hung transport
                cannot stall the session.
        """
        self.model = model
        self._client = client

    async def complete(self, request: StructuredRequest) -> Answer:
        """Return a strict JSON-schema answer for *request*.

        Reads the provider stream and records each text fragment as
        :class:`~agentsparty.tracing.signals.ModelStreamed` on the ambient scope,
        then returns one whole :class:`~agentsparty.llm.types.Answer`.

        Args:
            request: The structured-output turn to send to the provider.

        Returns:
            The model's answer: text, identity and the bill.

        Raises:
            ModelUnavailable: on retryable transport or status failures.
            ModelRefused: on permanent provider refusals.
        """
        try:
            stream = await self._client.responses.create(
                model=self.model,
                instructions=request.instructions,
                input=_input_payload(request.messages),
                text={
                    'format': {
                        'type': 'json_schema',
                        'name': request.schema_name,
                        'schema': request.schema,
                        'strict': True,
                    },
                },
                reasoning={'effort': request.effort},
                stream=True,
            )
        except APIStatusError as exc:
            raise _translate(exc) from exc
        except APIConnectionError as exc:
            raise ModelUnavailable(f'cannot reach the provider: {exc}') from exc
        return await _answer_from_stream(stream, self.model)


async def _answer_from_stream(stream: Stream, model: str) -> Answer:
    """Fold *stream* into an answer, recording each text fragment as it arrives."""
    text = ''
    usage = NO_USAGE
    record = current().record
    async for event in stream:
        if event.type == _TEXT_DELTA:
            delta = event.delta
            record(ModelStreamed(delta))
            text += delta
        elif event.type == _COMPLETED:
            usage = _usage(event.response.usage)
    if not text:
        raise ModelError('model output must follow the requested schema')
    return Answer(text, ModelId('openai', model), usage)


def _usage(reported: ResponseUsage | None) -> Usage:
    """The bill *reported* by the Responses API, or the empty bill."""
    if reported is None:
        return NO_USAGE
    return Usage(
        input_tokens=reported.input_tokens,
        output_tokens=reported.output_tokens,
        cached_input_tokens=reported.input_tokens_details.cached_tokens,
        reasoning_tokens=reported.output_tokens_details.reasoning_tokens,
    )


def _translate(exc: APIStatusError) -> ModelError:
    """The domain failure *exc* stands for.

    Args:
        exc: The status error the SDK raised.
    """
    if exc.status_code not in _RETRYABLE:
        return ModelRefused(f'provider refused the request: {exc}')
    return ModelUnavailable(str(exc), _retry_after(exc.response.headers))


def _retry_after(headers: Mapping[str, str]) -> float:
    """How long the provider asked to wait, or ``0.0`` if it did not say.

    Only the delta-seconds form is read; the HTTP-date form is treated as no
    hint, because reading it needs a clock, and a clock in a translation
    function is a dependency the caller cannot substitute.
    """
    raw = headers.get('retry-after', '')
    return float(raw) if raw.isdigit() else 0


def _input_payload(messages: tuple[Message, ...]) -> ResponseInputParam:
    # list[EasyInputMessageParam] is a valid Responses input; the SDK alias
    # is a wide union of TypedDicts, so invariant list assignment needs cast.
    items: list[ResponseInputItemParam] = [
        EasyInputMessageParam(role=message.role, content=message.content) for message in messages
    ]
    return items


__all__ = ['OpenAIClient', 'OpenAIModel']
