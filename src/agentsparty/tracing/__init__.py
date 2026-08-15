"""Observability for protocol sessions: domain signals, spans and sinks.

``SqliteTracer`` is deliberately not re-exported — same reasoning as
``agentsparty.llm`` not re-exporting provider backends: a sink that touches a
database stays an explicit import::

    from agentsparty.tracing.sqlite import SqliteTracer
"""

from agentsparty.tracing._folds import text_of, usage_of
from agentsparty.tracing.facet import (
    EVERYTHING,
    FAILURE,
    MODEL,
    NOTHING,
    SESSION,
    SIGNAL_NAMES,
    STEP,
    TOOL,
    Facet,
    SignalName,
    facet,
)
from agentsparty.tracing.memory import MemoryTracer
from agentsparty.tracing.model import TracedModel, traced
from agentsparty.tracing.queue import QueueTracer, Watch, watching
from agentsparty.tracing.scope import (
    NULL_SCOPE,
    Scope,
    counting_ids,
    current,
    new_scope,
    uuid_ids,
)
from agentsparty.tracing.signals import (
    Delivered,
    Description,
    Failed,
    Forked,
    ModelAnswered,
    ModelCalled,
    ModelCorrected,
    ModelStreamed,
    Recalled,
    Selected,
    SessionCancelled,
    SessionFinished,
    SessionStarted,
    Signal,
    StepStarted,
    ToolAnswered,
    ToolCalled,
    Unfolded,
    describe,
)
from agentsparty.tracing.stream import StreamTracer
from agentsparty.tracing.types import (
    NULL_TRACER,
    Event,
    Fanout,
    Mapped,
    NoTracer,
    Span,
    SpanId,
    Tracer,
    fanout,
    mapped,
)

__all__ = [
    'EVERYTHING',
    'FAILURE',
    'MODEL',
    'NOTHING',
    'NULL_SCOPE',
    'NULL_TRACER',
    'SESSION',
    'SIGNAL_NAMES',
    'STEP',
    'TOOL',
    'Delivered',
    'Description',
    'Event',
    'Facet',
    'Failed',
    'Fanout',
    'Forked',
    'Mapped',
    'MemoryTracer',
    'ModelAnswered',
    'ModelCalled',
    'ModelCorrected',
    'ModelStreamed',
    'NoTracer',
    'QueueTracer',
    'Recalled',
    'Scope',
    'Selected',
    'SessionCancelled',
    'SessionFinished',
    'SessionStarted',
    'Signal',
    'SignalName',
    'Span',
    'SpanId',
    'StepStarted',
    'StreamTracer',
    'ToolAnswered',
    'ToolCalled',
    'TracedModel',
    'Tracer',
    'Unfolded',
    'Watch',
    'counting_ids',
    'current',
    'describe',
    'facet',
    'fanout',
    'mapped',
    'new_scope',
    'text_of',
    'traced',
    'usage_of',
    'uuid_ids',
    'watching',
]
