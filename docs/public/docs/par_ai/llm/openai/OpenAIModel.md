# OpenAIModel (/docs/agentsparty/llm/openai/OpenAIModel)

LanguageModel backed by the OpenAI Responses API.

The client is any object that looks like ``AsyncOpenAI`` on the
``responses.create`` surface — OpenAI, OpenRouter, Azure, a local
gateway, or a test stub. The model id is the provider string the client
expects; this class does not interpret it.

## Functions

<PyFunction name={"__init__"} type={"(self, model, client) -> None"}>

Create a model wrapper for *model* served by *client*.

<PySourceCode >

```python
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
```

</PySourceCode>

<div >

<PyParameter name={"model"} type={"str"} value={undefined}>

Provider model identifier (e.g. ``"gpt-4o"``,
``"poolside/laguna-xs-2.1"``). Passed through to the client.

</PyParameter>
<PyParameter name={"client"} type={"OpenAIClient"} value={undefined}>

An OpenAI-compatible async client. Prefer
``AsyncOpenAI(max_retries=0, timeout=30.0)`` so SDK retries
do not hide under [`Retrying`](/docs/agentsparty/llm/compose/Retrying) /
[`Fallback`](/docs/agentsparty/llm/compose/Fallback), and a hung transport
cannot stall the session.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"complete"} type={"(self, request) -> Answer"}>

Return a strict JSON-schema answer for *request*.

Reads the provider stream and records each text fragment as
[`ModelStreamed`](/docs/agentsparty/tracing/signals/ModelStreamed) on the ambient scope,
then returns one whole [`Answer`](/docs/agentsparty/llm/types/Answer).

<PySourceCode >

```python
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
```

</PySourceCode>

<div >

<PyParameter name={"request"} type={"StructuredRequest"} value={undefined}>

The structured-output turn to send to the provider.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.Answer"}>

The model's answer: text, identity and the bill.

</PyFunctionReturn>

</PyFunction>
