"""Tests for the answering participant: totality, replay, request locality."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.journal import NULL_JOURNAL, Journal, MemoryJournal
from agentsparty.kernel.errors import PayloadError, SelectionError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import roles
from agentsparty.machine import Decide, Machine, View
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import (
    Integer,
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
from agentsparty.protocol.language.endpoint import EndpointBranchCase, EndpointEnd
from agentsparty.runtime import AgentRuntime
from agentsparty.toolbox import Tool, Toolbox, reply, tool

User, Planner, Tools = roles('User', 'Planner', 'Tools')

PROTO = seq(
    msg[User, Planner]('ask', Text),
    alt[Planner, Tools](
        case('search', Text)
        >> alt[Tools, Planner](case('hits', list_of(Text)), case('offline', Text))
        >> msg[Planner, User]('answer', Text),
        case('calc', Text)
        >> msg[Tools, Planner]('value', Number)
        >> msg[Planner, User]('answer', Text),
    ),
).close()

_OFFLINE_TRACE_LABELS = ('ask', 'search', 'offline', 'answer')


def _plan(first: str, request: str = 'mpst') -> Decide:
    """Planner: ask the named tool once, then answer the user."""

    def decide(view: View) -> Choice:
        labels = {str(label) for label in view.offered}
        if first in labels:
            return Choice(Label(first), request)
        return Choice(Label('answer'), 'done')

    return decide


def _asking() -> Decide:
    def ask(view: View) -> Choice:
        return Choice(Label('ask'), 'what is mpst?')

    return ask


def _tools(record: list[object] | None = None) -> list[Tool[Any]]:
    """The search and calc tools; calls are logged into *record* when given."""

    async def search(query: str) -> Choice:
        if record is not None:
            record.append(('search', query))
        return reply('hits', [f'{query}-1', f'{query}-2'])

    async def calc(expression: str) -> Choice:
        if record is not None:
            record.append(('calc', expression))
        return reply('value', 42.0)

    return [tool('search', Text, search), tool('calc', Text, calc)]


def _toolbox(record: list[object] | None = None) -> Toolbox:
    """A Tools toolbox: search answers with two hits, calc with 42.0."""
    return Toolbox(Tools, PROTO, _tools(record))


def _answering_box(search: Callable[[str], Awaitable[Choice]]) -> Toolbox:
    """A Tools toolbox whose search tool answers as *search* does."""

    async def calc(expression: str) -> Choice:
        return reply('value', 1.0)

    return Toolbox(Tools, PROTO, [tool('search', Text, search), tool('calc', Text, calc)])


def _request(query: str) -> Envelope:
    """The envelope that asks the Tools role to search *query*."""
    return Envelope(Planner, Tools, Label('search'), query)


def _answer() -> Envelope:
    """The envelope a successful search answer would carry."""
    return Envelope(Tools, Planner, Label('hits'), ['mpst-1', 'mpst-2'])


def _replies() -> NonEmptyMap[Label, EndpointBranchCase]:
    """The reply branches the protocol offers for a search request."""
    return NonEmptyMap.of_pairs(
        [
            (Label('hits'), EndpointBranchCase(Label('hits'), list_of(Text), EndpointEnd())),
            (Label('offline'), EndpointBranchCase(Label('offline'), Text, EndpointEnd())),
        ],
    )


async def _run_with(
    box: Toolbox,
    journal: Journal = NULL_JOURNAL,
    request: str = 'mpst',
) -> list[Envelope]:
    """Run the protocol with *box* as the Tools participant."""
    return await AgentRuntime(
        PROTO,
        [
            Machine(User, PROTO, _asking()),
            Machine(Planner, PROTO, _plan('search', request)),
            box,
        ],
        journal=journal,
    ).run()


async def _run(
    journal: MemoryJournal,
    record: list[object] | None = None,
    request: str = 'mpst',
) -> list[Envelope]:
    """Run the protocol with a record-logging toolbox under *journal*."""
    return await _run_with(_toolbox(record), journal, request)


_requests = st.text(min_size=1, max_size=20)


@given(_requests)
async def test_replay_does_not_run_the_tool(request: str) -> None:
    """The effect happens once: in the run that recorded it."""
    live_calls: list[object] = []
    journal = MemoryJournal()
    live = await _run(journal, live_calls, request)

    replay_calls: list[object] = []
    replayed = await _run(
        MemoryJournal(journal.script().decisions),
        replay_calls,
        request,
    )
    assert live_calls == [('search', request)]
    assert replay_calls == []
    assert replayed == live


@given(_requests)
async def test_answer_depends_only_on_the_request(request: str) -> None:
    """The tool sees the request and nothing about the session around it."""
    seen: list[object] = []
    await _run(MemoryJournal(), seen, request)
    first = list(seen)
    seen.clear()
    await _run(MemoryJournal(), seen, request)
    assert first == [('search', request)]
    assert seen == first


async def test_run_yields_the_expected_trace() -> None:
    """A complete live run follows the protocol's successful search path."""
    trace = await _run(MemoryJournal())
    assert tuple(str(envelope.label) for envelope in trace) == (
        'ask',
        'search',
        'hits',
        'answer',
    )


def test_endpoint_contract_is_the_projection() -> None:
    box = _toolbox()
    assert box.endpoint_contract == project(PROTO, Tools)
    assert box.role == Tools


def test_missing_tool_is_rejected() -> None:
    async def search(query: str) -> Choice:
        return reply('hits', [])

    with pytest.raises(ValueError, match='no tool for: calc'):
        Toolbox(Tools, PROTO, [tool('search', Text, search)])


@pytest.mark.parametrize(
    ('names', 'message'),
    [
        (('search', 'calc', 'fetch'), 'never asked for: fetch'),
        (('search', 'search', 'calc'), 'duplicate'),
    ],
    ids=('extra', 'duplicate'),
)
def test_invalid_tool_collections_are_rejected(
    names: tuple[str, ...],
    message: str,
) -> None:
    async def anything(value: str) -> Choice:
        return reply('hits', [])

    with pytest.raises(ValueError, match=message):
        Toolbox(Tools, PROTO, [tool(name, Text, anything) for name in names])


def test_wrong_codec_is_rejected() -> None:
    async def anything(value: object) -> Choice:
        return reply('hits', [])

    with pytest.raises(ValueError, match='wrong payloads'):
        Toolbox(
            Tools,
            PROTO,
            [tool('search', Integer, anything), tool('calc', Text, anything)],
        )


def test_no_tools_is_rejected() -> None:
    with pytest.raises(ValueError, match='was given no tools'):
        Toolbox(Tools, PROTO, [])


def test_a_toolbox_may_not_speak_first() -> None:
    proto = msg[Tools, Planner]('hello', Text).close()

    async def anything(value: str) -> Choice:
        return reply('hello', 'x')

    with pytest.raises(ValueError, match='speaks first'):
        Toolbox(Tools, proto, [tool('hello', Text, anything)])


def test_an_unanswered_request_is_rejected() -> None:
    proto = msg[Planner, Tools]('note', Text).close()

    async def anything(value: str) -> Choice:
        return reply('note', None)

    with pytest.raises(ValueError, match='is not answered'):
        Toolbox(Tools, proto, [tool('note', Text, anything)])


def test_a_binder_between_request_and_answer_is_rejected() -> None:
    proto = alt[Planner, Tools](
        case('ping') >> rec('t', alt[Tools, Planner](case('pong') >> var('t'))),
    ).close()

    async def anything(value: None) -> Choice:
        return reply('pong')

    with pytest.raises(ValueError, match='is not answered'):
        Toolbox(Tools, proto, [tool('ping', Text, anything)])


async def test_select_with_no_request_raises() -> None:
    """select answers an owed request; an idle box must not be asked to."""
    box = _toolbox()
    with pytest.raises(AssertionError, match='was asked to answer nothing'):
        await box.select(Planner, _replies())


async def test_offer_twice_is_rejected() -> None:
    """offer takes one request at a time; a second one is a programmer error."""
    box = _toolbox()
    await box.offer(_request('mpst'))
    with pytest.raises(AssertionError, match='still owed'):
        await box.offer(_request('mpst'))


async def test_cancel_frees_the_slot() -> None:
    """a toolbox owing a request accepts a new one after cancel."""
    box = _toolbox()
    await box.offer(_request('mpst'))
    await box.cancel(Cancelled('StepLimitError: no budget'))
    await box.offer(_request('mpst'))
    with pytest.raises(AssertionError, match='still owed'):
        await box.offer(_request('mpst'))


async def _step(box: Toolbox, pending: str | None, verb: str, request: str) -> str | None:
    """Apply one automaton step; returns the request the box now owes."""
    if verb == 'offer':
        if pending is not None:
            with pytest.raises(AssertionError, match='still owed'):
                await box.offer(_request(request))
            return pending
        await box.offer(_request(request))
        return request
    if verb == 'select':
        if pending is None:
            with pytest.raises(AssertionError, match='was asked to answer nothing'):
                await box.select(Planner, _replies())
            return None
        chosen = await box.select(Planner, _replies())
        assert chosen.payload == [f'{pending}-1', f'{pending}-2']
        return None
    # recall and cancel drop the owed request, whichever state the box is in:
    if verb == 'recall':
        await box.recall(_answer())
    else:
        await box.cancel(Cancelled('no budget'))
    return None


async def _drive_slot_machine(word: list[tuple[str, str]]) -> tuple[Toolbox, str | None]:
    """Apply a generated word to a toolbox and its tiny reference model."""
    box = _toolbox()
    pending: str | None = None
    for verb, request in word:
        pending = await _step(box, pending, verb, request)
    return box, pending


async def _slot_matches_reference(box: Toolbox, pending: str | None) -> bool:
    """Observe the slot through the only operation that depends on its state."""
    if pending is None:
        await box.offer(_request('x'))
        return True
    with pytest.raises(AssertionError, match='still owed'):
        await box.offer(_request('x'))
    return True


async def _slot_machine_matches_reference(word: list[tuple[str, str]]) -> bool:
    """Run a generated word and compare the observed slot to its model."""
    box, pending = await _drive_slot_machine(word)
    return await _slot_matches_reference(box, pending)


_words = st.lists(
    st.tuples(
        st.sampled_from(('offer', 'select', 'recall', 'cancel')),
        st.text(min_size=1, max_size=4),
    ),
    max_size=8,
)


@given(_words)
async def test_the_slot_agrees_with_a_reference_model(word: list[tuple[str, str]]) -> None:
    """The public methods are a two-state machine: Idle ⇄ Pending.

    offer stores the request (and refuses while one is owed); select answers
    it and goes idle; recall and cancel drop it in either state. The reference
    model is one string — the owed request, or nothing.
    """
    assert await _slot_machine_matches_reference(word)


async def test_a_failed_select_still_frees_the_slot() -> None:
    """A selection failure consumes the request: the box owes nothing after."""

    async def search(query: str) -> Choice:
        return reply('maybe', [])

    box = _answering_box(search)
    await box.offer(_request('mpst'))
    with pytest.raises(SelectionError, match='not on offer'):
        await box.select(Planner, _replies())
    # the request was consumed even though answering failed:
    await box.offer(_request('mpst'))
    with pytest.raises(AssertionError, match='still owed'):
        await box.offer(_request('mpst'))


async def test_a_wrong_payload_still_frees_the_slot() -> None:
    """A payload failure consumes the request: the box owes nothing after."""

    async def search(query: str) -> Choice:
        return reply('hits', 123)  # list[str] expected

    box = _answering_box(search)
    await box.offer(_request('mpst'))
    with pytest.raises(PayloadError, match='expected list payload, got 123'):
        await box.select(Planner, _replies())
    await box.offer(_request('mpst'))


async def test_unknown_reply_label_raises_selection_error() -> None:
    async def search(query: str) -> Choice:
        return reply('maybe', [])

    with pytest.raises(SelectionError, match='not on offer'):
        await _run_with(_answering_box(search))


async def test_wrong_raw_payload_raises_payload_error() -> None:
    async def search(query: str) -> Choice:
        return reply('hits', 123)  # list[str] expected

    with pytest.raises(PayloadError, match='expected list payload, got 123'):
        await _run_with(_answering_box(search))


async def test_a_declared_failure_is_an_ordinary_branch() -> None:
    async def search(query: str) -> Choice:
        return reply('offline', 'index unreachable')

    trace = await _run_with(_answering_box(search))
    assert tuple(str(envelope.label) for envelope in trace) == _OFFLINE_TRACE_LABELS


@pytest.mark.parametrize(
    'branch',
    [case('hits', list_of(Text)), Label('hits'), 'hits'],
    ids=('case', 'label', 'text'),
)
def test_reply_names_a_branch_by_case_label_or_text(
    branch: str | Label | Any,
) -> None:
    """A reply names the branch the same way the protocol declares it."""
    assert reply(branch, ['x']).label == Label('hits')


async def test_at_binds_under_a_ready_endpoint() -> None:
    """The cast entry point binds the same tools under a projected endpoint."""
    endpoint = project(PROTO, Tools)
    box = Toolbox.at(Tools, endpoint, _tools())
    await box.offer(_request('mpst'))
    chosen = await box.select(Planner, _replies())
    assert box.role == Tools
    assert box.endpoint_contract == endpoint
    assert chosen.payload == ['mpst-1', 'mpst-2']
