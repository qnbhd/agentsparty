"""Shared protocol generators for the property-based tests.

Payloads are deliberately restricted to *singleton* codecs (``Nothing``,
``Text``, ``Integer``, ``Number``, ``Flag``).  ``Codec`` is a frozen dataclass
whose ``decode`` field is a closure: combinator-built codecs (``list_of``,
``dict_of``, ...) create a fresh closure on every call, so
``list_of(Text) == list_of(Text)`` is always False.  Session merge compares
payloads by codec *name*, and module singletons have stable names; composite
codecs also compare by name, but generators stick to singletons so
structure-level ``==`` on local branches stays well-behaved.
"""

from __future__ import annotations

from typing import Any

from hypothesis import assume
from hypothesis import strategies as st

from agentsparty.kernel.errors import ProjectionError
from agentsparty.kernel.role import Role, roles
from agentsparty.protocol import (
    Codec,
    Flag,
    Fragment,
    Integer,
    Nothing,
    Number,
    SessionType,
    Text,
    alt,
    case,
    project,
    rec,
    stop,
    var,
)
from agentsparty.protocol.language.endpoint import EndpointType

A, B, C, D = roles('A', 'B', 'C', 'D')
POOL: tuple[Role, ...] = (A, B, C, D)
LABEL_NAMES = ('alpha', 'beta', 'gamma', 'delta')

# Disjoint namespace: an "outsider" role can never appear in a protocol drawn
# from POOL, so the missing-role law holds by construction.
X, Y, Z = roles('X', 'Y', 'Z')
OUTSIDER_POOL: tuple[Role, ...] = (X, Y, Z)

SINGLETONS = (Nothing, Text, Integer, Number, Flag)
CODE = st.sampled_from(SINGLETONS)
ROLE = st.sampled_from(POOL)


def _case_inputs(
    draw: st.DrawFn,
    count: int,
) -> tuple[list[str], list[Codec[Any]]]:
    """Draw unique labels and singleton codecs for *count* cases."""
    names = draw(
        st.lists(
            st.sampled_from(LABEL_NAMES),
            min_size=count,
            max_size=count,
            unique=True,
        ),
    )
    codecs = draw(st.lists(CODE, min_size=count, max_size=count))
    return names, codecs


def assert_filled_branches(proto, cases, tail) -> None:
    """Check that filling preserves each branch and its continuation."""
    for alternative in cases:
        arm = proto.branches[alternative.label]
        assert arm.label == alternative.label
        assert arm.payload == alternative.payload
        if alternative.body is None:
            assert arm.continuation == tail
        else:
            assert arm.continuation == alternative.body.fill(tail)


@st.composite
def role_pair(draw: st.DrawFn) -> tuple[Role, Role]:
    """Two distinct roles drawn from the small pool."""
    sender = draw(ROLE)
    receiver = draw(ROLE)
    assume(sender != receiver)
    return sender, receiver


@st.composite
def _interaction(
    draw: st.DrawFn,
    children: st.SearchStrategy[Fragment[SessionType]],
    min_cases: int,
    max_cases: int,
) -> Fragment[SessionType]:
    """A ``alt`` node whose arms may continue into ``children``."""
    sender, receiver = draw(role_pair())
    count = draw(st.integers(min_cases, max_cases))
    names, codecs = _case_inputs(draw, count)
    continues = draw(st.lists(st.booleans(), min_size=count, max_size=count))
    alternatives = []
    for name, codec, cont in zip(names, codecs, continues, strict=True):
        alternative = case(name, codec)
        if cont:
            alternative >>= draw(children)
        alternatives.append(alternative)
    return alt[sender, receiver](*alternatives)


def linear_fragments(
    max_leaves: int = 12,
) -> st.SearchStrategy[Fragment[SessionType]]:
    """Single-branch chains; ``project`` never calls ``_merge`` on these."""
    return st.recursive(
        st.just(stop),
        lambda children: _interaction(children, 1, 1),
        max_leaves=max_leaves,
    )


def branching_fragments(
    max_leaves: int = 8,
) -> st.SearchStrategy[Fragment[SessionType]]:
    """Full trees with one to three arms per alt node."""
    return st.recursive(
        st.just(stop),
        lambda children: _interaction(children, 1, 3),
        max_leaves=max_leaves,
    )


def linear_protocols(
    max_leaves: int = 12,
) -> st.SearchStrategy[SessionType]:
    """Closed linear protocols (the ADT, not fragments)."""
    return linear_fragments(max_leaves).map(lambda fragment: fragment.close())


def branching_protocols(
    max_leaves: int = 8,
) -> st.SearchStrategy[SessionType]:
    """Closed branching protocols (the ADT, not fragments)."""
    return branching_fragments(max_leaves).map(lambda fragment: fragment.close())


@st.composite
def protocol_with_outsider(draw: st.DrawFn) -> tuple[SessionType, Role]:
    """A closed branching protocol plus a role absent from it.

    The outsider is drawn from ``OUTSIDER_POOL``, disjoint from ``POOL``, so
    ``outsider not in participants(p)`` is guaranteed by construction.
    """
    p = draw(branching_protocols())
    outsider = draw(st.sampled_from(OUTSIDER_POOL))
    return p, outsider


@st.composite
def branching_root_protocols(draw: st.DrawFn) -> SessionType:
    """A branching root whose arms are linear chains.

    Projection is total for both the sender and the receiver of the root, so
    the label/payload-preservation law can be checked without skipping.
    """
    sender, receiver = draw(role_pair())
    count = draw(st.integers(1, 3))
    names, codecs = _case_inputs(draw, count)
    alternatives = []
    for name, codec in zip(names, codecs, strict=True):
        alternative = case(name, codec)
        if draw(st.booleans()):
            alternative >>= draw(linear_fragments(6))
        alternatives.append(alternative)
    return alt[sender, receiver](*alternatives).close()


@st.composite
def guarded_recursive_fragments(
    draw: st.DrawFn,
) -> Fragment[SessionType]:
    """Guarded recursive shapes with bounded depth.

    Template::

        rec(n, alt[Sender, Receiver](..., case('loop') >> body >> var(n), case('done') >> stop))

    Payloads are module singletons (same codec-identity caveat as the module
    docstring). Unguarded or open terms never appear here.
    """
    sender, receiver = draw(role_pair())
    name = draw(st.sampled_from(('t', 'u', 'loop')))
    loop_codec = draw(CODE)
    done_codec = draw(CODE)
    body: Fragment[SessionType] = stop
    if draw(st.booleans()):
        body = draw(linear_fragments(4))
    return rec(
        name,
        alt[sender, receiver](
            case('loop', loop_codec) >> body >> var(name),
            case('done', done_codec) >> stop,
        ),
    )


def guarded_recursive_protocols() -> st.SearchStrategy[SessionType]:
    """Closed guarded recursive protocols (the ADT, not fragments)."""
    return guarded_recursive_fragments().map(lambda fragment: fragment.close())


@st.composite
def projected_endpoints(draw: st.DrawFn) -> tuple[SessionType, Role, EndpointType]:
    """A protocol, one of its participants, and that participant's projection."""
    proto = draw(
        st.one_of(
            linear_protocols(),
            branching_protocols(),
            guarded_recursive_protocols(),
        ),
    )
    subject = draw(ROLE)
    try:
        local = project(proto, subject)
    except ProjectionError:
        assume(condition=False)
    return proto, subject, local


@st.composite
def role_subsets(
    draw: st.DrawFn,
) -> tuple[SessionType, frozenset[Role], frozenset[Role]]:
    """A protocol and nested focus sets ``E₂ ⊆ E₁ ⊆ roles(proto)``."""
    from agentsparty.protocol.session import participants

    proto = draw(
        st.one_of(
            linear_protocols(),
            branching_protocols(),
            guarded_recursive_protocols(),
        ),
    )
    roles_in = participants(proto)
    assume(roles_in)
    # Non-empty subset of participants
    e1_list = draw(
        st.lists(
            st.sampled_from(roles_in),
            min_size=1,
            max_size=len(roles_in),
            unique=True,
        ),
    )
    e1 = frozenset(e1_list)
    e2_list = draw(
        st.lists(
            st.sampled_from(e1_list),
            min_size=0,
            max_size=len(e1_list),
            unique=True,
        ),
    )
    e2 = frozenset(e2_list)
    return proto, e1, e2
