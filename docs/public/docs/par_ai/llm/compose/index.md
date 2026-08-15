# compose (/docs/agentsparty/llm/compose/index)

Building one language model out of others.

Every type here is a ``LanguageModel`` that wraps ``LanguageModel``s. They
compose by nesting and nothing else: there is no registry, no ordering table
and no hook list, because the order *is* the nesting you wrote.

What may live here is decided by one rule: a transformer maps a request to an
answer to **that same request**. It may fail, and it may answer where the
model it wraps could not; it may not change the request in a way that cannot
be recomputed from the journal. That rule is what keeps this whole layer
invisible to the protocol — and it is also why conversation summarisation is
a role and not a wrapper.

<PyAttribute name={"Sleep"} type={"TypeAlias"} value={"Callable[[float], Awaitable[None]]"}>

How a transformer waits; a parameter so a test can supply its own.

</PyAttribute>

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"Unavailable"} href={"/docs/agentsparty/llm/compose/Unavailable"} />
<Card title={"Fallback"} href={"/docs/agentsparty/llm/compose/Fallback"} />
<Card title={"Retrying"} href={"/docs/agentsparty/llm/compose/Retrying"} />
<Card title={"Metered"} href={"/docs/agentsparty/llm/compose/Metered"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"fallback"} type={"(*models) -> LanguageModel"}>

Try *models* in order until one answers.

With no models this is `Unavailable`; with one it is that model
itself. Nesting order does not matter — the chain is just tried in the
order given.

<PySourceCode >

```python
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
```

</PySourceCode>

<div >

<PyParameter name={"models"} type={"LanguageModel"} value={"()"}>

The models to try, most preferred first.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.llm.types.LanguageModel"} />

</PyFunction>

</Tab>

</Tabs>
