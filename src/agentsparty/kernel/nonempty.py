"""Non-empty containers: ``NonEmptyTuple`` (static) and ``NonEmptyMap`` (composition).

Direction rule: a non-empty container appears where the library is the
producer — in ADT fields the user reads, and in parameters the runtime
passes to the user's implementation (protocol parameters are
contravariant, so implementations declaring a wider ``Mapping`` keep
satisfying a protocol declaring ``NonEmptyMap``). It never appears in a
parameter the user fills: user-facing construction stays on the widest
reasonable built-in.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import TypeAlias, TypeGuard, TypeVar

from typing_extensions import Self

__all__ = ['EmptyError', 'NonEmptyMap', 'NonEmptyTuple']

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class EmptyError(ValueError):
    """Raised when a non-empty container would be created or left empty."""


NonEmptyTuple: TypeAlias = 'tuple[T, *tuple[T, ...]]'


def ne_tuple(head: T, /, *tail: T) -> NonEmptyTuple[T]:
    """Build a ``NonEmptyTuple``. Calling it with no arguments is a static error."""
    return (head, *tail)


def is_nonempty_tuple(value: tuple[T, ...], /) -> TypeGuard[NonEmptyTuple[T]]:
    """Narrow ``tuple[T, ...]`` to ``NonEmptyTuple[T]``."""
    return len(value) > 0


class NonEmptyMap(Mapping[K, V]):
    """Immutable non-empty mapping by composition.

    Construction only via ``of_pairs`` / ``of_mapping`` / ``check_pairs``.
    Explicit ``__eq__`` / ``__hash__`` so structural protocol equality stays sound.
    """

    __slots__ = ('_data',)

    def __init__(self, data: dict[K, V], /) -> None:
        """Wrap a non-empty *data* mapping; rejects an empty one."""
        if not data:
            raise EmptyError('NonEmptyMap cannot be empty')
        self._data = data

    @classmethod
    def of_pairs(cls, pairs: Iterable[tuple[K, V]], /) -> Self:
        """Build from an iterable of pairs; rejects empty or duplicate keys."""
        buffer: dict[K, V] = {}
        for key, value in pairs:
            if key in buffer:
                raise ValueError(f'duplicate key {key!r}')
            buffer[key] = value
        if not buffer:
            raise EmptyError('cannot build a NonEmptyMap from an empty iterable')
        return cls(buffer)

    @classmethod
    def of_mapping(cls, mapping: Mapping[K, V], /) -> Self:
        """Build from a mapping; rejects an empty one."""
        if not mapping:
            raise EmptyError('cannot build a NonEmptyMap from an empty mapping')
        return cls(dict(mapping))

    @classmethod
    def check_pairs(cls, pairs: Iterable[tuple[K, V]], /) -> Self | None:
        """Build from pairs, or return ``None`` when *pairs* is empty."""
        buffer: dict[K, V] = {}
        for key, value in pairs:
            if key in buffer:
                raise ValueError(f'duplicate key {key!r}')
            buffer[key] = value
        if buffer:
            return cls(buffer)
        return None

    def __getitem__(self, key: K) -> V:
        """Return the value stored under *key*."""
        return self._data[key]

    def __iter__(self) -> Iterator[K]:
        """Iterate over the stored keys."""
        return iter(self._data)

    def __len__(self) -> int:
        """Return the number of stored entries."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return a reproducible representation."""
        item_parts = [f'{key!r}: {val!r}' for key, val in self._data.items()]
        body = ', '.join(item_parts)
        return f'NonEmptyMap({{{body}}})'

    def __eq__(self, other: object) -> bool:
        """Structural equality with another ``NonEmptyMap``."""
        match other:
            case NonEmptyMap():
                return dict(self) == dict(other)
            case _:
                return NotImplemented

    def __hash__(self) -> int:
        """Hash by entries so protocol structural equality stays sound."""
        return hash(frozenset(self._data.items()))
