"""In-memory tracer for tests, doctests and assertions."""

from __future__ import annotations

from agentsparty.tracing.signals import describe
from agentsparty.tracing.types import Event

__all__ = ['MemoryTracer']


class MemoryTracer:
    """Tracer that keeps every event in memory, in recording order."""

    def __init__(self) -> None:
        """Start with an empty log."""
        self.events: list[Event] = []

    def record(self, event: Event) -> None:
        """Append *event* to :attr:`events`.

        Args:
            event: The event to keep.
        """
        self.events.append(event)

    def names(self) -> list[str]:
        """The signal name of every recorded event, in order."""
        return [describe(event.signal).name for event in self.events]
