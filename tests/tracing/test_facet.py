"""Facets: the Boolean algebra of sides of a session, and its coverage."""

from __future__ import annotations

from functools import reduce
from itertools import combinations
from operator import or_
from typing import get_args, get_type_hints

from hypothesis import given
from hypothesis import strategies as st

from agentsparty.tracing.facet import (
    EVERYTHING,
    FAILURE,
    MODEL,
    NOTHING,
    SESSION,
    SIGNAL_NAMES,
    STEP,
    TOOL,
    Facet,
    SignalName,
    facet,
)
from tests.tracing.test_signals import all_signal_instances

ATOMS = (SESSION, STEP, MODEL, TOOL, FAILURE)


@st.composite
def facets(draw: st.DrawFn) -> Facet:
    return Facet(frozenset(draw(st.sets(st.sampled_from(sorted(SIGNAL_NAMES))))))


def test_every_signal_is_classified() -> None:
    """No signal falls outside the catalogue, and none falls outside an atom."""
    for signal, name in all_signal_instances():
        assert name in SIGNAL_NAMES
        assert signal in EVERYTHING
        assert signal not in NOTHING
        assert sum(signal in atom for atom in ATOMS) == 1


def test_atoms_partition_the_catalogue() -> None:
    """The atoms cover everything and never overlap."""
    assert reduce(or_, ATOMS) == EVERYTHING
    for left, right in combinations(ATOMS, 2):
        assert (left & right) == NOTHING


@given(facets(), facets(), facets())
def test_facets_are_a_boolean_algebra(a: Facet, b: Facet, c: Facet) -> None:
    assert (a | b) | c == a | (b | c)
    assert a | b == b | a
    assert a | (a & b) == a
    assert a & (b | c) == (a & b) | (a & c)
    assert a | ~a == EVERYTHING
    assert a & ~a == NOTHING
    assert ~(a | b) == ~a & ~b
    assert a <= a | b


@given(facets(), facets())
def test_membership_is_the_homomorphism(a: Facet, b: Facet) -> None:
    """Joining facets is disjoining memberships; complement is negation."""
    for signal, _ in all_signal_instances():
        assert (signal in a | b) == (signal in a or signal in b)
        assert (signal in a & b) == (signal in a and signal in b)
        assert (signal in ~a) == (signal not in a)


def test_signal_name_alias_matches_runtime_catalogue() -> None:
    assert set(get_args(SignalName)) == SIGNAL_NAMES


def test_facet_accepts_only_signal_name_literals() -> None:
    assert get_type_hints(facet)['names'] is SignalName
