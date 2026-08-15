"""Property tests: resume reproduces a live run."""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings

from agentsparty.journal import NULL_JOURNAL, ROOT_TRACK, MemoryJournal, StepIndex
from agentsparty.journal.types import Decision
from agentsparty.kernel.errors import JournalError, RecursionLimitError
from agentsparty.kernel.role import roles
from agentsparty.protocol import Integer, Label, Text, msg, participants, project
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing import MemoryTracer
from tests.journal.conftest import Peer, is_projectable, session
from tests.protocol.strategies import (
    branching_root_protocols,
    guarded_recursive_protocols,
    linear_protocols,
)


@given(proto=linear_protocols())
@settings(max_examples=40, deadline=None)
async def test_resume_at_every_prefix_reproduces_the_run(proto) -> None:
    full = MemoryJournal()
    baseline, _ = await session(proto, full)
    recorded = full.script()
    for k in range(recorded.length + 1):
        prefix = () if k == 0 else recorded.upto(StepIndex(ROOT_TRACK, k)).decisions
        trace, _ = await session(proto, MemoryJournal(prefix))
        assert trace == baseline


@given(proto=linear_protocols())
@settings(max_examples=40, deadline=None)
async def test_full_journal_makes_zero_selects(proto) -> None:
    full = MemoryJournal()
    baseline, _ = await session(proto, full)
    recorded = full.script()
    trace, peers = await session(proto, MemoryJournal(recorded.decisions))
    assert trace == baseline
    assert all(peer.selects == 0 for peer in peers)


@given(proto=branching_root_protocols())
@settings(max_examples=30, deadline=None)
async def test_run_is_idempotent_on_a_full_journal(proto) -> None:
    assume(is_projectable(proto))
    journal = MemoryJournal()
    first, _ = await session(proto, journal)
    length = journal.script().length
    peers = [Peer(role, project(proto, role)) for role in participants(proto)]
    second = await AgentRuntime(proto, peers, journal=journal).run()
    assert second == first
    assert journal.script().length == length


@given(proto=linear_protocols())
@settings(max_examples=40, deadline=None)
async def test_null_journal_matches_memory_journal(proto) -> None:
    with_memory, _ = await session(proto, MemoryJournal())
    with_null, _ = await session(proto, NULL_JOURNAL)
    assert with_null == with_memory


@given(proto=linear_protocols())
@settings(max_examples=40, deadline=None)
async def test_sender_recalls_and_receiver_receives(proto) -> None:
    full = MemoryJournal()
    baseline, _ = await session(proto, full)
    trace, peers = await session(proto, MemoryJournal(full.script().decisions))
    assert trace == baseline
    by_role = {peer.role.name: peer for peer in peers}
    for envelope in trace:
        assert envelope in by_role[envelope.sender.name].recalled
        assert envelope in by_role[envelope.receiver.name].received
    assert sum(len(peer.recalled) for peer in peers) == len(trace)


@given(proto=guarded_recursive_protocols())
@settings(max_examples=25, deadline=None)
async def test_replay_does_not_consume_recursion_budget(proto) -> None:
    from agentsparty.kernel.budget import UNBOUNDED, Allowance

    assume(is_projectable(proto))
    full = MemoryJournal()
    baseline, _ = await session(proto, full, allowance=UNBOUNDED)
    recorded = full.script()
    # Budget 0 would fail on any live unfolding; full replay must succeed.
    try:
        await session(
            proto,
            MemoryJournal(recorded.decisions),
            allowance=Allowance(unfoldings=0),
        )
    except RecursionLimitError as exc:  # pragma: no cover - regression
        raise AssertionError('replay charged the recursion budget') from exc
    assert baseline  # session always delivers at least the done arm


@given(proto=linear_protocols())
@settings(max_examples=20, deadline=None)
async def test_recalled_signal_replaces_selected_on_replay(proto) -> None:
    full = MemoryJournal()
    baseline, _ = await session(proto, full)
    if not baseline:
        return
    mem = MemoryTracer()
    peers = [Peer(role, project(proto, role)) for role in participants(proto)]
    await AgentRuntime(
        proto,
        peers,
        journal=MemoryJournal(full.script().decisions),
        tracer=mem,
    ).run()
    names = mem.names()
    assert 'step.selected' not in names
    assert names.count('step.recalled') == len(baseline)


@given(proto=branching_root_protocols())
@settings(max_examples=30, deadline=None)
async def test_resume_at_every_prefix_reproduces_the_run_branching(proto) -> None:
    assume(is_projectable(proto))
    full = MemoryJournal()
    baseline, _ = await session(proto, full)
    recorded = full.script()
    for k in range(recorded.length + 1):
        prefix = () if k == 0 else recorded.upto(StepIndex(ROOT_TRACK, k)).decisions
        trace, _ = await session(proto, MemoryJournal(prefix))
        assert trace == baseline


async def test_recall_bad_raw_raises_journal_error() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Integer).close()
    # Same digest, but the raw does not decode under the declared codec.
    decision = Decision(
        StepIndex(ROOT_TRACK, 1),
        A,
        B,
        Label('Hi'),
        'int',
        'not-an-int',
    )
    journal = MemoryJournal([decision])
    with pytest.raises(JournalError, match='does not decode'):
        await session(proto, journal)


async def test_overlong_journal_raises() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Only', Text).close()
    decisions = [
        Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('Only'), 'str', 'x'),
        Decision(StepIndex(ROOT_TRACK, 2), A, B, Label('Only'), 'str', 'y'),
    ]
    journal = MemoryJournal(decisions)
    with pytest.raises(JournalError, match='delivered only'):
        await session(proto, journal)
