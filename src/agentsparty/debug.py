"""Human-readable sections of a session, written to a :class:`Console`.

This module prints; it does not decide anything.  It is the printing twin of
``agentsparty.tracing``, which is the machine-readable one.  Nothing inside
``agentsparty`` imports it: a library that prints from its own guts is a library
you cannot embed.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Final

from agentsparty._utils.assertions import post, safe_assert
from agentsparty.kernel.console import Console, StreamConsole
from agentsparty.participant import Envelope
from agentsparty.protocol import SessionType, project_all, render
from agentsparty.protocol import duties as _duties
from agentsparty.tracing import Event, describe

__all__ = ['Report']

_DEFAULT_CONSOLE: Final = StreamConsole()


def _envelope_line(envelope: Envelope) -> str:
    payload = '' if envelope.payload is None else f' {envelope.payload!r}'
    sender = envelope.sender.name
    receiver = envelope.receiver.name
    return f'{sender}:{envelope.label} -> {receiver}{payload}'


def _step(envelope: Envelope) -> str:
    sender = envelope.sender.name
    return f'{sender}:{envelope.label}'


def _duty_lines(node: SessionType) -> Iterator[str]:
    for role, endpoint in project_all(node):
        for duty in _duties(endpoint):
            role_name = role.name
            label = duty.label.name
            receiver = duty.receiver.name
            yield f'{role_name}: {label} -> {receiver}'


def _fact_line(item: tuple[str, int]) -> str:
    name, count = item
    return f'{name}: {count}'


def _counted(events: Iterable[Event]) -> dict[str, int]:
    """Count signal names in order of first appearance."""
    counts: dict[str, int] = {}
    event_count = 0
    for event in events:
        name = describe(event.signal).name
        counts[name] = counts.get(name, 0) + 1
        event_count += 1
    post(expr=sum(counts.values()) == event_count)
    return counts


class Report:
    """Titled sections of a session, written to a ``Console``."""

    def __init__(self, console: Console | None = None) -> None:
        """Create a report writing to *console*, or the process stdout."""
        self._console = _DEFAULT_CONSOLE if console is None else console

    def protocol(self, node: SessionType, *, title: str = 'protocol') -> None:
        """Write the rendered protocol as one titled section."""
        # Deliberately does not project: projection is a check, not a print.
        self._section(title, [render(node)])

    def conversation(
        self,
        envelopes: Iterable[Envelope],
        *,
        title: str = 'conversation',
    ) -> None:
        """Write one formatted line for each delivered envelope."""
        self._section(title, map(_envelope_line, envelopes))

    def skeleton(
        self,
        envelopes: Iterable[Envelope],
        *,
        title: str = 'skeleton',
    ) -> None:
        """Write the sender and label of each envelope on one line."""
        self._section(title, ['  '.join(map(_step, envelopes))])

    def duties(self, node: SessionType, *, title: str = 'duties') -> None:
        """Write each role's authored message duties."""
        self._section(title, _duty_lines(node))

    def facts(
        self,
        events: Iterable[Event],
        *,
        title: str = 'run facts',
    ) -> None:
        """Write counts of signal names in first-seen order."""
        counts = _counted(events)
        self._section(title, map(_fact_line, counts.items()))

    def note(self, *lines: str, title: str) -> None:
        """Write prose lines as a titled section."""
        self._section(title, lines)

    @contextmanager
    def refusing(
        self,
        expected: type[Exception],
        *,
        title: str,
    ) -> Iterator[None]:
        """Report and suppress *expected* errors raised by the body."""
        self._console.show(f'=== {title} ===')
        try:
            yield
        except expected as error:
            self._console.show(f'{type(error).__name__}: {error}')
            return
        safe_assert(expr=False, message=f'{title}: expected {expected.__name__}')

    def _section(self, title: str, lines: Iterable[str]) -> None:
        self._console.show(f'=== {title} ===')
        for line in lines:
            self._console.show(line)
