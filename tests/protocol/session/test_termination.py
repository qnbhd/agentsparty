"""Static may/must termination over closed global protocols."""

from __future__ import annotations

from agentsparty.kernel.role import roles
from agentsparty.protocol import (
    Text,
    alt,
    case,
    may_terminate,
    msg,
    must_terminate,
    rec,
    var,
)

A, B, C = roles('A', 'B', 'C')


def test_linear_protocol_may_and_must_terminate() -> None:
    """A finishable linear choreography reaches end on every path."""
    proto = (msg[A, B]('Hi', Text) >> msg[B, A]('Ack', Text)).close()
    assert may_terminate(proto) is True
    assert must_terminate(proto) is True


def test_recursive_with_exit_may_but_need_not_terminate() -> None:
    """A loop with a done branch can finish; it is not forced to."""
    proto = rec(
        't',
        alt[A, B](case('loop') >> var('t'), case('done')),
    ).close()
    assert may_terminate(proto) is True
    assert must_terminate(proto) is False


def test_pure_recursive_loop_never_terminates() -> None:
    """A daemon protocol has no path to end."""
    proto = rec('t', msg[A, B]('Tick', Text) >> var('t')).close()
    assert may_terminate(proto) is False
    assert must_terminate(proto) is False


def test_alt_with_only_exits_must_terminate() -> None:
    """Every arm ends; no cycle — must terminate."""
    proto = alt[A, B](
        case('Ok', Text),
        case('No', Text) >> msg[B, A]('Ack', Text),
    ).close()
    assert may_terminate(proto) is True
    assert must_terminate(proto) is True


def test_three_role_review_may_but_need_not() -> None:
    """Recursive review with NeedsInput loop: may end via Sign/Abort."""
    Lead, Worker, Auditor = roles('Lead', 'Worker', 'Auditor')
    review = rec(
        'loop',
        alt[Lead, Worker](
            case('Task', Text)
            >> alt[Worker, Lead](
                case('Done', Text) >> msg[Lead, Auditor]('Sign', Text),
                case('NeedsInput', Text) >> msg[Lead, Auditor]('Waiting') >> var('loop'),
            ),
            case('Abort') >> msg[Lead, Auditor]('Cancelled'),
        ),
    ).close()
    assert may_terminate(review) is True
    assert must_terminate(review) is False
