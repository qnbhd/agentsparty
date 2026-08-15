"""Which side of a session to watch: named subsets of the signal catalogue.

A facet is a *set of signal names*, never a tag stored on an event. The
``Signal`` union is closed and :func:`~agentsparty.tracing.signals.describe`
covers it, so the catalogue below is finite — which is what makes ``~``
always defined.

What is deliberately absent: a ``custom`` facet. The industry needs one
because its event set is open; agentsparty's is closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from agentsparty.tracing.signals import Signal, describe

__all__ = [
    'EVERYTHING',
    'FAILURE',
    'MODEL',
    'NOTHING',
    'SESSION',
    'SIGNAL_NAMES',
    'STEP',
    'TOOL',
    'Facet',
    'SignalName',
    'facet',
]

_SESSION: Final = frozenset(
    (
        'session.started',
        'session.finished',
        'session.cancelled',
        'session.unfolded',
        'session.forked',
    ),
)
_STEP: Final = frozenset(
    ('step.started', 'step.selected', 'step.recalled', 'step.delivered'),
)
_MODEL: Final = frozenset(
    ('model.called', 'model.answered', 'model.streamed', 'model.corrected'),
)
_TOOL: Final = frozenset(('tool.called', 'tool.answered'))
_FAILURE: Final = frozenset(('failed',))

SignalName: TypeAlias = Literal[
    'session.started',
    'session.finished',
    'session.cancelled',
    'session.unfolded',
    'session.forked',
    'step.started',
    'step.selected',
    'step.recalled',
    'step.delivered',
    'model.called',
    'model.answered',
    'model.streamed',
    'model.corrected',
    'tool.called',
    'tool.answered',
    'failed',
]

SIGNAL_NAMES: Final[frozenset[str]] = _SESSION | _STEP | _MODEL | _TOOL | _FAILURE
"""Every stable name :func:`~agentsparty.tracing.signals.describe` can produce.

The five parts above partition it, so the named facets below cover it without
overlap. ``tests/tracing/test_facet.py`` fails if a signal is added to
:mod:`agentsparty.tracing.signals` and not classified here.
"""


@dataclass(frozen=True, slots=True)
class Facet:
    """A side of a session one can watch: a subset of :data:`SIGNAL_NAMES`.

    Facets combine like sets: ``|`` is union, ``&`` is intersection, ``~`` is
    complement and ``<=`` is inclusion. That is the whole of what the industry
    spells as six methods: ``stream.llm``, ``stream.tools``, … and
    ``interleave([...])``, which is just ``|``.

    A facet carries no data about a signal beyond membership, which is why
    projecting a trace onto one loses nothing but the events it excludes.
    """

    names: frozenset[str]

    def __post_init__(self) -> None:
        """Reject a name no signal can produce.

        Without this, ``~`` would not always be defined: a facet holding an
        unknown name would have a complement that is not a subset of the
        catalogue.

        The check covers dynamically built sets; literal typos are rejected by
        the :func:`facet` signature before runtime.

        Raises:
            ValueError: if a name is not in :data:`SIGNAL_NAMES`.
        """
        unknown = sorted(self.names - SIGNAL_NAMES)
        if unknown:
            names = ', '.join(unknown)
            raise ValueError(f'not a signal name: {names}')

    def __contains__(self, signal: Signal) -> bool:
        """Whether this facet watches *signal*.

        Args:
            signal: The signal to classify.
        """
        return describe(signal).name in self.names

    def __or__(self, other: Facet) -> Facet:
        """The facet watching what either of the two watches.

        Args:
            other: The facet to join with.
        """
        return Facet(self.names | other.names)

    def __and__(self, other: Facet) -> Facet:
        """The facet watching what both of them watch.

        Args:
            other: The facet to meet with.
        """
        return Facet(self.names & other.names)

    def __invert__(self) -> Facet:
        """The facet watching every name this one leaves out."""
        return Facet(SIGNAL_NAMES - self.names)

    def __le__(self, other: Facet) -> bool:
        """Whether every name here is also watched by *other*.

        Args:
            other: The facet to compare against.
        """
        return self.names <= other.names


SESSION: Final = Facet(_SESSION)
"""The session's own life: started, finished, and each recursion unfolding."""

STEP: Final = Facet(_STEP)
"""One interaction node: offered, chosen or recalled, delivered."""

MODEL: Final = Facet(_MODEL)
"""Everything a language model did, including streamed fragments."""

TOOL: Final = Facet(_TOOL)
"""A toolbox running a tool and naming its reply branch."""

FAILURE: Final = Facet(_FAILURE)
"""A span whose body raised. Cross-cutting: any span can produce it."""

EVERYTHING: Final = Facet(SIGNAL_NAMES)
"""The facet watching every signal: the whole timeline."""

NOTHING: Final = Facet(frozenset())
"""The facet watching no signals; ``~EVERYTHING``."""


def facet(*names: SignalName) -> Facet:
    """The facet watching exactly *names*.

    For the sides that are not one of the named facets — a single signal,
    say::

        tokens = facet('model.streamed')

    Args:
        *names: Stable signal names, as produced by
            :func:`~agentsparty.tracing.signals.describe`.

    Raises:
        ValueError: if a name is not in :data:`SIGNAL_NAMES`.
    """
    return Facet(frozenset(names))
