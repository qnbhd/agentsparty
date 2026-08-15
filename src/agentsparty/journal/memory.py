"""In-memory journal for tests, doctests and forking a script by hand."""

from __future__ import annotations

from collections.abc import Iterable

from agentsparty.journal.types import Decision, Script, _check_append

__all__ = ['MemoryJournal']


class MemoryJournal:
    """Journal that keeps every decision in memory, in recording order."""

    def __init__(self, decisions: Iterable[Decision] = ()) -> None:
        """Start from *decisions*, empty by default.

        Preloading is how a session forks: ``MemoryJournal(script.upto(k).decisions)``
        replays the causal prefix and then goes live.

        Args:
            decisions: Decisions to preload (free interleaving across tracks).

        Raises:
            JournalError: if *decisions* is not a valid multi-track script.
        """
        self._script = Script.of(decisions)

    def script(self) -> Script:
        """Everything decided so far, one word per track."""
        return self._script

    def append(self, decision: Decision) -> None:
        """Append *decision* to the recorded list.

        Args:
            decision: The alt to record.
        """
        _check_append(self._script, decision)
        self._script = Script.of((*self._script.decisions, decision))
