"""Tracer that records choreography operators into session fragments."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Concatenate, Generic, TypeVar

from typing_extensions import ParamSpec, assert_never

from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import Case, Fragment, Label, _as_label, repeat, seq
from agentsparty.protocol.session import (
    alt,
    msg,
    par,
    rec,
    var,
)
from agentsparty.protocol.session import (
    stop as session_stop,
)
from agentsparty.protocol.session.types import SessionEnd, SessionType

T = TypeVar('T')
P = ParamSpec('P')


def _identity() -> Fragment[SessionType]:
    """An empty fragment: it passes the sequential tail through unchanged."""
    return Fragment.identity(SessionEnd())


@dataclass(frozen=True, slots=True)
class Located(Generic[T]):
    """Opaque value located at a receiver.

    In v1 this exists for (1) guarding ordinary ``if`` via :meth:`__bool__`,
    (2) readability, and (3) a door for later local computation. There are
    **no** consumption operators in v1 — that is intentional, not unfinished.
    """

    _receiver: Role | None = None

    def __bool__(self) -> bool:
        """Reject ordinary ``if`` on a traced value.

        Raises:
            TypeError: always — use ``c.decide`` for protocol branching.
        """
        raise TypeError(
            'cannot branch on a located value with ordinary if/while; '
            'use c.decide(...) for protocol alt',
        )


@dataclass
class _Scope:
    """One open region of the trace: steps plus a termination flag."""

    steps: list[Fragment[SessionType]] = field(default_factory=list)
    terminated: bool = False
    source: str = ''

    def append(self, fragment: Fragment[SessionType], *, source: str = '') -> None:
        if self.terminated:
            where = f' ({self.source})' if self.source else ''
            raise RuntimeError(f'cannot write to a scope after again()/stop(){where}')
        self.steps.append(fragment)
        if source:
            self.source = source

    def to_fragment(self) -> Fragment[SessionType]:
        if not self.steps:
            return _identity()
        first, *rest = self.steps
        if not rest:
            return first
        return seq(first, *rest)


class Chor:
    """Recording surface used inside a :func:`choreography` body."""

    def __init__(self) -> None:
        """Start with one root recording scope."""
        self._stack: list[_Scope] = [_Scope()]
        self._loop_serial: int = 0

    def say(
        self,
        sender: Role,
        receiver: Role,
        message: str | Label | Case[Any],
    ) -> Located[Any]:
        """Record an internal message from *sender* to *receiver*.

        Args:
            sender: The role sending the message.
            receiver: The role receiving the message.
            message: A label or a declared :class:`~agentsparty.protocol.language.core.Case`.

        Returns:
            An opaque :class:`Located` at *receiver* (no consumption in v1).
        """
        self._append(msg[sender, receiver](message))
        return Located(_receiver=receiver)

    def decide(self, sender: Role, receiver: Role) -> Decide:
        """Open a alt: *sender* picks a case for *receiver*.

        Use as ``with c.decide(S, R) as verdict:`` then
        ``with verdict.case(M):`` for each branch.
        """
        return Decide(self, sender, receiver)

    def loop(self, name: str | None = None) -> Loop:
        """Open a recursion binder (``with c.loop() as draft:``).

        Args:
            name: Optional recursion-variable name. When omitted, a fresh
                ``_loop_N`` name is generated. Pass an explicit name only when
                a combinator twin must share the same binder for
                :func:`~agentsparty.protocol.session.equal_session`.
        """
        return Loop(self, name=name)

    def times(self, n: int) -> Iterator[None]:
        """Unroll the loop body *n* times (``for _ in c.times(n):``).

        The body runs once under the tracer; the AST is ``repeat(n, body)``.
        """
        with self._times_scope(n):
            yield

    def parallel(self) -> Parallel:
        """Open a parallel split: ``with c.parallel() as split:`` / ``branch()``."""
        return Parallel(self)

    def stop(self) -> None:
        """Record an absorbing end and forbid further writes in this scope."""
        self._append(session_stop)
        self._current().terminated = True
        self._current().source = self._frame()

    def include(self, fragment: Fragment[SessionType]) -> None:
        """Splice a combinator-built open fragment into the trace.

        *fragment* must still be open (a :class:`~agentsparty.protocol.language.core.Fragment`):
        its hole is the sequential continuation of the choreography. A closed
        :class:`~agentsparty.protocol.session.SessionType` has no hole — pass the
        combinator expression without ``.close()``.

        Args:
            fragment: An open session fragment from facade A.

        Raises:
            TypeError: if a closed session protocol is passed instead of a fragment.
        """
        match fragment:
            case Fragment() as frag:
                self._append(frag)
            case _:
                raise TypeError(
                    'include() expects an open Fragment from the combinator '
                    'DSL; do not pass a closed SessionType (omit .close() so '
                    'the hole can continue the choreography)',
                )

    def _current(self) -> _Scope:
        return self._stack[-1]

    def _append(self, fragment: Fragment[SessionType]) -> None:
        self._current().append(fragment)

    def _frame(self) -> str:
        frame = inspect.currentframe()
        if frame is None or frame.f_back is None or frame.f_back.f_back is None:
            return ''
        caller = frame.f_back.f_back
        filename = caller.f_code.co_filename
        line = caller.f_lineno
        return f'{filename}:{line}'

    @contextmanager
    def _times_scope(self, n: int) -> Iterator[None]:
        """Push a body scope for :meth:`times` and seal it on the way out."""
        scope = _Scope()
        self._stack.append(scope)
        try:
            yield
        finally:
            self._finish_times(scope, n)

    def _finish_times(self, scope: _Scope, n: int) -> None:
        self._stack.pop()
        if n != 0:
            self._append(repeat(n, scope.to_fragment()))

    def _result(self) -> SessionType:
        if len(self._stack) != 1:
            raise RuntimeError('choreography ended with an unclosed scope')
        root = self._stack[0]
        if not root.steps:
            return session_stop.close()
        return root.to_fragment().close()


class Decide:
    """Context manager for ``with c.decide(sender, receiver) as verdict``."""

    def __init__(self, chor: Chor, sender: Role, receiver: Role) -> None:
        """Prepare a alt recorder for two roles."""
        self._chor = chor
        self._sender = sender
        self._receiver = receiver
        self._cases: list[Case[SessionType]] = []
        self._verdict = Verdict(self)

    def __enter__(self) -> Verdict:
        """Expose the handle used to open alt cases."""
        return self._verdict

    def __exit__(self, *exc: object) -> None:
        """Append the recorded cases as one alt."""
        if not self._cases:
            raise ValueError('decide() requires at least one case')
        result = alt[self._sender, self._receiver](*self._cases)
        self._chor._append(result)

    def _add_case(
        self,
        message: Case[Any] | str | Label,
        body: Fragment[SessionType],
    ) -> None:
        match message:
            case Case() as declared:
                arm = Case(
                    declared.label,
                    declared.payload,
                    body,
                    declared.intent,
                    declared.within,
                )
            case Label() as label:
                arm = Case(label, body=body)
            case str() as text:
                arm = Case(_as_label(text), body=body)
            case _:
                assert_never(message)
        self._cases.append(arm)


class Verdict:
    """Handle returned by :class:`Decide`; opens labelled case bodies."""

    def __init__(self, decide: Decide) -> None:
        """Prepare a handle for one alt recorder."""
        self._decide = decide

    def case(self, message: Case[Any] | str | Label) -> CaseBody:
        """Open a body for the declared branch label."""
        return CaseBody(self._decide, message)


class CaseBody:
    """Context manager for one branch under a :class:`Verdict`."""

    def __init__(self, decide: Decide, message: Case[Any] | str | Label) -> None:
        """Prepare a recorder for one alt branch."""
        self._decide = decide
        self._message = message
        self._scope = _Scope()

    def __enter__(self) -> None:
        """Start recording the branch body."""
        self._decide._chor._stack.append(self._scope)

    def __exit__(self, *exc: object) -> None:
        """Attach the branch body to its alt."""
        self._decide._chor._stack.pop()
        body = self._scope.to_fragment()
        self._decide._add_case(self._message, body)


class Loop:
    """Context manager for ``with c.loop() as draft`` recursion."""

    def __init__(self, chor: Chor, name: str | None = None) -> None:
        """Prepare a recursion scope and its back-edge handle."""
        self._chor = chor
        if name is None:
            self._name = f'_loop_{chor._loop_serial}'
            chor._loop_serial += 1
        else:
            self._name = name
        self._scope = _Scope()
        self._handle = LoopHandle(chor, self._name)

    def __enter__(self) -> LoopHandle:
        """Start recording the recursion body."""
        self._chor._stack.append(self._scope)
        return self._handle

    def __exit__(self, *exc: object) -> None:
        """Attach the recorded body to its recursion binder."""
        self._chor._stack.pop()
        body = self._scope.to_fragment()
        self._chor._append(rec(self._name, body))


class LoopHandle:
    """Binder handle; :meth:`again` closes the iteration with a back-edge."""

    def __init__(self, chor: Chor, name: str) -> None:
        """Remember the recursion name used by the back-edge."""
        self._chor = chor
        self._name = name

    def again(self) -> None:
        """Close this loop iteration with a back-edge to the binder."""
        self._chor._append(var(self._name))
        self._chor._current().terminated = True
        self._chor._current().source = self._chor._frame()


class Parallel:
    """Context manager for ``with c.parallel() as split``."""

    def __init__(self, chor: Chor) -> None:
        """Prepare an empty collection of parallel branches."""
        self._chor = chor
        self._branches: list[Fragment[SessionType]] = []

    def __enter__(self) -> Parallel:
        """Expose the branch builder."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Append the recorded branches as one parallel node."""
        if len(self._branches) < 2:
            raise ValueError('parallel() requires at least two branches')
        self._chor._append(par(*self._branches))

    def branch(self) -> BranchBody:
        """Open one branch body."""
        return BranchBody(self)


class BranchBody:
    """Context manager for one arm of a :class:`Parallel` split."""

    def __init__(self, parallel: Parallel) -> None:
        """Prepare a recorder owned by a parallel split."""
        self._parallel = parallel
        self._scope = _Scope()

    def __enter__(self) -> None:
        """Start recording the branch body."""
        self._parallel._chor._stack.append(self._scope)

    def __exit__(self, *exc: object) -> None:
        """Attach the recorded body to its parallel split."""
        self._parallel._chor._stack.pop()
        body = self._scope.to_fragment()
        self._parallel._branches.append(body)


def _build_choreography(
    fn: Callable[Concatenate[Chor, P], None],
    *args: P.args,
    **kwargs: P.kwargs,
) -> SessionType:
    chor = Chor()
    fn(chor, *args, **kwargs)
    return chor._result()


def choreography(
    fn: Callable[Concatenate[Chor, P], None],
) -> Callable[P, SessionType]:
    """Turn a procedure that records on a :class:`Chor` into a session builder.

    The decorated function receives ``c: Chor`` as its first argument and may
    take further parameters. The return value is a **builder**
    ``(*args, **kwargs) -> SessionType`` so parameterised protocols stay
    expressible and double-building is deterministic.

    Args:
        fn: A function ``(c: Chor, ...) -> None`` that only records operators.

    Returns:
        A function that builds a closed :class:`~agentsparty.protocol.session.SessionType`.
    """
    return partial(_build_choreography, fn)


__all__ = [
    'BranchBody',
    'CaseBody',
    'Chor',
    'Decide',
    'Located',
    'Loop',
    'LoopHandle',
    'Parallel',
    'Verdict',
    'choreography',
]
