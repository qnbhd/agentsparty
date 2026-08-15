"""Reflexive perimeter: the only module where ``isinstance`` is allowed.

Untrusted text becomes a closed JSON ADT (``RawValue``); every ``as_*`` is
total relative to its signature — value or ``PayloadError``, never TypeError.
"""

from __future__ import annotations

import json
import math
from typing import TypeAlias, cast

from agentsparty.kernel.errors import PayloadError

_RawAtom: TypeAlias = str | int | float | bool | None
RawValue: TypeAlias = _RawAtom | list['RawValue'] | dict[str, 'RawValue']


def load_json(text: str) -> RawValue:
    """Parse JSON text into a ``RawValue``. Sole producer of structured raw data."""
    try:
        return cast(RawValue, json.loads(text))
    except json.JSONDecodeError as exc:
        raise PayloadError(f'expected JSON payload, got {text!r}') from exc


def as_json_text(raw: RawValue) -> str:
    """JSON text for model parsers. Strings pass through; other raw values dump."""
    if isinstance(raw, str):
        return raw
    return json.dumps(raw)


def as_object(raw: RawValue) -> dict[str, RawValue]:
    """Read *raw* as a JSON object.

    Args:
        raw: Raw value to interpret.

    Returns:
        The object as a mapping of string keys to raw values.

    Raises:
        PayloadError: if *raw* is not a JSON object.
    """
    value = _parse_container(raw)
    if not isinstance(value, dict):
        raise PayloadError(f'expected object payload, got {raw!r}')
    if not all(isinstance(key, str) for key in value):
        raise PayloadError(f'expected object payload, got {raw!r}')
    return value


def as_array(raw: RawValue) -> list[RawValue]:
    """Read *raw* as a JSON array.

    Args:
        raw: Raw value to interpret.

    Returns:
        The array as a list of raw values.

    Raises:
        PayloadError: if *raw* is not a JSON array.
    """
    value = _parse_container(raw)
    if not isinstance(value, list):
        raise PayloadError(f'expected list payload, got {raw!r}')
    return value


def as_text(raw: RawValue) -> str:
    """Read *raw* as a string.

    Args:
        raw: Raw value to interpret.

    Returns:
        The string value.

    Raises:
        PayloadError: if *raw* is not a string.
    """
    if isinstance(raw, str):
        return raw
    raise PayloadError(f'expected str payload, got {raw!r}')


def as_integer(raw: RawValue) -> int:
    """Read *raw* as an integer, accepting numeric strings.

    Args:
        raw: Raw value to interpret.

    Returns:
        The integer value.

    Raises:
        PayloadError: if *raw* is not an int or an int-like string.
    """
    if isinstance(raw, bool) or raw is None:
        raise PayloadError(f'expected int payload, got {raw!r}')
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError as exc:
            raise PayloadError(f'expected int payload, got {raw!r}') from exc
    raise PayloadError(f'expected int payload, got {raw!r}')


def as_number(raw: RawValue) -> float:
    """Read *raw* as a finite number, accepting numeric strings.

    Args:
        raw: Raw value to interpret.

    Returns:
        The number as a finite float.

    Raises:
        PayloadError: if *raw* is not numeric, is a non-finite value
            (NaN/±Inf), or is not a finite numeric string.
    """
    if isinstance(raw, bool) or raw is None:
        raise PayloadError(f'expected float payload, got {raw!r}')
    if isinstance(raw, int | float):
        return _finite_float(float(raw), raw)
    if isinstance(raw, str):
        try:
            parsed = float(raw.strip())
        except ValueError as exc:
            raise PayloadError(f'expected float payload, got {raw!r}') from exc
        return _finite_float(parsed, raw)
    raise PayloadError(f'expected float payload, got {raw!r}')


def _finite_float(value: float, raw: RawValue) -> float:
    """Accept only finite floats; reject NaN and ±Inf as payload errors."""
    if math.isfinite(value):
        return value
    raise PayloadError(f'expected float payload, got {raw!r}')


def as_flag(raw: RawValue) -> bool:
    """Read *raw* as a boolean, accepting truthy/falsy strings.

    Args:
        raw: Raw value to interpret.

    Returns:
        The boolean value.

    Raises:
        PayloadError: if *raw* is neither a bool nor a truthy/falsy string.
    """
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {'true', '1', 'yes'}:
            return True
        if normalized in {'false', '0', 'no'}:
            return False
    raise PayloadError(f'expected bool payload, got {raw!r}')


def as_null(raw: RawValue) -> None:
    """Read *raw* as JSON ``null``.

    Args:
        raw: Raw value to interpret.

    Raises:
        PayloadError: if *raw* is not null.
    """
    if raw is None or raw == 'null':
        return
    raise PayloadError(f'expected null payload, got {raw!r}')


def as_nothing(raw: RawValue) -> None:
    """Read *raw* as "no payload" (only ``null`` is accepted).

    Args:
        raw: Raw value to interpret.

    Raises:
        PayloadError: if *raw* is anything but null.
    """
    if raw is None:
        return
    raise PayloadError(f'expected no payload, got {raw!r}')


def _parse_container(raw: RawValue) -> RawValue:
    if isinstance(raw, str):
        return load_json(raw)
    return raw


__all__ = [
    'RawValue',
    'as_array',
    'as_flag',
    'as_integer',
    'as_json_text',
    'as_nothing',
    'as_null',
    'as_number',
    'as_object',
    'as_text',
    'load_json',
]
