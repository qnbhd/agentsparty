"""Roles: named endpoints that participants bind to in a protocol."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Role:
    """A named endpoint in a protocol choreography."""

    name: str


def role(name: str) -> Role:
    """Build a single :class:`Role`.

    Args:
        name: The role's name.
    """
    return Role(name)


def roles(*names: str) -> tuple[Role, ...]:
    """Build several :class:`Role` objects, one per *name*.

    Args:
        *names: Role names, in the order they appear in a protocol.
    """
    return tuple(Role(name) for name in names)


__all__ = ['Role', 'role', 'roles']
