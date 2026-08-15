"""Deterministic language-model double for offline agent tests.

A test tool, not a substitute for a real provider: pass it explicitly to
:class:`~agentsparty.agent.Agent` when you need a fixed queue of answers without
the network.
"""

from __future__ import annotations

from collections.abc import Sequence

from agentsparty._utils.assertions import post
from agentsparty.kernel.errors import ModelRefused
from agentsparty.llm.types import NO_USAGE, Answer, ModelId, StructuredRequest

__all__ = ['ScriptedLanguageModel']


class ScriptedLanguageModel:
    """LanguageModel that returns a fixed queue of answer texts.

    Exhaustion raises :class:`~agentsparty.kernel.errors.ModelRefused` so agent repair
    paths stay honest: the double did not "fail open", it ran out of script.
    """

    def __init__(
        self,
        answers: Sequence[str],
        *,
        model: ModelId | None = None,
    ) -> None:
        """Queue *answers* to return from successive :meth:`complete` calls.

        Args:
            answers: JSON (or plain text) bodies returned one per call.
            model: Identity reported on each answer; defaults to a scripted id.
        """
        self._answers = list(answers)
        self._model = ModelId('scripted', 'test') if model is None else model
        self.requests: list[StructuredRequest] = []

    async def complete(self, request: StructuredRequest) -> Answer:
        """Return the next scripted answer, or refuse when the queue is empty.

        Args:
            request: The structured-output turn (recorded for assertions).

        Returns:
            The next scripted answer with empty usage.

        Raises:
            ModelRefused: if every scripted answer has already been consumed.
        """
        self.requests.append(request)
        if not self._answers:
            raise ModelRefused(
                'ScriptedLanguageModel exhausted; still need an answer for '
                f'schema {request.schema_name!r}',
            )
        text = self._answers.pop(0)
        answer = Answer(text, self._model, NO_USAGE)
        post(expr=answer.text == text, message='scripted answer must carry the queued text')
        return answer


__all__ = ['ScriptedLanguageModel']
