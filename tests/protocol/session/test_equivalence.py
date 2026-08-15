"""Protocol structural equality laws — precondition for NonEmptyMap rewrite."""

from __future__ import annotations

from contextlib import suppress

from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.role import Role, roles
from agentsparty.protocol import (
    Integer,
    Text,
    alt,
    case,
    msg,
    project,
    rec,
    var,
)
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.protocol.session import SessionEnd, SessionType


def _small_protocols() -> list[SessionType]:
    A, B, C = roles('A', 'B', 'C')
    p1 = msg[A, B]('Hi').close()
    p2 = msg[A, B]('Hi', Integer).close()
    p3 = (
        alt[A, B](
            case('Ok'),
            case('No', Text) >> msg[B, A]('Ack'),
        )
    ).close()
    p4 = (msg[A, B]('X') >> msg[B, C]('Y') >> msg[C, A]('Z')).close()
    p5 = SessionEnd()
    p6 = rec(
        't',
        alt[A, B](case('ping') >> var('t'), case('done')),
    ).close()
    return [p1, p2, p3, p4, p5, p6]


_PROTOS = _small_protocols()
_ROLES = roles('A', 'B', 'C')
_ENDPOINTS: list[EndpointType] = []
for _p in _PROTOS:
    for _r in _ROLES:
        with suppress(Exception):
            _ENDPOINTS.append(project(_p, _r))


@given(st.sampled_from(_PROTOS))
def test_global_eq_reflexive(p: SessionType) -> None:
    same = p
    assert p == same


@given(st.sampled_from(_PROTOS), st.sampled_from(_PROTOS))
def test_global_eq_symmetric(a: SessionType, b: SessionType) -> None:
    assert (a == b) == (b == a)


@given(
    st.sampled_from(_PROTOS),
    st.sampled_from(_PROTOS),
    st.sampled_from(_PROTOS),
)
def test_global_eq_transitive(a: SessionType, b: SessionType, c: SessionType) -> None:
    if a == b and b == c:
        assert a == c


@given(st.sampled_from(_ENDPOINTS))
def test_endpoint_eq_reflexive(p: EndpointType) -> None:
    same = p
    assert p == same


def _project_or_none(proto: SessionType, subject: Role) -> EndpointType | None:
    try:
        return project(proto, subject)
    except Exception:
        return None


@given(st.sampled_from(_PROTOS), st.sampled_from(_PROTOS))
def test_equal_protocols_project_equal(a: SessionType, b: SessionType) -> None:
    """Projection is deterministic: equal globals give equal locals per role."""
    if a != b:
        return
    for subject in _ROLES:
        left = _project_or_none(a, subject)
        right = _project_or_none(b, subject)
        assert (left is None) == (right is None)
        if left is not None:
            assert left == right
