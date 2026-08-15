"""Session protocol carrier: global and hybrid multiparty protocol AST."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

from typing_extensions import Unpack

from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Codec, Deadline, Fragment, Label

__all__ = [
    'GlobalType',
    'Interaction',
    'Parallel',
    'RecvFrom',
    'SendTo',
    'SessionBranchCase',
    'SessionEnd',
    'SessionFragment',
    'SessionRec',
    'SessionType',
    'SessionVar',
    'SingleSubject',
    'stop',
]


@dataclass(frozen=True, slots=True)
class SessionEnd:
    """Session protocol ending."""


@dataclass(frozen=True, slots=True)
class SessionBranchCase:
    """One labelled alternative within an interaction or interface."""

    label: Label
    payload: Codec[Any]
    continuation: SessionType
    intent: str = ''
    within: Deadline | None = None


@dataclass(frozen=True, slots=True)
class Interaction:
    """An internal message exchange from :attr:`sender` to :attr:`receiver`."""

    sender: Role
    receiver: Role
    branches: NonEmptyMap[Label, SessionBranchCase]


@dataclass(frozen=True, slots=True)
class SendTo:
    """External output ``p!q``.

    Internal :attr:`sender` picks a label for external :attr:`receiver`.
    """

    sender: Role
    receiver: Role
    branches: NonEmptyMap[Label, SessionBranchCase]


@dataclass(frozen=True, slots=True)
class RecvFrom:
    """External input ``p?q``.

    Internal :attr:`receiver` reacts to a label external :attr:`sender` picks.
    """

    sender: Role
    receiver: Role
    branches: NonEmptyMap[Label, SessionBranchCase]


@dataclass(frozen=True, slots=True)
class SessionVar:
    """A free or bound recursion variable."""

    name: str


@dataclass(frozen=True, slots=True)
class SessionRec:
    """A recursive session protocol ``μ name.body``."""

    name: str
    body: SessionType


@dataclass(frozen=True, slots=True)
class Parallel:
    """Independent composition ``H₁ | … | Hₙ``.

    Branches own pairwise-disjoint role sets and never exchange a message, so
    they have no common future: parallel composition has **no join**, and a
    parallel node has no continuation. Branches are closed, flattened, and
    ordered canonically, so ``par(a, b)`` and ``par(b, a)`` are one value.
    """

    branches: _ParallelBranches


SessionType: TypeAlias = (
    SessionEnd | Interaction | SendTo | RecvFrom | SessionRec | SessionVar | Parallel
)
# Non-empty parallel branches: at least two closed sessions.
_ParallelBranches: TypeAlias = tuple[SessionType, SessionType, Unpack[tuple[SessionType, ...]]]
GlobalType: TypeAlias = SessionEnd | Interaction | SessionRec | SessionVar | Parallel
SingleSubject: TypeAlias = SessionEnd | SessionVar | SessionRec | SendTo | RecvFrom
SessionFragment: TypeAlias = Fragment[SessionType]

stop: Fragment[SessionType] = Fragment.halt(SessionEnd())

_Prefix: TypeAlias = Interaction | SendTo | RecvFrom
