"""What a recorded session adds up to: folds over events.

Two folds live here because both just accumulate with ``+``: a bill adds on
:class:`~agentsparty.llm.types.Usage`, a text adds on ``str``. Both read what a
tracer already recorded and hold no state of their own; this is where the
industry puts a callback handler and a context manager.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping

from agentsparty.llm.types import Answer, ModelId, Usage
from agentsparty.tracing.signals import ModelAnswered, ModelStreamed
from agentsparty.tracing.types import Event, SpanId


def _answers(events: Iterable[Event]) -> Iterator[Answer]:
    """Every answer recorded in *events*, in the order they were recorded."""
    for event in events:
        match event.signal:
            case ModelAnswered(answer=answer):
                yield answer
            case _:
                pass


def usage_of(events: Iterable[Event]) -> Mapping[ModelId, Usage]:
    """What each model was billed across *events*.

    A pure fold: it reads what a tracer already recorded and holds no state of
    its own. This is where the industry puts a callback handler and a context
    manager; agentsparty needs neither, because the receipts are already in the
    trace and bills add up.

    Args:
        events: Recorded events, from any tracer.

    Returns:
        One total per model that answered; models that never answered are
        absent rather than present with an empty bill.
    """
    billed: defaultdict[ModelId, Usage] = defaultdict(Usage)
    for answer in _answers(events):
        billed[answer.model] += answer.usage
    return dict(billed)


def _fragments(events: Iterable[Event]) -> Iterator[tuple[SpanId, str]]:
    """Every streamed fragment in *events*, with the model span it came from."""
    for event in events:
        match event.signal:
            case ModelStreamed(delta=delta):
                yield event.span.id, delta
            case _:
                pass


def text_of(events: Iterable[Event]) -> Mapping[SpanId, str]:
    """What each model span said, assembled from the fragments it streamed.

    The industry's ``get_full_text()``, as a pure fold rather than a buffer on
    a stream object. An adapter that streams honestly satisfies

    ``text_of(events)[span] == answer.text``

    for the ``ModelAnswered`` that closes that span. agentsparty states that law and
    tests it against its own stubs, but cannot enforce it: the fragments are
    the adapter's word, and half a JSON payload decodes to nothing either way.

    Args:
        events: Recorded events, from any tracer.

    Returns:
        One assembled text per model span that streamed; spans that streamed
        nothing are absent rather than present with an empty string.
    """
    said: defaultdict[SpanId, str] = defaultdict(str)
    for span, fragment in _fragments(events):
        said[span] += fragment
    return dict(said)
