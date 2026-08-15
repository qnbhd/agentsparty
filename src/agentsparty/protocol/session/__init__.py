"""Session types and DSL (``alt``, ``msg``, ``owning``, …).

Public facade: re-exports the session package surface. Implementation lives
in leaf modules; do not import this package from those leaves.
"""

from __future__ import annotations

from agentsparty.protocol.session._bridge import as_endpoint, as_session
from agentsparty.protocol.session._composition import assert_compatible, compose
from agentsparty.protocol.session._equivalence import equal_session
from agentsparty.protocol.session._participants import participants
from agentsparty.protocol.session._projection import localise, project, project_all, project_onto
from agentsparty.protocol.session._recursion import free_vars, unfold
from agentsparty.protocol.session._syntax import (
    Boundary,
    alt,
    msg,
    owning,
    par,
    rec,
    var,
)
from agentsparty.protocol.session._termination import may_terminate, must_terminate
from agentsparty.protocol.session._wellformed import (
    as_global,
    assert_wellformed,
    ensure_session,
    epart,
    ipart,
)
from agentsparty.protocol.session.types import (
    GlobalType,
    Interaction,
    Parallel,
    RecvFrom,
    SendTo,
    SessionBranchCase,
    SessionEnd,
    SessionFragment,
    SessionRec,
    SessionType,
    SessionVar,
    SingleSubject,
    stop,
)

__all__ = [
    'Boundary',
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
    'alt',
    'as_endpoint',
    'as_global',
    'as_session',
    'assert_compatible',
    'assert_wellformed',
    'compose',
    'ensure_session',
    'epart',
    'equal_session',
    'free_vars',
    'ipart',
    'localise',
    'may_terminate',
    'msg',
    'must_terminate',
    'owning',
    'par',
    'participants',
    'project',
    'project_all',
    'project_onto',
    'rec',
    'stop',
    'unfold',
    'var',
]
