"""Perimeter totality and raw coercions — characterizing properties.

Spec (module docstring): every ``as_*`` is total — value or ``PayloadError``,
never ``TypeError``.  Correctness is the partition of each function's domain
against a simpler reference model (stdlib ``json`` / ``int`` / ``float``), not
an open-ended list of CLI scenarios.
"""

from __future__ import annotations

import json
import math
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.errors import PayloadError
from agentsparty.protocol.language.raw import (
    RawValue,
    as_array,
    as_flag,
    as_integer,
    as_json_text,
    as_nothing,
    as_null,
    as_number,
    as_object,
    as_text,
    load_json,
)

_json_atoms = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**6), max_value=10**6),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(max_size=20),
)


@st.composite
def raw_values(draw: st.DrawFn) -> RawValue:
    # Mix atoms in explicitly: pure ``st.recursive`` almost never yields plain
    # leaves, so identity branches (e.g. ``as_integer`` on ``int``) go unhit.
    nested = st.recursive(
        _json_atoms,
        lambda children: st.one_of(
            st.lists(children, max_size=4),
            st.dictionaries(st.text(max_size=8), children, max_size=4),
        ),
        max_leaves=12,
    )
    return draw(st.one_of(_json_atoms, nested))


_FLAG_TRUTHY = ('true', '1', 'yes')
_FLAG_FALSY = ('false', '0', 'no')
_WS = st.text(alphabet=' \t\n\r', max_size=3)


def _is_plain_int(raw: object) -> bool:
    """True for ``int`` that is not ``bool`` (bool subclasses int)."""
    return type(raw) is int


def _is_plain_number(raw: object) -> bool:
    return type(raw) is int or type(raw) is float


@given(raw=raw_values())
def test_load_json_roundtrip(raw: RawValue) -> None:
    """load_json ∘ json.dumps = id on RawValue."""
    assert load_json(json.dumps(raw)) == raw


@given(text=st.text(max_size=40))
def test_load_json_invalid_raises_payload_error(text: str) -> None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        with pytest.raises(PayloadError, match='expected JSON'):
            load_json(text)
    else:
        assert load_json(text) == parsed or (isinstance(parsed, float) and math.isnan(parsed))


@given(raw=raw_values())
def test_as_json_text_partition(raw: RawValue) -> None:
    if isinstance(raw, str):
        assert as_json_text(raw) == raw
    else:
        assert as_json_text(raw) == json.dumps(raw)


@given(raw=raw_values())
def test_as_text_characterization(raw: RawValue) -> None:
    if isinstance(raw, str):
        assert as_text(raw) == raw
    else:
        with pytest.raises(PayloadError, match='expected str'):
            as_text(raw)


@given(raw=st.one_of(raw_values(), st.text(max_size=30)))
def test_as_integer_characterization(raw: RawValue) -> None:
    """Full domain partition: plain int id | int(s.strip()) | PayloadError (bool⊄int)."""
    if _is_plain_int(raw):
        assert as_integer(raw) == raw
        return
    if isinstance(raw, str):
        try:
            expected = int(raw.strip())
        except ValueError:
            with pytest.raises(PayloadError, match='expected int'):
                as_integer(raw)
        else:
            assert as_integer(raw) == expected
        return
    with pytest.raises(PayloadError, match='expected int'):
        as_integer(raw)


@given(raw=st.one_of(raw_values(), st.text(max_size=30)))
def test_as_number_characterization(raw: RawValue) -> None:
    expected = _number_reference(raw)
    if expected is None:
        with pytest.raises(PayloadError, match='expected float'):
            as_number(raw)
        return
    assert math.isclose(as_number(raw), expected)


def _number_reference(raw: RawValue) -> float | None:
    """Finite float expected from *raw*, or ``None`` when as_number must reject."""
    if _is_plain_number(raw):
        value = float(cast(int | float, raw))
        return value if math.isfinite(value) else None
    if not isinstance(raw, str):
        return None
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) else None


@given(
    token=st.sampled_from(_FLAG_TRUTHY + _FLAG_FALSY),
    left=_WS,
    right=_WS,
    case=st.sampled_from(('lower', 'upper', 'capitalize')),
)
def test_as_flag_accepts_tokens_with_ws_and_case(
    token: str,
    left: str,
    right: str,
    case: str,
) -> None:
    """Finite token table + case/ws — characterization alone rarely hits every token."""
    body = getattr(token, case)()
    text = f'{left}{body}{right}'
    expected = token in _FLAG_TRUTHY
    assert as_flag(text) is expected


@given(raw=raw_values())
def test_as_flag_characterization(raw: RawValue) -> None:
    if isinstance(raw, bool):
        assert as_flag(raw) is raw
        return
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in _FLAG_TRUTHY:
            assert as_flag(raw) is True
            return
        if normalized in _FLAG_FALSY:
            assert as_flag(raw) is False
            return
    with pytest.raises(PayloadError, match='expected bool'):
        as_flag(raw)


def test_as_null_accepts_null_string_as_nothing_rejects() -> None:
    """Finite contrast: ``"null"`` is in as_null's domain and outside as_nothing's.

    Free-text generators almost never draw the exact token ``"null"``, so this
    success/reject pair must be forced explicitly (plan property inventory).
    """
    assert as_null('null') is None
    with pytest.raises(PayloadError, match='expected no payload'):
        as_nothing('null')


@given(raw=raw_values())
def test_as_null_characterization(raw: RawValue) -> None:
    if raw is None or raw == 'null':
        assert as_null(raw) is None
    else:
        with pytest.raises(PayloadError, match='expected null'):
            as_null(raw)


@given(raw=raw_values())
def test_as_nothing_characterization(raw: RawValue) -> None:
    if raw is None:
        assert as_nothing(raw) is None
    else:
        with pytest.raises(PayloadError, match='expected no payload'):
            as_nothing(raw)


@given(obj=st.dictionaries(st.text(max_size=8), raw_values(), max_size=4))
def test_as_object_via_json_text(obj: dict[str, RawValue]) -> None:
    """String-container success path; free text in raw_values is rarely valid JSON objects."""
    assert as_object(json.dumps(obj)) == obj


@given(raw=raw_values())
def test_as_object_characterization(raw: RawValue) -> None:
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            with pytest.raises(PayloadError):
                as_object(raw)
            return
    else:
        value = raw

    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        assert as_object(raw) == value
    else:
        with pytest.raises(PayloadError, match='expected object'):
            as_object(raw)


@given(xs=st.lists(raw_values(), max_size=4))
def test_as_array_via_json_text(xs: list[RawValue]) -> None:
    assert as_array(json.dumps(xs)) == xs


@given(raw=raw_values())
def test_as_array_characterization(raw: RawValue) -> None:
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            with pytest.raises(PayloadError):
                as_array(raw)
            return
    else:
        value = raw

    if isinstance(value, list):
        assert as_array(raw) == value
    else:
        with pytest.raises(PayloadError, match='expected list'):
            as_array(raw)


def test_as_object_rejects_non_str_keys() -> None:
    """Defensive branch: JSON never yields non-str keys; hand-built values can."""
    with pytest.raises(PayloadError, match='expected object'):
        as_object(cast(Any, {1: 'x'}))
