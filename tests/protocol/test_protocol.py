"""Tests for the ``common.py`` algebra: the codec-based DSL and its laws.

Two parts: codec-based DSL smoke tests (``msg``, ``alt``, ``seq``,
``repeat``, projection, rendering) followed by the property-based algebraic
laws (monoid, projection, merge, rendering).

Two structural facts shape every test here:

* ``Fragment`` is a frozen dataclass whose ``_fill`` is a closure, so two
  structurally identical fragments never compare equal.  All monoid laws are
  therefore stated extensionally, through ``.close()``.
* ``Codec`` carries a closure too, so only module singletons compare equal;
  generated protocols use singletons only (see ``strategies.py``).
"""

from __future__ import annotations

import operator
from functools import reduce
from itertools import starmap

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.journal.types import digest_of
from agentsparty.kernel.errors import ProjectionError
from agentsparty.kernel.role import Role, roles
from agentsparty.protocol import (
    Duty,
    Fragment,
    Integer,
    Label,
    Nothing,
    SessionEnd,
    SessionRec,
    SessionVar,
    Text,
    alt,
    case,
    duties,
    msg,
    participants,
    project,
    project_all,
    rec,
    render,
    repeat,
    seq,
    stop,
    var,
)
from agentsparty.protocol.language.core import branches_map
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointBranchCase,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    EndpointVar,
)
from agentsparty.protocol.session import Interaction, SessionBranchCase, SessionType
from tests.protocol import strategies


def test_msg_projection() -> None:
    Buyer, Seller = roles('Buyer', 'Seller')
    proto = msg[Buyer, Seller]('Order', Text).close()
    expected = branches_map([EndpointBranchCase(Label('Order'), Text, EndpointEnd())])
    assert project(proto, Buyer) == EndpointSelect(Seller, expected)
    assert project(proto, Seller) == EndpointBranch(Buyer, expected)


def test_render_golden() -> None:
    """Golden presentation spec: arrow, payload signature, multi-branch layout."""
    A, B = roles('A', 'B')
    assert render(msg[A, B]('Order', Text).close()) == 'A -> B : Order(str)\nend'
    proto = alt[A, B](case('Ok'), case('No', Integer)).close()
    assert render(proto) == ('A -> B {\n  No(int):\n    end\n  Ok():\n    end\n}')


def test_stop_in_branch() -> None:
    A, B = roles('A', 'B')
    proto = alt[A, B](
        case('Early') >> stop,
        case('Go') >> msg[B, A]('Back'),
    ).close()
    expected = Interaction(
        A,
        B,
        branches_map(
            [
                SessionBranchCase(Label('Early'), Nothing, SessionEnd()),
                SessionBranchCase(Label('Go'), Nothing, msg[B, A]('Back').close()),
            ],
        ),
    )
    assert proto == expected


def test_repeat_negative_raises() -> None:
    A, B = roles('A', 'B')
    with pytest.raises(ValueError, match='non-negative'):
        repeat(-1, msg[A, B]('tick'))


def test_observer_outside_alt_identical_arms_merge() -> None:
    A, B, C, D = roles('A', 'B', 'C', 'D')
    body = msg[C, D]('work')
    proto = alt[A, B](case('Go') >> body, case('Skip') >> body).close()
    # Both arms agree, so the observer's view collapses to the shared body.
    assert project(proto, C) == project(body.close(), C)


def test_observer_outside_alt_different_arms_raises() -> None:
    A, B, C, D = roles('A', 'B', 'C', 'D')
    proto = alt[A, B](case('Go') >> msg[C, D]('work'), case('Skip')).close()
    with pytest.raises(ProjectionError):
        project(proto, C)


def test_merge_payload_conflict_raises() -> None:
    """Observer of a alt whose arms carry the same label with different payloads."""
    A, B, C = roles('A', 'B', 'C')
    proto = alt[A, B](
        case('Go') >> msg[B, C]('k', Text),
        case('Skip') >> msg[B, C]('k', Integer),
    ).close()
    with pytest.raises(ProjectionError, match='two payloads'):
        project(proto, C)


def test_a_merge_of_two_intents_is_refused() -> None:
    A, B, C = roles('A', 'B', 'C')
    proto = alt[A, B](
        case('Go') >> msg[B, C]('k', Text, 'one'),
        case('Skip') >> msg[B, C]('k', Text, 'two'),
    ).close()
    with pytest.raises(ProjectionError, match='two intents'):
        project(proto, C)


def test_projection_preserves_intent() -> None:
    A, B = roles('A', 'B')
    intent = 'a short diagram'
    proto = msg[A, B]('Design', Text, intent).close()
    local = project(proto, A)
    assert isinstance(local, EndpointSelect)
    branch = local.branches[Label('Design')]
    assert branch.intent == intent


def test_render_shows_intent_on_one_line() -> None:
    A, B = roles('A', 'B')
    multi = 'first line\nsecond line'
    text = render(msg[A, B]('Hi', Text, multi).close())
    assert multi not in text  # raw newlines must not appear
    assert multi.replace('\n', '\\n') in text or repr(multi)[1:-1] in text
    assert text.count('\n') == render(msg[A, B]('Hi', Text).close()).count('\n')


def test_digest_changes_with_intent() -> None:
    A, B = roles('A', 'B')
    plain = msg[A, B]('Hi', Text).close()
    with_intent = msg[A, B]('Hi', Text, 'say hello').close()
    assert digest_of(plain) != digest_of(with_intent)


def test_a_protocol_without_intent_keeps_its_digest() -> None:
    """Regression: empty intents must not change the pre-intent fingerprint."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / 'examples' / 'online' / 'guide.py'
    spec = importlib.util.spec_from_file_location('guide_example', path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert digest_of(module.protocol).value == '4efbdb16b63b033d'


def _sent_labels(node: SessionType, subject: Role) -> set[Label]:
    """Labels of messages *subject* sends in *node* (reference oracle)."""
    match node:
        case SessionEnd() | SessionVar():
            return set()
        case SessionRec(body=body):
            return _sent_labels(body, subject)
        case Interaction(sender=sender, receiver=_, branches=brs):
            own = {b.label for b in brs.values()} if sender == subject else set()
            deeper = set()
            for branch in brs.values():
                deeper |= _sent_labels(branch.continuation, subject)
            return own | deeper
        case _:  # SendTo / RecvFrom: pure-global generators never produce them
            return set()


@given(p=strategies.branching_protocols())
def test_duties_are_the_select_branches(p: SessionType) -> None:
    from tests.journal.conftest import is_projectable

    if not is_projectable(p):
        return
    for subject in participants(p):
        local = project(p, subject)
        got = {duty.label for duty in duties(local)}
        assert got == _sent_labels(p, subject)


@given(p=strategies.branching_protocols())
def test_duties_have_no_repeats(p: SessionType) -> None:
    from tests.journal.conftest import is_projectable

    if not is_projectable(p):
        return
    for subject in participants(p):
        found = duties(project(p, subject))
        assert len(set(found)) == len(found)


def test_duties_of_a_pure_receiver_are_empty() -> None:
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    assert duties(project(proto, B)) == ()


def test_duties_carry_the_intent() -> None:
    A, B = roles('A', 'B')
    intent = 'a PlantUML diagram'
    proto = msg[A, B]('Design', Text, intent).close()
    found = duties(project(proto, A))
    assert found == (Duty(B, Label('Design'), 'str', intent),)


def _global_depth(node: SessionType) -> int:
    match node:
        case SessionEnd() | SessionVar():
            return 0
        case SessionRec(body=body):
            return 1 + _global_depth(body)
        case Interaction(branches=brs):
            return 1 + max(_global_depth(branch.continuation) for branch in brs.values())
        case _:
            return 0


def _endpoint_depth(node: EndpointType) -> int:
    match node:
        case EndpointEnd() | EndpointVar():
            return 0
        case EndpointRec(body=body):
            return 1 + _endpoint_depth(body)
        case EndpointBranch(branches=brs) | EndpointSelect(branches=brs):
            return 1 + max(_endpoint_depth(branch.continuation) for branch in brs.values())


@given(pair=strategies.protocol_with_outsider())
def test_missing_role_projects_to_endpoint_end(
    pair: tuple[SessionType, Role],
) -> None:
    """A role that never appears gets the empty endpoint protocol — and never raises."""
    p, outsider = pair
    assert project(p, outsider) == EndpointEnd()


@given(p=strategies.linear_protocols())
def test_projection_total_on_linear_protocols(p: SessionType) -> None:
    """On single-branch chains ``_merge`` is never called, so projection is total."""
    for subject in strategies.POOL:
        local = project(p, subject)
        assert _endpoint_depth(local) <= _global_depth(p)


@given(
    continuation=strategies.linear_fragments(),
    trio=st.lists(strategies.ROLE, min_size=3, max_size=3, unique=True),
)
def test_observer_passes_through_foreign_exchange(
    continuation: Fragment[SessionType],
    trio: list[Role],
) -> None:
    """Projection of an observer sees right through a foreign exchange."""
    x, y, subject = trio
    message = msg[x, y]('ping', Text)
    observed = (message >> continuation).close()
    assert project(observed, subject) == project(continuation.close(), subject)


@given(p=strategies.branching_root_protocols())
def test_active_role_preserves_labels_and_payloads(p: SessionType) -> None:
    """The active role keeps every label, the payload object and the partner."""
    assert isinstance(p, Interaction)  # branching_root_protocols always yields one
    sender = p.sender
    receiver = p.receiver
    branches = p.branches

    selection = project(p, sender)
    branch = project(p, receiver)
    assert isinstance(selection, EndpointSelect)
    assert isinstance(branch, EndpointBranch)
    assert selection.receiver == receiver
    assert branch.sender == sender

    assert set(selection.branches.keys()) == set(branches.keys())
    assert set(branch.branches.keys()) == set(branches.keys())
    for label in branches:
        assert selection.branches[label].payload is branches[label].payload
        assert branch.branches[label].payload is branches[label].payload
        assert selection.branches[label].label == label
        assert branch.branches[label].label == label


@given(p=strategies.linear_protocols())
def test_project_all_covers_each_participant_once(p: SessionType) -> None:
    """``project_all`` returns one projection per participant, in participant order.

    Stated as a contract rather than as the implementation's own comprehension:
    the subjects align with ``participants`` and every entry is that role's
    projection.
    """
    entries = project_all(p)
    assert [subject for subject, _local in entries] == participants(p)
    for subject, local in entries:
        assert local == project(p, subject)


def _expected_participants(node: SessionType) -> list[Role]:
    occurrences: list[Role] = []

    def visit(current: SessionType) -> None:
        match current:
            case SessionEnd() | SessionVar():
                return
            case SessionRec(body=body):
                visit(body)
            case Interaction(sender=sender, receiver=receiver, branches=branches):
                occurrences.extend((sender, receiver))
                for branch in branches.values():
                    visit(branch.continuation)
            case _:
                return

    visit(node)
    return list(dict.fromkeys(occurrences))


@given(p=strategies.branching_protocols())
def test_participants_are_roles_in_first_appearance_order(p: SessionType) -> None:
    assert participants(p) == _expected_participants(p)


def test_observer_merge_unions_external_inputs() -> None:
    """An outsider of a alt sees the union of external receives on shared peers."""
    A, B, C = roles('A', 'B', 'C')
    proto = alt[A, B](
        case('Left') >> msg[A, C]('alpha', Text),
        case('Right') >> msg[A, C]('beta', Integer),
    ).close()
    local = project(proto, C)
    assert isinstance(local, EndpointBranch)
    assert set(local.branches.keys()) == {Label('alpha'), Label('beta')}


def test_observer_cannot_merge_distinct_internal_alts() -> None:
    """Classic MPST merges only external alts; EndpointSelect arms must not fuse."""
    a, b, c, d = roles('A', 'B', 'C', 'D')
    proto = alt[a, b](
        case('left') >> msg[c, d]('m'),
        case('right') >> msg[c, d]('n'),
    ).close()
    with pytest.raises(ProjectionError):
        project(proto, c)


@given(p=strategies.branching_protocols(), indent=st.integers(0, 5))
def test_render_indent_shifts_every_line(p: SessionType, indent: int) -> None:
    base = render(p).splitlines()
    shifted = render(p, indent).splitlines()
    assert shifted == ['  ' * indent + line for line in base]


@st.composite
def _alt_in_two_orders(
    draw: st.DrawFn,
) -> tuple[SessionType, SessionType]:
    sender, receiver = draw(strategies.role_pair())
    count = draw(st.integers(1, 4))
    names, codecs = strategies._case_inputs(draw, count)
    cases = list(starmap(case, zip(names, codecs, strict=True)))
    permuted = draw(st.permutations(cases))
    return (
        alt[sender, receiver](*cases).close(),
        alt[sender, receiver](*permuted).close(),
    )


@given(pair=_alt_in_two_orders())
def test_render_invariant_to_branch_order(
    pair: tuple[SessionType, SessionType],
) -> None:
    first, second = pair
    assert render(first) == render(second)


def _leaf_count(node: SessionType) -> int:
    match node:
        case SessionEnd():
            return 1
        case SessionVar():
            return 0
        case SessionRec(body=body):
            return _leaf_count(body)
        case Interaction(branches=brs):
            return sum(_leaf_count(branch.continuation) for branch in brs.values())
        case _:
            return 0


def _labels(node: SessionType) -> list[Label]:
    match node:
        case SessionEnd() | SessionVar():
            return []
        case SessionRec(body=body):
            return _labels(body)
        case Interaction(branches=brs):
            result: list[Label] = []
            for branch in brs.values():
                result.append(branch.label)
                result.extend(_labels(branch.continuation))
            return result
        case _:
            return []


@given(p=strategies.branching_protocols())
def test_render_complete(p: SessionType) -> None:
    text = render(p)
    for subject in participants(p):
        assert subject.name in text
    for label in _labels(p):
        assert label.name in text
    assert text.count('end') == _leaf_count(p)


@given(p=strategies.linear_protocols())
def test_render_of_endpoint_contractcol(p: SessionType) -> None:
    match p:
        case SessionEnd():
            assert render(EndpointEnd()) == 'end'
        case Interaction(sender=sender, receiver=receiver):
            selection = project(p, sender)
            branch = project(p, receiver)
            assert isinstance(selection, EndpointSelect)
            assert isinstance(branch, EndpointBranch)
            assert render(selection).startswith(f'!{receiver.name}')
            assert render(branch).startswith(f'?{sender.name}')
        case SessionRec() | SessionVar():
            pass


def _ping_done_proto() -> SessionType:
    """μt. A → B : { ping().t , done().end }."""
    A, B = roles('A', 'B')
    return rec(
        't',
        alt[A, B](
            case('ping') >> var('t'),
            case('done'),
        ),
    ).close()


def test_project_rec_var_on_active_roles() -> None:
    """PROJ-VAR / PROJ-REC-1: pure A↔B loop projects to EndpointRec/EndpointSelect/Var."""
    A, B = roles('A', 'B')
    proto = _ping_done_proto()
    local_a = project(proto, A)
    assert isinstance(local_a, EndpointRec)
    assert local_a.name == 't'
    assert isinstance(local_a.body, EndpointSelect)
    assert local_a.body.receiver == B
    ping = local_a.body.branches[Label('ping')]
    done = local_a.body.branches[Label('done')]
    assert ping.continuation == EndpointVar('t')
    assert done.continuation == EndpointEnd()

    local_b = project(proto, B)
    assert isinstance(local_b, EndpointRec)
    assert local_b.name == 't'
    assert isinstance(local_b.body, EndpointBranch)
    assert local_b.body.sender == A
    assert local_b.body.branches[Label('ping')].continuation == EndpointVar('t')
    assert local_b.body.branches[Label('done')].continuation == EndpointEnd()


def test_project_rec_outsider_is_end() -> None:
    """PROJ-REC-2: outsider of a pure A↔B loop gets EndpointEnd."""
    C = roles('C')[0]
    assert project(_ping_done_proto(), C) == EndpointEnd()


@given(p=strategies.guarded_recursive_protocols())
def test_project_rec_outsider_property(p: SessionType) -> None:
    """PROJ-REC-2 over generated guarded recursive bodies without outsider roles."""
    for outsider in strategies.OUTSIDER_POOL:
        assert project(p, outsider) == EndpointEnd()


def test_project_rejects_unguarded_raw_adt() -> None:
    with pytest.raises(ValueError, match='unguarded'):
        project(SessionRec('t', SessionVar('t')), roles('A')[0])


def test_project_rejects_open_raw_adt() -> None:
    with pytest.raises(ValueError, match='free recursion variable'):
        project(SessionVar('t'), roles('A')[0])


def _recursive_loop(sender, receiver):
    return rec(
        't',
        alt[sender, receiver](
            case('loop') >> var('t'),
            case('done'),
        ),
    )


def test_merge_identical_recursive_locals_is_mrg_id() -> None:
    """Identical recursive continuations on sibling arms merge via MRG-ID."""
    A, B, C, D = roles('A', 'B', 'C', 'D')
    loop = _recursive_loop(C, D)
    proto = alt[A, B](case('left') >> loop, case('right') >> loop).close()
    local_c = project(proto, C)
    expected = project(loop.close(), C)
    assert local_c == expected


def test_merge_non_equal_rec_raises() -> None:
    """Non-equal Rec/continuation pairs raise ProjectionError."""
    A, B, C, D = roles('A', 'B', 'C', 'D')
    loop = _recursive_loop(C, D)
    proto = alt[A, B](
        case('left') >> loop,
        case('right') >> msg[C, D]('once'),
    ).close()
    with pytest.raises(ProjectionError):
        project(proto, C)


def test_render_recursive_micro_example_golden() -> None:
    """Locked ASCII format for the §11 micro-example."""
    assert render(_ping_done_proto()) == (
        'rec t\n  A -> B {\n    done():\n      end\n    ping():\n      t\n  }'
    )


def test_participants_ignore_var_and_descend_rec() -> None:
    A, B = roles('A', 'B')
    proto = _ping_done_proto()
    assert participants(proto) == [A, B]


@given(fragment=strategies.linear_fragments())
def test_stop_is_right_neutral_under_close(
    fragment: Fragment[SessionType],
) -> None:
    assert (fragment >> stop).close() == fragment.close()


@given(
    first=strategies.linear_fragments(),
    rest=st.lists(strategies.linear_fragments(), min_size=1, max_size=3),
)
def test_seq_is_left_fold(
    first: Fragment[SessionType],
    rest: list[Fragment[SessionType]],
) -> None:
    assert seq(first, *rest).close() == reduce(operator.rshift, rest, first).close()
