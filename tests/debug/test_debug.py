"""Contracts for the human-readable debug report."""

from __future__ import annotations

import ast
import io
from collections.abc import Iterable
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty import debug
from agentsparty.kernel.console import StreamConsole
from agentsparty.kernel.role import roles
from agentsparty.participant import Envelope
from agentsparty.protocol import Label, Text, msg
from agentsparty.tracing import Event, SessionFinished, SessionStarted
from agentsparty.tracing.types import Span, SpanId


def _report() -> tuple[debug.Report, io.StringIO]:
    buffer = io.StringIO()
    return debug.Report(StreamConsole(writer=buffer)), buffer


def _envelopes(values: Iterable[tuple[str, object | None]]) -> list[Envelope]:
    sender, receiver = roles('Sender', 'Receiver')
    return [Envelope(sender, receiver, Label(label), payload) for label, payload in values]


@given(
    st.lists(
        st.tuples(st.sampled_from(['A', 'B', 'C']), st.one_of(st.none(), st.integers(-2, 2))),
        max_size=12,
    ),
)
def test_conversation_has_one_header_and_line_per_envelope(
    values: list[tuple[str, object | None]],
) -> None:
    report, buffer = _report()
    report.conversation(_envelopes(values))
    assert len(buffer.getvalue().splitlines()) == 1 + len(values)


@given(
    st.lists(
        st.tuples(st.sampled_from(['A', 'B', 'C']), st.none()),
        max_size=12,
    ),
)
def test_skeleton_is_the_conversation_step_projection(
    values: list[tuple[str, None]],
) -> None:
    report, buffer = _report()
    envelopes = _envelopes(values)
    report.conversation(envelopes)
    conversation = buffer.getvalue().splitlines()[1:]
    buffer.seek(0)
    buffer.truncate()
    report.skeleton(envelopes)
    skeleton = buffer.getvalue().splitlines()[1]
    expected = [line.split(' -> ')[0] for line in conversation]
    assert (skeleton.split('  ') if values else []) == expected


def test_empty_sequences_have_only_their_section_headers() -> None:
    report, buffer = _report()
    report.conversation(())
    report.skeleton(())
    assert buffer.getvalue() == '=== conversation ===\n=== skeleton ===\n\n'


def test_conversation_omits_the_none_payload_suffix() -> None:
    report, buffer = _report()
    report.conversation(_envelopes([('Done', None), ('Value', 'ok')]))
    assert buffer.getvalue().splitlines()[1:] == [
        'Sender:Done -> Receiver',
        "Sender:Value -> Receiver 'ok'",
    ]


def test_facts_preserves_first_names_and_preserves_the_event_count() -> None:
    sender, receiver = roles('Sender', 'Receiver')
    protocol = msg[sender, receiver]('Hi', Text).close()
    events = [
        Event(SessionFinished(1), Span(SpanId('root'), None), 1),
        Event(SessionStarted(protocol, (sender, receiver)), Span(SpanId('root'), None), 2),
        Event(SessionFinished(1), Span(SpanId('root'), None), 3),
    ]
    report, buffer = _report()
    report.facts(events)
    assert buffer.getvalue() == ('=== run facts ===\nsession.finished: 2\nsession.started: 1\n')


def test_each_non_protocol_section_line_is_single_line() -> None:
    report, buffer = _report()
    report.note('first', 'second', title='note')
    assert all('\n' not in line for line in buffer.getvalue().splitlines())


def test_protocol_duties_and_titles() -> None:
    sender, receiver = roles('Sender', 'Receiver')
    protocol = msg[sender, receiver]('Hi', Text).close()
    report, buffer = _report()
    report.protocol(protocol, title='shape')
    report.duties(protocol, title='work')
    assert buffer.getvalue().startswith('=== shape ===\n')
    assert '=== work ===\nSender: Hi -> Receiver\n' in buffer.getvalue()


def test_note_requires_a_title_and_writes_lines_as_is() -> None:
    report, buffer = _report()
    report.note('a', 'b', title='prose')
    assert buffer.getvalue() == '=== prose ===\na\nb\n'


def test_refusing_swallows_expected_exception_and_reports_it() -> None:
    report, buffer = _report()
    with report.refusing(ValueError, title='refusal'):
        raise ValueError('bad shape')
    assert buffer.getvalue() == '=== refusal ===\nValueError: bad shape\n'


def test_refusing_propagates_unexpected_exception() -> None:
    report, _buffer = _report()
    with (
        pytest.raises(TypeError, match='unexpected'),
        report.refusing(
            ValueError,
            title='refusal',
        ),
    ):
        raise TypeError('unexpected')


def test_refusing_fails_when_body_does_not_raise() -> None:
    report, _buffer = _report()
    with (
        pytest.raises(AssertionError, match='expected ValueError'),
        report.refusing(
            ValueError,
            title='refusal',
        ),
    ):
        pass


def test_reports_are_independent_when_sharing_a_console() -> None:
    report, buffer = _report()
    report.note('one', title='first')
    report.note('two', title='second')
    assert buffer.getvalue() == '=== first ===\none\n=== second ===\ntwo\n'


def _debug_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    imports = [
        [alias.name for alias in node.names]
        if isinstance(node, ast.Import)
        else [node.module or '']
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    return [name for names in imports for name in names if name.startswith('agentsparty.debug')]


def test_debug_is_not_imported_by_library_modules() -> None:
    source_root = Path(__file__).parents[2] / 'src' / 'agentsparty'
    leaks = [
        f'{path}:{name}'
        for path in source_root.rglob('*.py')
        if path.name != 'debug.py'
        for name in _debug_imports(path)
    ]
    assert leaks == []


def test_report_without_console_uses_current_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    # StreamConsole resolves stdout per call, so this checks the process default.
    debug.Report().note('visible', title='default')
    assert capsys.readouterr().out == '=== default ===\nvisible\n'
