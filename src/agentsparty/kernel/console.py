"""Line-oriented console seam for CLI participants."""

from __future__ import annotations

import asyncio
import sys
from typing import Protocol, TextIO


class Console(Protocol):
    """Line-oriented text seam: everything the CLI needs from a terminal."""

    async def ask(self, prompt: str) -> str:
        """Write *prompt* and return one line of user input.

        Args:
            prompt: The text to show before reading input.
        """
        ...

    def show(self, text: str) -> None:
        """Print *text* followed by a newline.

        Args:
            text: The line to print.
        """
        ...


class StreamConsole:
    """Console backed by text streams, defaulting to the process stdio.

    Streams are resolved on every call rather than captured in ``__init__``:
    ``sys.stdout`` is routinely replaced after construction (test capture,
    output redirection), and a captured handle would silently ignore that.
    """

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

    async def ask(self, prompt: str) -> str:
        """Write the prompt, then read one line without blocking the loop."""
        out = self._out
        out.write(prompt)
        out.flush()
        return await asyncio.to_thread(self._read_line)

    def show(self, text: str) -> None:
        """Write *text* and a newline to the output stream.

        Args:
            text: The line to print.
        """
        out = self._out
        out.write(f'{text}\n')
        out.flush()

    @property
    def _in(self) -> TextIO:
        return sys.stdin if self._reader is None else self._reader

    @property
    def _out(self) -> TextIO:
        return sys.stdout if self._writer is None else self._writer

    def _read_line(self) -> str:
        line = self._in.readline()
        if not line:
            raise EOFError('console input closed')
        # Only the line terminator is removed; leading and trailing spaces
        # belong to the answer and are the caller's to interpret.
        return line.removesuffix('\n')


__all__ = ['Console', 'StreamConsole']
