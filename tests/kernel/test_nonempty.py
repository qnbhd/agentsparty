"""NonEmptyMap composition and NonEmptyTuple helpers."""

from __future__ import annotations

from operator import itemgetter

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.nonempty import EmptyError, NonEmptyMap, is_nonempty_tuple, ne_tuple

_nonempty_dicts = st.dictionaries(
    st.text(min_size=1, max_size=4),
    st.integers(),
    min_size=1,
    max_size=5,
)

# Small key alphabet so duplicate keys appear often in pair-list draws.
_pair_lists = st.lists(
    st.tuples(st.sampled_from('abcde'), st.integers()),
    min_size=1,
    max_size=8,
)
_unique_pair_lists = st.lists(
    st.tuples(st.sampled_from('abcde'), st.integers()),
    min_size=1,
    max_size=5,
    unique_by=itemgetter(0),
)


@given(st.integers(), st.lists(st.integers()))
def test_ne_tuple_contract(head: int, tail: list[int]) -> None:
    result = ne_tuple(head, *tail)
    assert is_nonempty_tuple(result)
    assert result[0] == head
    assert result[1:] == tuple(tail)
    assert len(result) == 1 + len(tail)
    assert result == (head, *tail)


@given(st.lists(st.integers()))
def test_is_nonempty_tuple_agrees_with_reference_model(items: list[int]) -> None:
    value = tuple(items)
    assert is_nonempty_tuple(value) == bool(value)


def test_constructors_reject_empty() -> None:
    with pytest.raises(EmptyError):
        NonEmptyMap.of_pairs([])
    with pytest.raises(EmptyError):
        NonEmptyMap.of_mapping({})
    with pytest.raises(EmptyError):
        NonEmptyMap({})
    assert NonEmptyMap.check_pairs([]) is None


@given(_pair_lists)
def test_of_pairs_and_check_pairs_on_sequences(
    pairs: list[tuple[str, int]],
) -> None:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        with pytest.raises(ValueError, match='duplicate key'):
            NonEmptyMap.of_pairs(pairs)
        with pytest.raises(ValueError, match='duplicate key'):
            NonEmptyMap.check_pairs(pairs)
        return

    expected = dict(pairs)
    built = NonEmptyMap.of_pairs(pairs)
    checked = NonEmptyMap.check_pairs(pairs)
    assert dict(built) == expected
    assert checked == built
    assert len(built) == len(expected)
    assert set(built) == set(expected)


@given(_nonempty_dicts)
def test_of_mapping_roundtrip(d: dict[str, int]) -> None:
    m = NonEmptyMap.of_mapping(d)
    assert dict(m) == d
    assert m == NonEmptyMap.of_mapping(d)


@given(_nonempty_dicts)
def test_of_mapping_does_not_alias_source(d: dict[str, int]) -> None:
    source = dict(d)
    m = NonEmptyMap.of_mapping(source)
    source.clear()
    assert dict(m) == d


def test_missing_key_raises_key_error() -> None:
    m = NonEmptyMap.of_pairs([('a', 1)])
    with pytest.raises(KeyError):
        _ = m['missing']


@given(_nonempty_dicts)
def test_equality_is_equivalence_and_constructors_agree(
    d: dict[str, int],
) -> None:
    from_pairs = NonEmptyMap.of_pairs(d.items())
    from_mapping = NonEmptyMap.of_mapping(d)
    from_check = NonEmptyMap.check_pairs(d.items())
    # path agreement + transitivity on equal content
    assert from_pairs == from_mapping == from_check
    # symmetry
    assert from_mapping == from_pairs
    # reflexivity
    same = from_pairs
    assert from_pairs == same
    # hash congruence: a == b implies hash(a) == hash(b)
    assert hash(from_pairs) == hash(from_mapping) == hash(from_check)


@given(_unique_pair_lists)
def test_eq_and_hash_are_order_independent(
    pairs: list[tuple[str, int]],
) -> None:
    forward = NonEmptyMap.of_pairs(pairs)
    backward = NonEmptyMap.of_pairs(reversed(pairs))
    assert forward == backward
    assert hash(forward) == hash(backward)


def test_map_inequality_axes_and_dict_key() -> None:
    base = NonEmptyMap.of_pairs([('x', 1)])
    different_value = NonEmptyMap.of_pairs([('x', 2)])
    different_key = NonEmptyMap.of_pairs([('y', 1)])
    superset = NonEmptyMap.of_pairs([('x', 1), ('y', 1)])
    assert base != different_value
    assert base != different_key
    assert base != superset
    assert {base: 1}[NonEmptyMap.of_pairs([('x', 1)])] == 1


def test_map_eq_with_non_map() -> None:
    m = NonEmptyMap.of_pairs([('x', 1)])
    assert m != 'not a map'
    assert m != 42
    assert m != object()
    equality = NonEmptyMap.__eq__
    assert equality(m, 'not a map') is NotImplemented


def test_map_repr() -> None:
    m = NonEmptyMap.of_pairs([('a', 1), ('b', 2)])
    assert repr(m) == "NonEmptyMap({'a': 1, 'b': 2})"
