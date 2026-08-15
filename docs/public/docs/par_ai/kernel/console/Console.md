# Console (/docs/agentsparty/kernel/console/Console)

Line-oriented text seam: everything the CLI needs from a terminal.

## Functions

<PyFunction name={"ask"} type={"(self, prompt) -> str"}>

Write *prompt* and return one line of user input.

<PySourceCode >

```python
async def ask(self, prompt: str) -> str:
    """Write *prompt* and return one line of user input.

    Args:
        prompt: The text to show before reading input.
    """
    ...
```

</PySourceCode>

<div >

<PyParameter name={"prompt"} type={"str"} value={undefined}>

The text to show before reading input.

</PyParameter>

</div>

<PyFunctionReturn type={"str"} />

</PyFunction>

<PyFunction name={"show"} type={"(self, text) -> None"}>

Print *text* followed by a newline.

<PySourceCode >

```python
def show(self, text: str) -> None:
    """Print *text* followed by a newline.

    Args:
        text: The line to print.
    """
    ...
```

</PySourceCode>

<div >

<PyParameter name={"text"} type={"str"} value={undefined}>

The line to print.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
