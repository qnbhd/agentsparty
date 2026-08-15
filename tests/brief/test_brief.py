"""Brief: fold over envelopes; bounded windows; pure remember."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from agentsparty.brief import Recent, Transcript, line
from agentsparty.kernel.role import roles
from agentsparty.participant import Envelope
from agentsparty.protocol import Label
from tests.protocol.strategies import role_pair

A, B = roles('A', 'B')


@st.composite
def envelopes(draw: st.DrawFn, max_size: int = 8) -> list[Envelope]:
    """A short sequence of envelopes between a fixed role pair."""
    sender, receiver = draw(role_pair())
    n = draw(st.integers(0, max_size))
    labels = draw(
        st.lists(
            st.sampled_from(['alpha', 'beta', 'gamma', 'delta']),
            min_size=n,
            max_size=n,
        ),
    )
    payloads = draw(
        st.lists(
            st.one_of(st.none(), st.text(max_size=4), st.integers(-5, 5)),
            min_size=n,
            max_size=n,
        ),
    )
    # alternate direction so both sides appear as sender sometimes:
    result = []
    for i, (name, payload) in enumerate(zip(labels, payloads, strict=True)):
        if i % 2 == 0:
            result.append(Envelope(sender, receiver, Label(name), payload))
        else:
            result.append(Envelope(receiver, sender, Label(name), payload))
    return result


def _fold(brief, es: list[Envelope]):
    for envelope in es:
        brief = brief.remember(envelope)
    return brief


@given(es=envelopes())
def test_transcript_remembers_every_turn(es: list[Envelope]) -> None:
    subject = es[0].sender if es else A
    brief = _fold(Transcript(subject), es)
    assert len(brief.messages()) == len(es)


@given(es=envelopes(), k=st.integers(1, 6))
def test_recent_window_is_bounded(es: list[Envelope], k: int) -> None:
    subject = es[0].sender if es else A
    brief = _fold(Recent(subject, k), es)
    assert len(brief.messages()) == min(k, len(es))


@given(es=envelopes(), k=st.integers(1, 6))
def test_recent_is_a_suffix_of_transcript(es: list[Envelope], k: int) -> None:
    subject = es[0].sender if es else A
    recent = _fold(Recent(subject, k), es).messages()
    full = _fold(Transcript(subject), es).messages()
    assert recent == full[-k:]


@given(es=envelopes())
def test_remember_never_mutates(es: list[Envelope]) -> None:
    subject = es[0].sender if es else A
    original = Transcript(subject)
    before = original.messages()
    _fold(original, es)
    assert original.messages() == before


def test_recent_rejects_zero_window() -> None:
    try:
        Recent(A, 0)
    except ValueError:
        return
    raise AssertionError('expected ValueError')


def test_line_marks_sent_as_assistant() -> None:
    sent = line(A, Envelope(A, B, Label('Hi'), 'x'))
    received = line(A, Envelope(B, A, Label('Hi'), 'x'))
    assert sent.role == 'assistant'
    assert received.role == 'user'
