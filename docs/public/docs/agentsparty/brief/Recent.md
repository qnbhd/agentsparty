# Recent (/docs/agentsparty/brief/Recent)

Brief that keeps only the last `keep` envelopes.

The bounded-context policy: what the industry spends a summarisation
middleware on, without the model call that makes replay diverge. To keep
information from before the window, send it through the protocol — see
the ``Scribe`` pattern in the documentation's agent-system guide.

## Attributes

<PyAttribute name={"subject"} type={"Role"} value={null} />

<PyAttribute name={"keep"} type={"int"} value={null} />

<PyAttribute name={"turns"} type={"tuple[Envelope, ...]"} value={"()"} />

## Functions

<PyFunction name={"remember"} type={"(self, envelope) -> Brief"}>

The brief with *envelope* appended and the window re-applied.

<PySourceCode >

```python
def remember(self, envelope: Envelope) -> Brief:
    """The brief with *envelope* appended and the window re-applied.

    Args:
        envelope: A message this participant sent or received.
    """
    kept = (*self.turns, envelope)[-self.keep :]
    return Recent(self.subject, self.keep, kept)
```

</PySourceCode>

<div >

<PyParameter name={"envelope"} type={"Envelope"} value={undefined}>

A message this participant sent or received.

</PyParameter>

</div>

<PyFunctionReturn type={"agentsparty.brief.Brief"} />

</PyFunction>

<PyFunction name={"messages"} type={"(self) -> tuple[Message, ...]"}>

The envelopes still inside the window, rendered oldest first.

<PySourceCode >

```python
def messages(self) -> tuple[Message, ...]:
    """The envelopes still inside the window, rendered oldest first."""
    return tuple(line(self.subject, envelope) for envelope in self.turns)
```

</PySourceCode>

<PyFunctionReturn type={"tuple[agentsparty.llm.types.Message, ...]"} />

</PyFunction>

<PyFunction name={"__init__"} type={"(self, subject, keep, turns=()) -> None"}>

<div >

<PyParameter name={"subject"} type={"Role"} value={null} />
<PyParameter name={"keep"} type={"int"} value={null} />
<PyParameter name={"turns"} type={"tuple[Envelope, ...]"} value={"()"} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
