"""Facade B: choreography operators, equality with combinators, guards."""

from __future__ import annotations

import pytest

from agentsparty.choreography import Chor, Located, choreography
from agentsparty.kernel.role import roles
from agentsparty.protocol import (
    Text,
    alt,
    case,
    equal_session,
    msg,
    par,
    rec,
    repeat,
    stop,
    var,
)
from agentsparty.protocol.session import Interaction, SessionType


def test_linear_say_equals_combinator() -> None:
    A, B = roles('A', 'B')
    Hi = case('Hi', Text)
    Ack = case('Ack', Text)

    @choreography
    def hello(c: Chor) -> None:
        c.say(A, B, Hi)
        c.say(B, A, Ack)

    proto_a = (msg[A, B](Hi) >> msg[B, A](Ack)).close()
    assert equal_session(hello(), proto_a)
    assert equal_session(hello(), hello())
    assert isinstance(hello(), (SessionType, Interaction))


def test_decide_equals_alt() -> None:
    A, B = roles('A', 'B')
    Yes = case('Yes', Text)
    No = case('No')

    @choreography
    def decide_proto(c: Chor) -> None:
        with c.decide(A, B) as verdict:
            with verdict.case(Yes):
                pass
            with verdict.case(No):
                c.stop()

    # stop absorbs; empty case body is identity
    proto_a = alt[A, B](
        case('Yes', Text),
        case('No') >> stop,
    ).close()
    assert equal_session(decide_proto(), proto_a)
    assert equal_session(decide_proto(), decide_proto())


def test_loop_again_equals_rec_var() -> None:
    A, B = roles('A', 'B')
    Tick = case('Tick', Text)
    Done = case('Done')

    @choreography
    def loop_proto(c: Chor) -> None:
        with c.loop() as draft:
            c.say(A, B, Tick)
            with c.decide(B, A) as verdict:
                with verdict.case(Done):
                    pass
                with verdict.case(case('More')):
                    draft.again()

    proto_a = rec(
        '_loop_0',
        msg[A, B](Tick)
        >> alt[B, A](
            case('Done'),
            case('More') >> var('_loop_0'),
        ),
    ).close()
    assert equal_session(loop_proto(), proto_a)
    assert equal_session(loop_proto(), loop_proto())


def test_times_equals_repeat() -> None:
    A, B = roles('A', 'B')
    Hi = case('Hi', Text)

    @choreography
    def twice(c: Chor) -> None:
        for _ in c.times(2):
            c.say(A, B, Hi)

    proto_a = repeat(2, msg[A, B](Hi)).close()
    assert equal_session(twice(), proto_a)


def test_parallel_equals_par() -> None:
    A, B, C, D = roles('A', 'B', 'C', 'D')
    X = case('X', Text)
    Y = case('Y', Text)

    @choreography
    def split(c: Chor) -> None:
        with c.parallel() as p:
            with p.branch():
                c.say(A, B, X)
            with p.branch():
                c.say(C, D, Y)

    proto_a = par(msg[A, B](X), msg[C, D](Y)).close()
    assert equal_session(split(), proto_a)


def test_include_combinator_fragment() -> None:
    A, B = roles('A', 'B')
    Hi = case('Hi', Text)
    fragment = msg[A, B](Hi)

    @choreography
    def with_include(c: Chor) -> None:
        c.include(fragment)

    assert equal_session(with_include(), fragment.close())


def test_include_closed_session_raises() -> None:
    A, B = roles('A', 'B')
    closed = msg[A, B]('Hi', Text).close()

    @choreography
    def bad(c: Chor) -> None:
        c.include(closed)  # ty: ignore[invalid-argument-type]

    with pytest.raises(TypeError, match=r'open Fragment'):
        bad()


def test_loop_optional_name_matches_combinator() -> None:
    A, B = roles('A', 'B')

    @choreography
    def named(c: Chor) -> None:
        with c.loop('tick') as draft:
            c.say(A, B, 'X')
            draft.again()

    from agentsparty.protocol import rec, var

    proto_a = rec('tick', msg[A, B]('X') >> var('tick')).close()
    assert equal_session(named(), proto_a)


def test_located_bool_raises() -> None:
    located: Located[str] = Located()
    with pytest.raises(TypeError, match=r'c\.decide'):
        bool(located)


def test_write_after_again_raises() -> None:
    A, B = roles('A', 'B')

    @choreography
    def bad(c: Chor) -> None:
        with c.loop() as draft:
            draft.again()
            c.say(A, B, 'X')

    with pytest.raises(RuntimeError, match=r'after again'):
        bad()


def test_write_after_stop_raises() -> None:
    A, B = roles('A', 'B')

    @choreography
    def bad(c: Chor) -> None:
        c.stop()
        c.say(A, B, 'X')

    with pytest.raises(RuntimeError, match=r'after again\(\)/stop'):
        bad()


def test_built_values_are_real_session_protocols() -> None:
    A, B = roles('A', 'B')

    @choreography
    def linear(c: Chor) -> None:
        c.say(A, B, 'Hi')

    node = linear()
    # Real constructors: Interaction, not a choreography-only wrapper.
    assert isinstance(node, Interaction)
