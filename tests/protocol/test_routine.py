"""Property and example tests for ``Routine`` and ``do``."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from typing_extensions import Unpack, assert_never

from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role, roles
from agentsparty.protocol import (
    Label,
    Routine,
    Text,
    alt,
    case,
    do,
    msg,
    participants,
    project,
    rec,
    render,
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
from agentsparty.protocol.routine import _rename
from agentsparty.protocol.session import (
    Interaction,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
    assert_wellformed,
)
from tests.protocol.strategies import (
    POOL,
    branching_fragments,
    linear_fragments,
)


def _review_routine() -> Routine:
    Author, Critic = roles('Author', 'Critic')
    return Routine(
        'Review',
        (Author, Critic),
        msg[Author, Critic]('Draft', Text)
        >> alt[Critic, Author](case('Approve'), case('Reject', Text)),
    )


def _endpoint_rename(node: EndpointType, binding: Mapping[Role, Role]) -> EndpointType:
    """Reference rename over endpoint types (test oracle only)."""
    match node:
        case EndpointEnd() | EndpointVar():
            return node
        case EndpointRec(name=name, body=body):
            return EndpointRec(name, _endpoint_rename(body, binding))
        case EndpointSelect(receiver=receiver, branches=branches):
            return EndpointSelect(
                binding.get(receiver, receiver),
                _endpoint_branches_rename(branches, binding),
            )
        case EndpointBranch(sender=sender, branches=branches):
            return EndpointBranch(
                binding.get(sender, sender),
                _endpoint_branches_rename(branches, binding),
            )
        case _:  # pragma: no cover
            assert_never(node)


def _endpoint_branches_rename(
    branches: Mapping[Label, EndpointBranchCase],
    binding: Mapping[Role, Role],
) -> NonEmptyMap[Label, EndpointBranchCase]:
    return branches_map(
        EndpointBranchCase(
            branch.label,
            branch.payload,
            _endpoint_rename(branch.continuation, binding),
        )
        for branch in branches.values()
    )


@st.composite
def two_role_routines(draw: st.DrawFn) -> Routine:
    """A routine whose body mentions exactly two formal roles."""
    body = draw(linear_fragments(8))
    mentioned = participants(body.fill(SessionEnd()))
    assume(len(mentioned) == 2)
    params = tuple(mentioned)
    return Routine('R', cast(tuple[Role, Unpack[tuple[Role, ...]]], params), body)


@st.composite
def branching_two_role_routines(draw: st.DrawFn) -> Routine:
    """A branching routine on exactly two formal roles (projectable)."""
    body = draw(branching_fragments(6))
    closed = body.close()
    mentioned = participants(closed)
    assume(len(mentioned) == 2)
    params = tuple(mentioned)
    try:
        project(closed, params[0])
        project(closed, params[1])
    except Exception:
        assume(condition=False)
    return Routine('R', cast(tuple[Role, Unpack[tuple[Role, ...]]], params), body)


EXTRA = roles('P', 'Q', 'S', 'T', 'U', 'V')


@st.composite
def injective_actuals(draw: st.DrawFn, n: int) -> tuple[Role, ...]:
    """*n* distinct actual roles from an extended pool."""
    actuals = draw(
        st.lists(
            st.sampled_from(POOL + EXTRA),
            min_size=n,
            max_size=n,
            unique=True,
        ),
    )
    return tuple(actuals)


@given(routine=two_role_routines())
@settings(max_examples=40, deadline=None)
def test_identity_binding_is_identity(routine: Routine) -> None:
    left = render(do(routine, *routine.params).close())
    right = render(routine.body.close())
    assert left == right


@given(data=st.data())
@settings(max_examples=40, deadline=None)
def test_injective_binding_preserves_wellformedness(data: st.DataObject) -> None:
    routine = data.draw(two_role_routines())
    actuals = data.draw(injective_actuals(len(routine.params)))
    result = do(routine, *actuals).close()
    assert_wellformed(result)
    assert set(participants(result)) == set(actuals)


@given(proto=linear_fragments(8).map(lambda f: f.close()), data=st.data())
@settings(max_examples=40, deadline=None)
def test_rename_is_functorial(proto, data: st.DataObject) -> None:
    mentioned = participants(proto)
    assume(mentioned)
    pool = POOL + EXTRA
    sigma_targets = data.draw(
        st.lists(
            st.sampled_from(pool),
            min_size=len(mentioned),
            max_size=len(mentioned),
            unique=True,
        ),
    )
    sigma = dict(zip(mentioned, sigma_targets, strict=True))
    tau_targets = data.draw(
        st.lists(
            st.sampled_from(pool),
            min_size=len(sigma_targets),
            max_size=len(sigma_targets),
            unique=True,
        ),
    )
    tau = dict(zip(sigma_targets, tau_targets, strict=True))
    composed = {role: tau[sigma[role]] for role in mentioned}
    left = _rename(_rename(proto, sigma), tau)
    right = _rename(proto, composed)
    assert left == right


@given(data=st.data())
@settings(max_examples=30, deadline=None)
def test_projection_commutes_with_rename(data: st.DataObject) -> None:
    routine = data.draw(branching_two_role_routines())
    actuals = data.draw(injective_actuals(len(routine.params)))
    binding = dict(zip(routine.params, actuals, strict=True))
    called = do(routine, *actuals).close()
    body = routine.body.close()
    for formal, actual in binding.items():
        left = project(called, actual)
        right = _endpoint_rename(project(body, formal), binding)
        assert left == right


def test_do_rejects_same_role_twice() -> None:
    r = _review_routine()
    A, _ = roles('Alice', 'Bob')
    with pytest.raises(ValueError, match='same role twice'):
        do(r, A, A)


def test_do_rejects_arity_mismatch() -> None:
    r = _review_routine()
    A = roles('Alice')[0]
    with pytest.raises(ValueError, match='takes 2 roles'):
        do(r, A)


def test_routine_rejects_hidden_role() -> None:
    Author, Critic, Judge = roles('Author', 'Critic', 'Judge')
    with pytest.raises(ValueError, match='not parameters'):
        Routine(
            'Bad',
            (Author, Critic),
            msg[Author, Critic]('Draft') >> msg[Judge, Author]('Verdict'),
        )


def test_routine_rejects_unused_param() -> None:
    Author, Critic, Extra = roles('Author', 'Critic', 'Extra')
    with pytest.raises(ValueError, match='never uses'):
        Routine(
            'Bad',
            cast(tuple[Role, Unpack[tuple[Role, ...]]], (Author, Critic, Extra)),
            msg[Author, Critic]('Draft'),
        )


def test_routine_rejects_free_recursion() -> None:
    Author, Critic = roles('Author', 'Critic')
    with pytest.raises(ValueError, match='free recursion'):
        Routine(
            'Bad',
            (Author, Critic),
            msg[Author, Critic]('Draft') >> var('t'),
        )


def test_routine_rejects_repeated_param() -> None:
    Author, Critic = roles('Author', 'Critic')
    with pytest.raises(ValueError, match='repeats a role parameter'):
        Routine('Bad', (Author, Author), msg[Author, Critic]('X'))


def test_tail_is_not_renamed() -> None:
    Author, Critic = roles('Author', 'Critic')
    review = Routine(
        'Review',
        (Author, Critic),
        msg[Author, Critic]('Draft', Text),
    )
    Alice, Bob, Carol = roles('Alice', 'Bob', 'Carol')
    proto = (
        msg[Carol, Alice]('Brief') >> do(review, Alice, Bob) >> msg[Alice, Carol]('Done')
    ).close()
    text = render(proto)
    assert 'Carol -> Alice' in text
    assert 'Alice -> Bob' in text
    assert 'Alice -> Carol' in text


def test_stop_absorbs_post_call_continuation() -> None:
    A, B = roles('A', 'B')
    halting = Routine('Halt', (A, B), msg[A, B]('Bye') >> stop)
    Alice, Bob, Carol = roles('Alice', 'Bob', 'Carol')
    proto = (do(halting, Alice, Bob) >> msg[Alice, Carol]('Never')).close()
    text = render(proto)
    assert 'Never' not in text
    assert 'Alice -> Bob' in text


def test_rec_var_places_external_tail_on_non_recursive_exit() -> None:
    A, B = roles('A', 'B')
    looping = Routine(
        'Loop',
        (A, B),
        rec(
            't',
            alt[A, B](
                case('again') >> var('t'),
                case('done'),
            ),
        ),
    )
    Alice, Bob, Owner = roles('Alice', 'Bob', 'Owner')
    filled = (do(looping, Alice, Bob) >> msg[Alice, Owner]('Report')).close()
    text = render(filled)
    assert 'Report' in text
    assert 'Alice -> Owner' in text
    assert isinstance(filled, SessionRec)
    interaction = filled.body
    assert isinstance(interaction, Interaction)
    again = interaction.branches[Label('again')]
    done = interaction.branches[Label('done')]
    assert isinstance(again.continuation, SessionVar)
    assert again.continuation.name == 't'
    assert isinstance(done.continuation, Interaction)
    assert done.continuation.sender == Alice
    assert done.continuation.receiver == Owner


def test_two_calls_with_different_bindings_coexist() -> None:
    Author, Critic = roles('Author', 'Critic')
    review = Routine(
        'Review',
        (Author, Critic),
        msg[Author, Critic]('Draft', Text)
        >> alt[Critic, Author](case('Approve'), case('Reject', Text)),
    )
    Alice, Bob, Carol = roles('Alice', 'Bob', 'Carol')
    proto = (do(review, Alice, Bob) >> do(review, Bob, Carol)).close()
    text = render(proto)
    assert 'Alice -> Bob' in text
    assert 'Bob -> Alice' in text
    assert 'Bob -> Carol' in text
    assert 'Carol -> Bob' in text
    assert set(participants(proto)) == {Alice, Bob, Carol}


def _intents(node: SessionType) -> list[tuple[str, str]]:
    """(label, intent) pairs in pre-order over a global protocol."""
    match node:
        case SessionEnd() | SessionVar():
            return []
        case SessionRec(body=body):
            return _intents(body)
        case Interaction(branches=branches):
            pairs: list[tuple[str, str]] = []
            for branch in branches.values():
                pairs.append((str(branch.label), branch.intent))
                pairs.extend(_intents(branch.continuation))
            return pairs
        case _:
            return []


def test_do_preserves_intent() -> None:
    Author, Critic = roles('Author', 'Critic')
    review = Routine(
        'Review',
        (Author, Critic),
        msg[Author, Critic]('Draft', Text, 'a section draft')
        >> alt[Critic, Author](
            case('Approve', intent='accept the draft'),
            case('Reject', Text, 'one critique'),
        ),
    )
    Alice, Bob = roles('Alice', 'Bob')
    called = do(review, Alice, Bob).close()
    body = review.body.close()
    assert _intents(called) == _intents(body)


@given(data=st.data())
@settings(max_examples=20, deadline=None)
def test_duties_are_stable_under_renaming(data: st.DataObject) -> None:
    from agentsparty.protocol import duties

    routine = data.draw(branching_two_role_routines())
    actuals = data.draw(injective_actuals(len(routine.params)))
    formal_duties = duties(project(routine.body.close(), routine.params[0]))
    actual_duties = duties(project(do(routine, *actuals).close(), actuals[0]))
    # Same labels, payloads, intents; only the receiver role may rename.
    assert [(d.label, d.payload, d.intent) for d in formal_duties] == [
        (d.label, d.payload, d.intent) for d in actual_duties
    ]
