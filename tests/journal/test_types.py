"""Boundary cases for the journal domain types."""

from __future__ import annotations

import pytest

from agentsparty.journal import (
    EMPTY_SCRIPT,
    FIRST_STEP,
    NULL_JOURNAL,
    ROOT_TRACK,
    Decision,
    NoJournal,
    Script,
    StepIndex,
    digest_of,
)
from agentsparty.kernel.errors import JournalError
from agentsparty.kernel.role import roles
from agentsparty.protocol import Label, Nothing, msg
from agentsparty.protocol.language.core import branches_map
from agentsparty.protocol.session import SessionBranchCase, SessionEnd


def _decision(
    step: int,
    sender: str = 'A',
    receiver: str = 'B',
    label: str = 'Hi',
    *,
    raw: str | int | float | bool | None = None,
    codec: str = 'undefined',
) -> Decision:
    A, B = roles(sender, receiver)
    return Decision(StepIndex(ROOT_TRACK, step), A, B, Label(label), codec, raw)


def test_step_index_rejects_zero() -> None:
    with pytest.raises(ValueError, match='starts at one'):
        StepIndex(ROOT_TRACK, 0)


def test_step_index_next() -> None:
    assert FIRST_STEP.next() == StepIndex(ROOT_TRACK, 2)


def test_script_of_empty() -> None:
    assert Script.of(()) == EMPTY_SCRIPT


def test_script_of_gap() -> None:
    with pytest.raises(JournalError, match=r'1\.\.2'):
        Script.of((_decision(1), _decision(3)))


def test_script_of_reversed() -> None:
    with pytest.raises(JournalError, match='in order'):
        Script.of((_decision(2), _decision(1)))


def test_script_at_and_upto() -> None:
    first = _decision(1, raw='a')
    second = _decision(2, raw='b')
    script = Script.of((first, second))
    assert script.at(StepIndex(ROOT_TRACK, 1)) == first
    assert script.at(StepIndex(ROOT_TRACK, 2)) == second
    assert script.upto(StepIndex(ROOT_TRACK, 1)).decisions == (first,)
    assert script.upto(StepIndex(ROOT_TRACK, 2)).decisions == (first, second)


def test_script_of_groups_independent_tracks() -> None:
    """Free interleaving across tracks is regrouped; each track is 1..n."""
    left = ROOT_TRACK.branch(0)
    right = ROOT_TRACK.branch(1)
    A, B, C, D = roles('A', 'B', 'C', 'D')
    a = Decision(StepIndex(left, 1), A, B, Label('L1'), 'undefined', None)
    b = Decision(StepIndex(right, 1), C, D, Label('R1'), 'undefined', None)
    c = Decision(StepIndex(left, 2), A, B, Label('L2'), 'undefined', None)
    # interleaved: left, right, left
    script = Script.of((a, b, c))
    assert script.length_of(left) == 2
    assert script.length_of(right) == 1
    assert script.words[left] == (a, c)
    assert script.words[right] == (b,)
    # canonical order is track-major
    assert script.decisions == (a, c, b)


def test_script_upto_keeps_independent_tracks() -> None:
    left = ROOT_TRACK.branch(0)
    right = ROOT_TRACK.branch(1)
    A, B, C, D = roles('A', 'B', 'C', 'D')
    a = Decision(StepIndex(left, 1), A, B, Label('L1'), 'undefined', None)
    b = Decision(StepIndex(right, 1), C, D, Label('R1'), 'undefined', None)
    c = Decision(StepIndex(left, 2), A, B, Label('L2'), 'undefined', None)
    script = Script.of((a, b, c))
    # truncate left to position 1; right is independent and stays
    cut = script.upto(StepIndex(left, 1))
    assert cut.length_of(left) == 1
    assert cut.length_of(right) == 1
    assert cut.words[left] == (a,)
    assert cut.words[right] == (b,)


def test_decision_branch_in_wrong_roles() -> None:
    A, B, C = roles('A', 'B', 'C')
    decision = Decision(FIRST_STEP, A, B, Label('Hi'), 'undefined', None)
    branch = SessionBranchCase(Label('Hi'), Nothing, SessionEnd())
    with pytest.raises(JournalError, match='was recorded as'):
        decision.branch_in(A, C, branches_map([branch]))


def test_decision_branch_in_unknown_label() -> None:
    A, B = roles('A', 'B')
    decision = Decision(FIRST_STEP, A, B, Label('Hi'), 'undefined', None)
    branch = SessionBranchCase(Label('Bye'), Nothing, SessionEnd())
    with pytest.raises(JournalError, match='offers'):
        decision.branch_in(A, B, branches_map([branch]))


def test_decision_branch_in_ok() -> None:
    A, B = roles('A', 'B')
    decision = Decision(FIRST_STEP, A, B, Label('Hi'), 'undefined', None)
    branch = SessionBranchCase(Label('Hi'), Nothing, SessionEnd())
    assert decision.branch_in(A, B, branches_map([branch])) is branch


def test_decision_branch_in_wrong_codec() -> None:
    A, B = roles('A', 'B')
    decision = Decision(FIRST_STEP, A, B, Label('Hi'), 'int', None)
    branch = SessionBranchCase(Label('Hi'), Nothing, SessionEnd())
    with pytest.raises(JournalError, match='codec'):
        decision.branch_in(A, B, branches_map([branch]))


def test_a_journal_written_under_a_weaker_codec_is_refused() -> None:
    """A Decision under plain Text cannot replay into a refined branch."""
    from agentsparty.protocol import Text, refine

    A, B = roles('A', 'B')
    refined = refine(Text, 'under 200 words', lambda s: len(s.split()) < 200)
    decision = Decision(FIRST_STEP, A, B, Label('Hi'), 'str', 'hello')
    branch = SessionBranchCase(Label('Hi'), refined, SessionEnd())
    with pytest.raises(JournalError, match='codec'):
        decision.branch_in(A, B, branches_map([branch]))


def test_digest_of_is_deterministic() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi').close()
    assert digest_of(proto) == digest_of(proto)


def test_digest_of_differs_for_different_protocols() -> None:
    A, B = roles('A', 'B')
    assert digest_of(msg[A, B]('Hi').close()) != digest_of(msg[A, B]('Bye').close())


def test_no_journal_is_empty() -> None:
    journal: NoJournal = NoJournal()
    assert journal.script() is EMPTY_SCRIPT
    journal.append(_decision(1))
    assert journal.script() is EMPTY_SCRIPT
    assert NULL_JOURNAL.script() is EMPTY_SCRIPT
