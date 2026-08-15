"""Persistence for protocol sessions: the decisions a session cannot recompute.

A journal records one decision per delivered message — the label a participant
picked and the raw payload it authored. Everything else about a session is a
function of the protocol and that journal, so resuming is a replay, not a
restore.

``SqliteJournal`` is deliberately not re-exported — same reasoning as
``agentsparty.tracing`` not re-exporting ``SqliteTracer``: a sink that touches a
database stays an explicit import::

    from agentsparty.journal.sqlite import SqliteJournal
"""

from agentsparty.journal.jsonl import JsonlJournal
from agentsparty.journal.memory import MemoryJournal
from agentsparty.journal.types import (
    EMPTY_SCRIPT,
    FIRST_STEP,
    NULL_JOURNAL,
    ROOT_TRACK,
    Decision,
    Digest,
    Journal,
    NoJournal,
    Script,
    SessionId,
    StepIndex,
    Track,
    digest_of,
)

__all__ = [
    'EMPTY_SCRIPT',
    'FIRST_STEP',
    'NULL_JOURNAL',
    'ROOT_TRACK',
    'Decision',
    'Digest',
    'Journal',
    'JsonlJournal',
    'MemoryJournal',
    'NoJournal',
    'Script',
    'SessionId',
    'StepIndex',
    'Track',
    'digest_of',
]
