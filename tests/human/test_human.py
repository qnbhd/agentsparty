from __future__ import annotations

import io
import sys
from collections.abc import Sequence

import pytest

from agentsparty.human import (
    CliHumanIo,
    Human,
    ScriptedHumanIo,
    _chosen_of,
    _Menu,
    _payload_prompt,
    _render_envelope,
)
from agentsparty.kernel.console import StreamConsole
from agentsparty.kernel.errors import PayloadError, SelectionError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import roles
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol import (
    Integer,
    Label,
    Nothing,
    Text,
    msg,
)
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointBranchCase, EndpointEnd

Buyer, Seller = roles('Buyer', 'Seller')

ORDER = EndpointBranchCase(Label('Order'), Text, EndpointEnd())
QUIT = EndpointBranchCase(Label('Quit'), Nothing, EndpointEnd())
AMOUNT = EndpointBranchCase(Label('Amount'), Integer, EndpointEnd())


def _menu(*branches: EndpointBranchCase) -> _Menu:
    return _Menu.of(NonEmptyMap.of_pairs([(b.label, b) for b in branches]))


class FakeConsole:
    def __init__(self, answers: Sequence[str]) -> None:
        self.answers = list(answers)
        self.asked: list[str] = []
        self.shown: list[str] = []

    async def ask(self, prompt: str) -> str:
        self.asked.append(prompt)
        if not self.answers:
            raise EOFError(f'FakeConsole exhausted at {prompt!r}')
        return self.answers.pop(0)

    def show(self, text: str) -> None:
        self.shown.append(text)


def test_menu_orders_branches_by_label() -> None:
    menu = _menu(QUIT, ORDER, AMOUNT)
    assert [str(b.label) for b in menu.ordered] == ['Amount', 'Order', 'Quit']


def test_menu_render() -> None:
    assert _menu(ORDER, QUIT).render('Buyer', Seller) == (
        '[Buyer] select a message to send to Seller:\n'
        '  1. Order  (payload: str)\n'
        '  2. Quit  (payload: undefined)\n'
        'Enter label (or number), then payload if required.'
    )


def test_menu_shows_intent() -> None:
    with_intent = EndpointBranchCase(
        Label('Order'),
        Text,
        EndpointEnd(),
        'a short shopping list',
    )
    menu = _menu(with_intent, QUIT)
    rendered = menu.render('Buyer', Seller)
    assert 'a short shopping list' in rendered
    assert rendered.splitlines()[1] == '  1. Order  (payload: str)'
    assert rendered.splitlines()[2] == '       a short shopping list'


def test_menu_resolve_by_position() -> None:
    menu = _menu(ORDER, QUIT)
    assert menu.resolve('1') is ORDER
    assert menu.resolve('2') is QUIT


def test_menu_resolve_by_label() -> None:
    assert _menu(ORDER, QUIT).resolve('Quit') is QUIT


def test_menu_resolve_ignores_surrounding_whitespace() -> None:
    menu = _menu(ORDER, QUIT)
    assert menu.resolve('  Order \n') is ORDER
    assert menu.resolve(' 2 ') is QUIT


def test_menu_resolve_position_below_range() -> None:
    with pytest.raises(SelectionError, match=r'alt 0 out of range 1\.\.2'):
        _menu(ORDER, QUIT).resolve('0')


def test_menu_resolve_position_above_range() -> None:
    with pytest.raises(SelectionError, match=r'alt 99 out of range 1\.\.2'):
        _menu(ORDER, QUIT).resolve('99')


def test_menu_resolve_unknown_label() -> None:
    expected = 'chosen label Nope not on offer: Order, Quit'
    with pytest.raises(SelectionError, match=expected):
        _menu(ORDER, QUIT).resolve('Nope')


def test_payload_prompt_none_without_payload() -> None:
    assert _payload_prompt(QUIT) is None


def test_payload_prompt_names_the_type() -> None:
    assert _payload_prompt(AMOUNT) == '> payload (int): '


def test_chosen_of_undefined_branch() -> None:
    assert _chosen_of(QUIT, None) == Chosen(branch=QUIT, payload=None, raw=None)


def test_chosen_of_parses_payload() -> None:
    assert _chosen_of(AMOUNT, '42') == Chosen(branch=AMOUNT, payload=42, raw='42')


def test_chosen_of_keeps_payload_whitespace() -> None:
    assert _chosen_of(ORDER, ' wide load ').payload == ' wide load '


def test_chosen_of_rejects_bad_payload() -> None:
    with pytest.raises(PayloadError, match='expected int payload'):
        _chosen_of(AMOUNT, 'not-a-number')


def test_render_envelope_without_payload() -> None:
    envelope = Envelope(sender=Seller, receiver=Buyer, label=Label('Done'))
    assert _render_envelope('Buyer', envelope) == '[Buyer] received Done from Seller'


def test_render_envelope_single_line_payload() -> None:
    envelope = Envelope(Seller, Buyer, Label('Quote'), '42')
    assert _render_envelope('Buyer', envelope) == '[Buyer] received Quote from Seller\n  42'


def test_render_envelope_indents_every_line() -> None:
    envelope = Envelope(Seller, Buyer, Label('Quote'), 'one\ntwo')
    assert _render_envelope('Buyer', envelope) == (
        '[Buyer] received Quote from Seller\n  one\n  two'
    )


async def _choose(
    console: FakeConsole, *branches: EndpointBranchCase
) -> Chosen[EndpointBranchCase]:
    human_io = CliHumanIo(console=console)
    pairs = [(b.label, b) for b in branches]
    return await human_io.choose(Buyer, Seller, NonEmptyMap.of_pairs(pairs))


async def test_choose_returns_parsed_payload() -> None:
    console = FakeConsole(['Order', 'widget'])
    chosen = await _choose(console, ORDER, QUIT)
    assert chosen.branch is ORDER
    assert chosen.payload == 'widget'
    assert console.asked == ['> label: ', '> payload (str): ']


async def test_choose_skips_payload_prompt_for_undefined_branch() -> None:
    console = FakeConsole(['2'])
    chosen = await _choose(console, ORDER, QUIT)
    assert chosen.branch is QUIT
    assert chosen.payload is None
    assert console.asked == ['> label: ']


async def test_choose_retries_and_shows_the_menu_once() -> None:
    console = FakeConsole(['7', 'Nope', '1', 'oops', '1', '42'])
    chosen = await _choose(console, AMOUNT)
    assert chosen.branch is AMOUNT
    assert chosen.payload == 42

    menus = [text for text in console.shown if text.startswith('[Buyer] select')]
    assert len(menus) == 1
    assert [text for text in console.shown if text.startswith('error:')] == [
        'error: alt 7 out of range 1..1',
        'error: chosen label Nope not on offer: Amount',
        "error: expected int payload, got 'oops'",
    ]


async def test_choose_propagates_eof() -> None:
    with pytest.raises(EOFError):
        await _choose(FakeConsole([]), ORDER)


async def test_notify_writes_through_the_console() -> None:
    console = FakeConsole([])
    human_io = CliHumanIo(console=console)
    await human_io.notify(Buyer, Envelope(Seller, Buyer, Label('Quote'), '42'))
    assert console.shown == ['[Buyer] received Quote from Seller\n  42']


async def test_streamconsole_ask_writes_prompt_and_reads_a_line() -> None:
    writer = io.StringIO()
    console = StreamConsole(reader=io.StringIO('widget\nnext\n'), writer=writer)
    assert await console.ask('> label: ') == 'widget'
    assert writer.getvalue() == '> label: '


async def test_streamconsole_ask_keeps_payload_spacing() -> None:
    console = StreamConsole(reader=io.StringIO('  wide load  \n'), writer=io.StringIO())
    assert await console.ask('> ') == '  wide load  '


async def test_streamconsole_ask_raises_on_eof() -> None:
    console = StreamConsole(reader=io.StringIO(''), writer=io.StringIO())
    with pytest.raises(EOFError, match='console input closed'):
        await console.ask('> ')


def test_streamconsole_show_appends_one_newline() -> None:
    writer = io.StringIO()
    StreamConsole(writer=writer).show('hello')
    assert writer.getvalue() == 'hello\n'


def test_streamconsole_resolves_streams_lazily() -> None:
    console = StreamConsole()
    captured = io.StringIO()
    original = sys.stdout
    sys.stdout = captured
    try:
        console.show('late binding')
    finally:
        sys.stdout = original
    assert captured.getvalue() == 'late binding\n'


async def test_human_cancel_delegates_with_its_role() -> None:
    """L8-h: Human passes its own role through to the underlying HumanIo."""
    proto = msg[Buyer, Seller]('Order', Text).close()
    io = ScriptedHumanIo([])
    human = Human(Buyer, proto, io)
    notice = Cancelled('StepLimitError: no budget')
    await human.cancel(notice)
    assert io.cancellations == [notice]
