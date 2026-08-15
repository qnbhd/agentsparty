"""Small domain primitives shared by the protocol and runtime layers."""

from __future__ import annotations

from agentsparty.kernel.budget import (
    DEFAULT_ALLOWANCE,
    DEFAULT_UNFOLDINGS,
    NOTHING_SPENT,
    ONE_STEP,
    ONE_UNFOLDING,
    UNBOUNDED,
    Allowance,
    Spent,
)
from agentsparty.kernel.console import Console, StreamConsole
from agentsparty.kernel.errors import (
    AllowanceExceeded,
    CompositionError,
    ConformanceError,
    DeadlineExceeded,
    JournalError,
    ModelError,
    ModelRefused,
    ModelUnavailable,
    PayloadError,
    ProjectionError,
    RecursionLimitError,
    SelectionError,
    StepLimitError,
    TokenLimitError,
    fault,
)
from agentsparty.kernel.nonempty import EmptyError, NonEmptyMap, NonEmptyTuple
from agentsparty.kernel.role import Role, role, roles

__all__ = [
    'DEFAULT_ALLOWANCE',
    'DEFAULT_UNFOLDINGS',
    'NOTHING_SPENT',
    'ONE_STEP',
    'ONE_UNFOLDING',
    'UNBOUNDED',
    'Allowance',
    'AllowanceExceeded',
    'CompositionError',
    'ConformanceError',
    'Console',
    'DeadlineExceeded',
    'EmptyError',
    'JournalError',
    'ModelError',
    'ModelRefused',
    'ModelUnavailable',
    'NonEmptyMap',
    'NonEmptyTuple',
    'PayloadError',
    'ProjectionError',
    'RecursionLimitError',
    'Role',
    'SelectionError',
    'Spent',
    'StepLimitError',
    'StreamConsole',
    'TokenLimitError',
    'fault',
    'role',
    'roles',
]
