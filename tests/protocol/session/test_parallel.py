"""Laws for parallel composition: monoid, projection, localisation, termination."""

from __future__ import annotations

import pytest
from hypothesis import given, settings

from agentsparty.journal.types import digest_of
from agentsparty.kernel.errors import ProjectionError
from agentsparty.kernel.role import roles
from agentsparty.protocol import (
    Text,
    localise,
    may_terminate,
    msg,
    must_terminate,
    par,
    project,
    project_onto,
    stop,
    var,
)
from agentsparty.protocol.session import equal_session
from agentsparty.protocol.session._syntax import _parallel
from tests.protocol.strategies import linear_protocols


def _independent_pair():
    """Two closed choreographies over disjoint role sets."""
    A, B, C, D = roles('Auditor', 'Scanner', 'Archivist', 'Notary')
    left = msg[A, B]('Scan', Text).close()
    right = msg[C, D]('File', Text).close()
    return left, right, A, B, C, D


def test_par_commutative_monoid() -> None:
    """Par(a,b)==par(b,a); associativity; unit end."""
    A, B, C, D = roles('Auditor', 'Scanner', 'Archivist', 'Notary')
    E, F = roles('Editor', 'Fact')
    left = msg[A, B]('Scan', Text)
    right = msg[C, D]('File', Text)
    third = msg[E, F]('Check', Text)
    assert equal_session(par(left, right).close(), par(right, left).close())
    nested = par(left, par(right, third)).close()
    flat = par(left, right, third).close()
    assert equal_session(nested, flat)
    assert equal_session(par(left, stop).close(), left.close())
    assert digest_of(par(left, right).close()) == digest_of(par(right, left).close())


def test_par_refuses_tail() -> None:
    A, B, C, D = roles('Auditor', 'Scanner', 'Archivist', 'Notary')
    with pytest.raises(ValueError, match='par has no join'):
        (par(msg[A, B]('Scan'), msg[C, D]('File')) >> msg[A, C]('Report')).close()


def test_par_refuses_open_branch() -> None:
    _A, _B, C, D = roles('A', 'B', 'C', 'D')
    open_branch = var('t')
    with pytest.raises(ValueError, match='must be closed'):
        par(open_branch, msg[C, D]('Go')).close()


def test_par_refuses_shared_role() -> None:
    A, B, C = roles('A', 'B', 'C')
    with pytest.raises(ValueError, match='both mention'):
        par(msg[A, B]('Hi'), msg[A, C]('Go')).close()


def test_proj_par() -> None:
    """Project onto a role in one branch sees only that branch."""
    left, right, A, _B, C, _D = _independent_pair()
    split = _parallel([left, right])
    assert equal_session(
        project_onto(split, frozenset({A})),
        project_onto(left, frozenset({A})),
    )
    assert equal_session(
        project_onto(split, frozenset({C})),
        project_onto(right, frozenset({C})),
    )
    # endpoint projection is the same as projecting the owning branch
    assert project(split, A) == project(left, A)
    with pytest.raises(ProjectionError, match='spans two parallel branches'):
        project_onto(split, frozenset({A, C}))


def test_loc_par() -> None:
    """Localise distributes over parallel branches."""
    left, right, *_ = _independent_pair()
    split = _parallel([left, right])
    assert equal_session(
        localise(split),
        _parallel([localise(left), localise(right)]),
    )


def test_termination_par() -> None:
    """May/must terminate are conjunctions over branches."""
    left, right, *_ = _independent_pair()
    split = _parallel([left, right])
    assert may_terminate(split) == (may_terminate(left) and may_terminate(right))
    assert must_terminate(split) == (must_terminate(left) and must_terminate(right))


def test_render_par_shape() -> None:
    from agentsparty.protocol import render

    A, B, C, D = roles('Auditor', 'Scanner', 'Archivist', 'Notary')
    text = render(par(msg[A, B]('Scan'), msg[C, D]('File')).close())
    assert text.startswith('par {')
    assert '\n  |\n' in text
    assert text.rstrip().endswith('}')


@given(proto=linear_protocols())
@settings(max_examples=20, deadline=None)
def test_digest_without_par_unchanged_shape(proto) -> None:
    """P12 guard: a protocol without par still digests as a non-empty string."""
    assert len(digest_of(proto).value) == 16
