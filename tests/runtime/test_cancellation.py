"""Session-level laws of cancellation: every bound participant is told once."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from agentsparty.journal import ROOT_TRACK, Decision, MemoryJournal, StepIndex
from agentsparty.kernel.budget import Allowance
from agentsparty.kernel.errors import JournalError, RecursionLimitError, StepLimitError
from agentsparty.kernel.role import Role, roles
from agentsparty.machine import Decide, Machine, View
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import (
    Label,
    Number,
    Text,
    alt,
    case,
    list_of,
    msg,
    project,
    rec,
    seq,
    var,
)
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.protocol.session import SessionType
from agentsparty.runtime import AgentRuntime
from agentsparty.toolbox import Toolbox, reply, tool
from agentsparty.tracing import MemoryTracer
from agentsparty.tracing.signals import Failed, SessionFinished
from tests.conftest import Stub, stub


@dataclass
class Rude:
    """Participant whose ``cancel`` raises; must not silence the others."""

    role: Role
    endpoint_contract: EndpointType
    cancelled: list[Cancelled] = field(default_factory=list)

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        raise AssertionError('Rude is never asked to select')

    async def offer(self, envelope: Envelope) -> None:
        pass

    async def recall(self, envelope: Envelope) -> None:
        pass

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled.append(notice)
        raise RuntimeError('cleanup failed')


def _three_role_proto() -> SessionType:
    A, B, C = roles('A', 'B', 'C')
    return (msg[A, B]('One', Text) >> msg[A, C]('Two', Text)).close()


async def test_every_bound_participant_is_told_exactly_once() -> None:
    """A session of three roles, failing on any step, tells each one once."""
    A, B, C = roles('A', 'B', 'C')
    proto = _three_role_proto()
    a = stub(proto, A, Choice(Label('One'), '1'))
    b = stub(proto, B)
    c = stub(proto, C)
    runtime = AgentRuntime(proto, [a, b, c], allowance=Allowance(steps=1))
    with pytest.raises(StepLimitError):
        await runtime.run()
    for participant in (a, b, c):
        assert len(participant.cancelled) == 1


def _step_crash() -> tuple[AgentRuntime, tuple[Stub, Stub, Stub]]:
    A, B, C = roles('A', 'B', 'C')
    proto = _three_role_proto()
    a = stub(proto, A, Choice(Label('One'), '1'))
    b = stub(proto, B)
    c = stub(proto, C)
    return AgentRuntime(proto, [a, b, c], allowance=Allowance(steps=1)), (a, b, c)


def _recursion_crash() -> tuple[AgentRuntime, tuple[Stub, Stub]]:
    A, B = roles('A', 'B')
    proto = rec('t', alt[A, B](case('loop') >> var('t'), case('done'))).close()
    a = stub(proto, A)
    b = stub(proto, B)
    return AgentRuntime(proto, [a, b], allowance=Allowance(unfoldings=0)), (a, b)


@pytest.mark.parametrize(
    ('setup', 'error_type'),
    [(_step_crash, StepLimitError), (_recursion_crash, RecursionLimitError)],
)
async def test_the_notice_names_the_exception(
    setup,
    error_type: type[StepLimitError] | type[RecursionLimitError],
) -> None:
    """The notice carries the failure as it would be written down."""
    runtime, participants = setup()
    with pytest.raises(error_type):
        await runtime.run()
    for participant in participants:
        [notice] = participant.cancelled
        assert notice.reason.startswith(error_type.__name__)


async def test_the_original_exception_is_re_raised_unchanged() -> None:
    """The caller sees the exact exception, not a cancellation wrapper."""
    A, B, C = roles('A', 'B', 'C')
    proto = _three_role_proto()
    a = stub(proto, A, Choice(Label('One'), '1'))
    b = stub(proto, B)
    c = stub(proto, C)
    runtime = AgentRuntime(proto, [a, b, c], allowance=Allowance(steps=1))
    with pytest.raises(StepLimitError) as excinfo:
        await runtime.run()
    # The exception type is StepLimitError (not a cancel wrapper). After the
    # first step A and B have participated, so C is named as idle.
    message = str(excinfo.value)
    assert message.startswith(
        'step allowance exhausted (limit=1); pass Allowance(steps=None) for unbounded steps',
    )
    assert 'Roles that never sent or received in this session: C' in message


async def test_a_broken_cancel_does_not_silence_the_others() -> None:
    """A failing cancel is recorded; the broadcast and the cause survive."""
    A, B, C = roles('A', 'B', 'C')
    proto = _three_role_proto()
    rude = Rude(A, project(proto, A))
    b = stub(proto, B)
    c = stub(proto, C)
    tracer = MemoryTracer()
    runtime = AgentRuntime(
        proto,
        [rude, b, c],
        allowance=Allowance(steps=0),
        tracer=tracer,
    )
    with pytest.raises(StepLimitError):
        await runtime.run()
    assert len(rude.cancelled) == 1
    assert len(b.cancelled) == 1
    assert len(c.cancelled) == 1
    failures: list[str] = []
    for event in tracer.events:
        match event.signal:
            case Failed(error=error):
                failures.append(error)
    assert any(
        f'`{rude.role.name}` could not be told' in text and 'RuntimeError: cleanup failed' in text
        for text in failures
    )


async def test_finished_and_cancelled_are_the_two_ways_a_session_ends() -> None:
    """Reaching end records ``session.finished``; a roll-up ``session.cancelled``."""
    A, B = roles('A', 'B')
    ok_proto = msg[A, B]('Hi', Text).close()
    ok_tracer = MemoryTracer()
    ok_a = stub(ok_proto, A, Choice(Label('Hi'), 'yo'))
    ok_b = stub(ok_proto, B)
    await AgentRuntime(ok_proto, [ok_a, ok_b], tracer=ok_tracer).run()
    assert 'session.finished' in ok_tracer.names()
    assert 'session.cancelled' not in ok_tracer.names()
    assert ok_tracer.events[-1].signal == SessionFinished(messages=1)
    assert ok_a.cancelled == []
    assert ok_b.cancelled == []

    X, Y, Z = roles('A', 'B', 'C')
    bad_proto = (msg[X, Y]('One', Text) >> msg[X, Z]('Two', Text)).close()
    bad_tracer = MemoryTracer()
    bad_a = stub(bad_proto, X, Choice(Label('One'), '1'))
    bad_b = stub(bad_proto, Y)
    bad_c = stub(bad_proto, Z)
    with pytest.raises(StepLimitError):
        await AgentRuntime(
            bad_proto,
            [bad_a, bad_b, bad_c],
            allowance=Allowance(steps=0),
            tracer=bad_tracer,
        ).run()
    assert 'session.cancelled' in bad_tracer.names()
    assert 'session.finished' not in bad_tracer.names()
    for participant in (bad_a, bad_b, bad_c):
        assert len(participant.cancelled) == 1


async def test_cancellation_leaves_the_journal_untouched() -> None:
    """A roll-up is not a rollback; recorded decisions replay on the next run."""
    A, B = roles('A', 'B')
    proto = (msg[A, B]('One', Text) >> msg[B, A]('Two', Text) >> msg[A, B]('Three', Text)).close()
    journal = MemoryJournal()
    a = stub(proto, A, Choice(Label('One'), '1'), Choice(Label('Three'), '3'))
    b = stub(proto, B, Choice(Label('Two'), '2'))
    runtime = AgentRuntime(proto, [a, b], journal=journal, allowance=Allowance(steps=2))
    with pytest.raises(StepLimitError):
        await runtime.run()
    assert journal.script().length == 2

    a2 = stub(proto, A, Choice(Label('Three'), '3'))
    b2 = stub(proto, B)
    trace = await AgentRuntime(proto, [a2, b2], journal=journal).run()
    assert [envelope.label.name for envelope in trace] == ['One', 'Two', 'Three']
    assert len(a2.recalled) + len(b2.recalled) == 2  # the recorded decisions


async def test_a_complete_replay_accepts_an_exact_journal() -> None:
    """A full replay has exactly as many envelopes as recorded decisions."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Only', Text).close()
    journal = MemoryJournal(
        [Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('Only'), 'str', 'only')],
    )
    a = stub(proto, A)
    b = stub(proto, B)

    trace = await AgentRuntime(proto, [a, b], journal=journal).run()

    assert [envelope.label.name for envelope in trace] == ['Only']
    assert journal.script().length == len(trace)


async def test_a_stale_journal_reports_the_record_count() -> None:
    """A journal with extra decisions reports the replay mismatch precisely."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Only', Text).close()
    journal = MemoryJournal(
        [
            Decision(StepIndex(ROOT_TRACK, 1), A, B, Label('Only'), 'str', 'only'),
            Decision(StepIndex(ROOT_TRACK, 2), A, B, Label('Only'), 'str', 'only'),
        ],
    )
    a = stub(proto, A)
    b = stub(proto, B)

    with pytest.raises(
        JournalError,
        match='journal records 2 decisions on track',
    ):
        await AgentRuntime(proto, [a, b], journal=journal).run()


def _service() -> tuple[SessionType, Role, Role, Role]:
    User, Planner, Tools = roles('User', 'Planner', 'Tools')
    proto = seq(
        msg[User, Planner]('ask', Text),
        alt[Planner, Tools](
            case('search', Text)
            >> alt[Tools, Planner](
                case('hits', list_of(Text)),
                case('offline', Text),
            )
            >> msg[Planner, User]('answer', Text),
            case('calc', Text)
            >> msg[Tools, Planner]('value', Number)
            >> msg[Planner, User]('answer', Text),
        ),
    ).close()
    return proto, User, Planner, Tools


def _asking() -> Decide:
    def ask(_view: View) -> Choice:
        return Choice(Label('ask'), 'what is mpst?')

    return ask


def _plan(first: str) -> Decide:
    def decide(view: View) -> Choice:
        labels = {str(label) for label in view.offered}
        if first in labels:
            return Choice(Label(first), 'mpst')
        return Choice(Label('answer'), 'done')

    return decide


async def _search(query: str) -> Choice:
    return reply('hits', [f'{query}-1', f'{query}-2'])


async def _calc(_expression: str) -> Choice:
    return reply('value', 42)


async def test_a_cancelled_toolbox_is_reusable() -> None:
    """A toolbox owing a request is freed by cancel and accepts a new runtime."""
    proto, User, Planner, Tools = _service()
    box = Toolbox(
        Tools,
        proto,
        [tool('search', Text, _search), tool('calc', Text, _calc)],
    )

    async def run_once(allowance: Allowance) -> list[Envelope]:
        return await AgentRuntime(
            proto,
            [
                Machine(User, proto, _asking()),
                Machine(Planner, proto, _plan('search')),
                box,
            ],
            allowance=allowance,
        ).run()

    with pytest.raises(StepLimitError):
        await run_once(Allowance(steps=2))  # fails before the tool answers
    trace = await run_once(Allowance())
    assert [envelope.label.name for envelope in trace] == [
        'ask',
        'search',
        'hits',
        'answer',
    ]
