# StreamConsole (/docs/agentsparty/console/StreamConsole)

Console backed by text streams, defaulting to the process stdio.

Streams are resolved on every call rather than captured in ``__init__``:
``sys.stdout`` is routinely replaced after construction (test capture,
output redirection), and a captured handle would silently ignore that.

## Functions

<PyFunction name={"__init__"} type={"(self, reader=None, writer=None) -> None"}>

Create a console over *reader*/*writer*, defaulting to stdio.

<PySourceCode >

```python
def __init__(
    self,
    reader: TextIO | None = None,
    writer: TextIO | None = None,
) -> None:
    """Create a console over *reader*/*writer*, defaulting to stdio.

    Args:
        reader: Input stream; ``sys.stdin`` when omitted.
        writer: Output stream; ``sys.stdout`` when omitted.
    """
    self._reader = reader
    self._writer = writer
```

</PySourceCode>

<div >

<PyParameter name={"reader"} type={"TextIO | None"} value={"None"}>

Input stream; ``sys.stdin`` when omitted.

</PyParameter>
<PyParameter name={"writer"} type={"TextIO | None"} value={"None"}>

Output stream; ``sys.stdout`` when omitted.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"ask"} type={"(self, prompt) -> str"}>

Write the prompt, then read one line without blocking the loop.

<PySourceCode >

```python
async def ask(self, prompt: str) -> str:
    """Write the prompt, then read one line without blocking the loop."""
    out = self._out
    out.write(prompt)
    out.flush()
    return await asyncio.to_thread(self._read_line)
```

</PySourceCode>

<div >

<PyParameter name={"prompt"} type={"str"} value={null} />

</div>

<PyFunctionReturn type={"str"} />

</PyFunction>

<PyFunction name={"show"} type={"(self, text) -> None"}>

Write *text* and a newline to the output stream.

<PySourceCode >

```python
def show(self, text: str) -> None:
    """Write *text* and a newline to the output stream.

    Args:
        text: The line to print.
    """
    out = self._out
    out.write(f'{text}\n')
    out.flush()
```

</PySourceCode>

<div >

<PyParameter name={"text"} type={"str"} value={undefined}>

The line to print.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
