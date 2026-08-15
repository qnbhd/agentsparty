# ScriptedLanguageModel (/docs/agentsparty/llm/scripted/ScriptedLanguageModel)

LanguageModel that returns a fixed queue of answer texts.

Exhaustion raises `ModelRefused` so agent repair
paths stay honest: the double did not "fail open", it ran out of script.

## Attributes

<PyAttribute name={"requests"} type={"list[StructuredRequest]"} value={"[]"} />

## Functions

<PyFunction name={"__init__"} type={"(self, answers, *, model=None) -> None"}>

Queue *answers* to return from successive `complete` calls.

<PySourceCode >

```python
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
```

</PySourceCode>

<div >

<PyParameter name={"answers"} type={"Sequence[str]"} value={undefined}>

JSON (or plain text) bodies returned one per call.

</PyParameter>
<PyParameter name={"model"} type={"ModelId | None"} value={"None"}>

Identity reported on each answer; defaults to a scripted id.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"complete"} type={"(self, request) -> Answer"}>

Return the next scripted answer, or refuse when the queue is empty.

<PySourceCode >

```python
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
```

</PySourceCode>

<div >

<PyParameter name={"request"} type={"StructuredRequest"} value={undefined}>

The structured-output turn (recorded for assertions).

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.Answer"}>

The next scripted answer with empty usage.

</PyFunctionReturn>

</PyFunction>
