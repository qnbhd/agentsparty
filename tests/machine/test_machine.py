"""Tests for the computed participant: purity, replay symmetry, errors."""

from __future__ import annotations

import pytest
from hypothesis import given

from agentsparty.journal import MemoryJournal
from agentsparty.kernel.errors import PayloadError, SelectionError
from agentsparty.kernel.role import roles
from agentsparty.machine import Machine, View
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import Label, Text, alt, case, msg, project, rec, var
from agentsparty.runtime import AgentRuntime
from tests._helpers import cancellable_envelopes


@given(
    envelopes=cancellable_envelopes(),
)
async def test_cancel_returns_a_machine_to_its_initial_state(
    envelopes: list[Envelope],
) -> None:
    """L8-m: a cancelled machine has seen nothing, and cancelling twice is one."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    machine = Machine(A, proto, lambda view: Choice(Label('unused')))
    for envelope in envelopes:
        await machine.offer(envelope)
    notice = Cancelled('StepLimitError: no budget')
    await machine.cancel(notice)
    assert machine.seen == ()
    await machine.cancel(notice)
    assert machine.seen == ()


def _count_sections(threshold: int = 2):
    """Decide Next until *threshold* Section envelopes are in *seen*."""

    def decide(view: View) -> Choice:
        sections = sum(1 for e in view.seen if e.label == Label('Section'))
        if sections >= threshold:
            return Choice(Label('Enough'))
        return Choice(Label('Next'))

    return decide


def test_decide_is_pure_without_session() -> None:
    """A policy runs on a hand-built View with no runtime."""
    A, B = roles('A', 'B')
    decide = _count_sections(2)
    empty = View((), B, (Label('Next'), Label('Enough')))
    assert decide(empty).label == Label('Next')

    one_section = View(
        (Envelope(A, B, Label('Section'), 's1'),),
        B,
        (Label('Next'), Label('Enough')),
    )
    assert decide(one_section).label == Label('Next')

    two_sections = View(
        (
            Envelope(A, B, Label('Section'), 's1'),
            Envelope(A, B, Label('Section'), 's2'),
        ),
        B,
        (Label('Next'), Label('Enough')),
    )
    assert decide(two_sections).label == Label('Enough')


async def test_seen_live_equals_seen_replay_and_decide_not_called() -> None:
    """Live seen == replay seen; full replay never calls decide."""
    A, B = roles('A', 'B')
    proto = (
        msg[A, B]('Ping', Text) >> alt[B, A](case('Ack'), case('Nack')) >> msg[A, B]('Done', Text)
    ).close()

    calls = {'n': 0}

    def decide(view: View) -> Choice:
        calls['n'] += 1
        return Choice(Label('Ack'))

    def always_text(view: View) -> Choice:
        # A always sends Text payloads for Ping/Done.
        offered = view.offered[0]
        return Choice(offered, 'x')

    live_journal = MemoryJournal()
    a_live = Machine(A, proto, always_text)
    b_live = Machine(B, proto, decide)
    live_trace = await AgentRuntime(proto, [a_live, b_live], journal=live_journal).run()
    live_seen_a = a_live.seen
    live_seen_b = b_live.seen
    live_calls = calls['n']
    assert live_calls >= 1
    assert live_trace

    # Full replay on a fresh machine: decide must not run.
    calls['n'] = 0
    a_replay = Machine(A, proto, always_text)
    b_replay = Machine(B, proto, decide)
    replay_trace = await AgentRuntime(
        proto,
        [a_replay, b_replay],
        journal=MemoryJournal(live_journal.script().decisions),
    ).run()
    assert calls['n'] == 0
    assert replay_trace == live_trace
    assert a_replay.seen == live_seen_a
    assert b_replay.seen == live_seen_b


async def test_two_identical_live_runs_yield_same_trace() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()

    def say_hi(view: View) -> Choice:
        return Choice(Label('Hi'), 'hello')

    async def run_once() -> list[Envelope]:
        a = Machine(A, proto, say_hi)
        b = Machine(B, proto, lambda view: Choice(Label('unused')))
        return await AgentRuntime(proto, [a, b]).run()

    assert await run_once() == await run_once()


async def test_unknown_label_raises_selection_error() -> None:
    A, B = roles('A', 'B')
    proto = alt[A, B](case('Yes'), case('No')).close()

    def bad(view: View) -> Choice:
        return Choice(Label('Maybe'))

    a = Machine(A, proto, bad)
    b = Machine(B, proto, lambda view: Choice(Label('unused')))
    with pytest.raises(SelectionError, match='not on offer'):
        await AgentRuntime(proto, [a, b]).run()


async def test_wrong_raw_payload_raises_payload_error() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()

    def bad_payload(view: View) -> Choice:
        return Choice(Label('Hi'), 123)  # Text expects str

    a = Machine(A, proto, bad_payload)
    b = Machine(B, proto, lambda view: Choice(Label('unused')))
    with pytest.raises(PayloadError):
        await AgentRuntime(proto, [a, b]).run()


async def test_own_send_counting_terminates_under_rec() -> None:
    """Policy: Stop after the third own Ping; terminates under rec."""
    A, B = roles('A', 'B')
    proto = rec(
        't',
        alt[A, B](
            case('Ping') >> var('t'),
            case('Stop'),
        ),
    ).close()

    def count_own_pings(view: View) -> Choice:
        pings = sum(1 for e in view.seen if e.label == Label('Ping') and e.sender == A)
        if pings >= 3:
            return Choice(Label('Stop'))
        return Choice(Label('Ping'))

    a = Machine(A, proto, count_own_pings)
    b = Machine(B, proto, lambda view: Choice(Label('unused')))
    trace = await AgentRuntime(proto, [a, b]).run()
    labels = [e.label.name for e in trace]
    assert labels == ['Ping', 'Ping', 'Ping', 'Stop']
    # After three Pings the machine has recorded them in seen (plus Stop).
    own_pings = [e for e in a.seen if e.label == Label('Ping')]
    assert len(own_pings) == 3


def test_machine_endpoint_contract_is_projection() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    m = Machine(A, proto, lambda view: Choice(Label('Hi'), 'x'))
    assert m.endpoint_contract == project(proto, A)
    assert m.role == A
