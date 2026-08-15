"""Model seam: wrap a language model so completions land under the ambient span."""

from __future__ import annotations

from agentsparty.llm.types import Answer, LanguageModel, StructuredRequest
from agentsparty.tracing.scope import current
from agentsparty.tracing.signals import ModelAnswered, ModelCalled

__all__ = ['TracedModel', 'traced']


class TracedModel:
    """A language model whose calls are recorded into the ambient scope."""

    def __init__(self, inner: LanguageModel) -> None:
        """Wrap *inner* so its completions appear in the running session.

        Args:
            inner: The language model to observe.
        """
        self._inner = inner

    async def complete(self, request: StructuredRequest) -> Answer:
        """Record a model span around ``inner.complete(request)``.

        Args:
            request: The structured-output turn to answer.
        """
        with (
            current()
            .child()
            .open(
                ModelCalled(request.schema_name, request.effort, len(request.messages)),
            ) as call
        ):
            answer = await self._inner.complete(request)
            call.record(ModelAnswered(answer))
            return answer


def traced(model: LanguageModel) -> LanguageModel:
    """Wrap *model* so every completion is recorded into the ambient scope.

    Outside a traced session the ambient scope discards everything, so a
    wrapped model behaves exactly like the one it wraps.

    Args:
        model: The language model to observe.
    """
    return TracedModel(model)
