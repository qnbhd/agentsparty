"""Session DSL: var, rec, par, alt, msg and directional prefixes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from itertools import chain
from typing import Any

from agentsparty.kernel.nonempty import NonEmptyTuple
from agentsparty.kernel.role import Role
from agentsparty.protocol.language.core import (
    Case,
    Codec,
    Deadline,
    Fragment,
    Label,
    Text,
    _bodies,
    _continuation,
    branches_map,
    case,
)
from agentsparty.protocol.session._recursion import _is_guarded, free_vars
from agentsparty.protocol.session._wellformed import (
    _assert_disjoint_roles,
    _assert_interface,
    _resolve_boundary,
    ensure_session,
    epart,
    ipart,
)
from agentsparty.protocol.session.types import (
    Interaction,
    Parallel,
    RecvFrom,
    SendTo,
    SessionBranchCase,
    SessionEnd,
    SessionRec,
    SessionType,
    SessionVar,
)


def var(name: str) -> Fragment[SessionType]:
    """Recursion variable leaf ``t`` — absorbs the sequential tail, like ``stop``.

    Args:
        name: The recursion-variable name (must match an enclosing ``rec``).
    """
    return Fragment.halt(SessionVar(name))


def _build_par(
    first: Fragment[SessionType],
    second: Fragment[SessionType],
    rest: tuple[Fragment[SessionType], ...],
    tail: SessionType,
) -> SessionType:
    if tail != SessionEnd():
        raise ValueError(
            'par has no join: nothing can follow a parallel composition, '
            'because its branches own disjoint roles and share no future. '
            'Move the continuation inside the branch that owns its roles.',
        )
    closed = [fragment.close() for fragment in (first, second, *rest)]
    return _parallel(closed)


def par(
    first: Fragment[SessionType],
    second: Fragment[SessionType],
    *rest: Fragment[SessionType],
) -> Fragment[SessionType]:
    """Independent composition: *first*, *second* and *rest* run side by side.

    Branches own disjoint roles and exchange no message, so there is no join
    and nothing may follow: writing ``par(...) >> more`` raises, because
    silently absorbing *more* would delete work. Put the continuation inside
    the branch that owns its roles.

    Args:
        first: The first independent branch.
        second: The second independent branch.
        *rest: Any further independent branches.

    Raises:
        ValueError: if something follows the parallel composition, if a branch
            is open, or if two branches share a role.

    Examples:
        >>> from agentsparty.protocol import msg, par, render
        >>> from agentsparty.kernel.role import roles
        >>> Auditor, Scanner, Archivist, Notary = roles('Auditor', 'Scanner', 'Archivist', 'Notary')
        >>> split = par(
        ...     msg[Auditor, Scanner]('Scan'),
        ...     msg[Archivist, Notary]('File'),
        ... ).close()
        >>> print(render(split).splitlines()[0])
        par {
    """
    return Fragment(partial(_build_par, first, second, rest), SessionEnd())


def _parallel(branches: Sequence[SessionType]) -> SessionType:
    """The independent composition of *branches*, in canonical form.

    Nested parallels are flattened, ``end`` branches are dropped, and the
    rest are ordered by their role names, so that equal compositions always
    produce the same value.

    Args:
        branches: The independent protocols to compose.

    Returns:
        ``end`` for no branches, the branch itself for one, a
        :class:`Parallel` otherwise.

    Raises:
        ValueError: if a branch is open (a recursion variable of an enclosing
            ``rec`` cannot cross into a parallel branch), or if two branches
            mention the same role.
    """
    kept = [branch for branch in _flatten_parallel(branches) if branch != SessionEnd()]
    _validate_parallel(kept)
    _assert_disjoint_roles(kept)
    ordered = sorted(kept, key=_branch_order_key)
    if not ordered:
        return SessionEnd()
    if len(ordered) == 1:
        return ordered[0]
    # len(ordered) == 1 returned above, so indices 0 and 1 exist.
    parallel_branches = (ordered[0], ordered[1], *ordered[2:])
    return Parallel(parallel_branches)


def _flatten_parallel(branches: Sequence[SessionType]) -> list[SessionType]:
    return list(
        chain.from_iterable(_flatten_branch(branch) for branch in branches),
    )


def _flatten_branch(branch: SessionType) -> tuple[SessionType, ...]:
    match branch:
        case Parallel(branches=branches):
            return branches
        case _:
            return (branch,)


def _validate_parallel(branches: Sequence[SessionType]) -> None:
    for branch in branches:
        free = free_vars(branch)
        if free:
            names = ', '.join(sorted(free))
            raise ValueError(
                f'a parallel branch must be closed; free recursion '
                f'variable(s) {names} cannot cross a branch boundary',
            )


def _branch_order_key(branch: SessionType) -> tuple[str, ...]:
    """Canonical sort key for a parallel branch: sorted role names."""
    roles = ipart(branch) | epart(branch)
    return tuple(sorted(role.name for role in roles))


def _build_rec(
    name: str,
    body: Fragment[SessionType],
    tail: SessionType,
) -> SessionType:
    if name in free_vars(tail):
        raise ValueError(
            f'sequential tail after rec({name!r}, …) contains a free '
            f'var({name!r}) and would be captured; write it inside the body',
        )
    filled = body.fill(tail)
    if not _is_guarded(name, filled):
        raise ValueError(f'unguarded recursion variable {name!r} in rec body')
    return SessionRec(name, filled)


def rec(name: str, body: Fragment[SessionType]) -> Fragment[SessionType]:
    """Create a recursive session fragment ``μ name.body``."""
    return Fragment(partial(_build_rec, name, body), SessionEnd())


def _build_alt(
    sender: Role,
    receiver: Role,
    first: Case[SessionType],
    *rest: Case[SessionType],
) -> Fragment[SessionType]:
    """Build an internal alternative from *sender* to *receiver*.

    Args:
        sender: The role choosing the branch.
        receiver: The role receiving the chosen message.
        first: The first labelled alternative offered.
        *rest: The remaining labelled alternatives.

    Raises:
        ValueError: if *sender* equals *receiver*.
    """
    return _prefix_fragment(Interaction, sender, receiver, (first, *rest))


class _Alt:
    """Subscript syntax for internal alternatives."""

    def __getitem__(
        self,
        roles: tuple[Role, Role],
    ) -> partial[Fragment[SessionType]]:
        """Pin *sender* and *receiver*; the caller supplies the labelled cases.

        Args:
            roles: The ``(sender, receiver)`` pair written in the subscript.
        """
        sender, receiver = roles
        return partial(_build_alt, sender, receiver)


alt: _Alt = _Alt()


class _Msg:
    """Subscript syntax for message interactions."""

    def __getitem__(
        self,
        roles: tuple[Role, Role],
    ) -> partial[Fragment[SessionType]]:
        """Pin *sender* and *receiver*; the caller supplies the case.

        Args:
            roles: The ``(sender, receiver)`` pair written in the subscript.
        """
        sender, receiver = roles
        return partial(_build_msg, sender, receiver)


msg: _Msg = _Msg()


def _build_msg(
    sender: Role,
    receiver: Role,
    label: str | Label | Case[Any],
    output_type: Codec[Any] = Text,
    intent: str = '',
    *,
    within: Deadline | None = None,
) -> Fragment[SessionType]:
    """A single-message internal interaction from *sender* to *receiver*.

    Args:
        sender: The role sending the message.
        receiver: The role receiving the message.
        label: The message label or an already declared case.
        output_type: The codec for the message payload; defaults to
            :data:`Text`.
        intent: What the sender is asked to produce; shown to whoever authors
            the message and part of the protocol digest. Defaults to empty.
        within: Optional wall-clock deadline for the sender's alt on this
            step; see :func:`~agentsparty.protocol.language.core.case`.

    Returns:
        A one-case interaction fragment.
    """
    match label:
        case Case() as declared:
            return _build_alt(sender, receiver, _case_without_body(declared))
        case _:
            pass
    return _build_alt(
        sender,
        receiver,
        case(label, output_type, intent=intent, within=within),
    )


def _case_without_body(declared: Case[Any]) -> Case[Any]:
    """Keep declaration metadata while leaving the continuation to the DSL."""
    return Case(
        declared.label,
        declared.payload,
        None,
        declared.intent,
        declared.within,
    )


@dataclass(frozen=True, slots=True)
class Boundary:
    """The roles a component owns; everything else it mentions is external.

    Create with :func:`owning` and then call :meth:`defining` with a
    protocol fragment built from :func:`msg` and :func:`alt`::

        Search = owning(Retriever, Ranker)

        search = Search.defining(
            msg[Planner, Retriever]('Query', Text)
            >> msg[Retriever, Ranker]('Candidates', list_of(Text))
            >> msg[Ranker, Retriever]('Ranked', list_of(Text))
            >> msg[Retriever, Writer]('Passages', list_of(Text))
        )

    ``defining`` derives every prefix tag from *owns* and raises
    :exc:`ValueError` when a role in *owns* does not appear in the body.
    """

    owns: frozenset[Role]

    def defining(self, body: Fragment[SessionType] | SessionType) -> SessionType:
        """Resolve the external boundary of *body* from :attr:`owns`.

        Args:
            body: An open fragment or closed session type whose every
                ``msg``/``alt`` prefix will be reclassified.

        Returns:
            A closed :class:`SessionType` with ``ipart(result) == self.owns``.

        Raises:
            ValueError: if a role in *owns* does not participate in *body*,
                or if a prefix mentions two roles and neither is owned.
        """
        resolved = _resolve_boundary(ensure_session(body), self.owns)
        _assert_interface(resolved, self.owns)
        return resolved


def owning(first: Role, /, *rest: Role):
    """Declare a component boundary from the roles it owns.

    Args:
        first: At least one owned role (positional-only; an empty component
            is a static error).
        *rest: Any further owned roles.

    Returns:
        A :class:`Boundary` ready for :meth:`Boundary.defining`.

    Examples:
        >>> from agentsparty.protocol import Text, msg, owning, render
        >>> from agentsparty.kernel.role import roles
        >>> Planner, Retriever, Ranker, Writer = roles('Planner', 'Retriever', 'Ranker', 'Writer')
        >>> Search = owning(Retriever, Ranker)
        >>> search = Search.defining(
        ...     msg[Planner, Retriever]('Query', Text)
        ...     >> msg[Retriever, Ranker]('Candidates', Text)
        ...     >> msg[Ranker, Retriever]('Ranked', Text)
        ...     >> msg[Retriever, Writer]('Passages', Text)
        ... )
        >>> print(render(search).splitlines()[0])
        Planner?Retriever : Query(str)
    """
    return Boundary(frozenset((first, *rest)))


def _build_prefix(
    kind: type[Interaction] | type[SendTo] | type[RecvFrom],
    sender: Role,
    receiver: Role,
    alternatives: tuple[Case[SessionType], ...],
    tail: SessionType,
) -> SessionType:
    return kind(
        sender,
        receiver,
        branches_map(
            SessionBranchCase(
                alternative.label,
                alternative.payload,
                _continuation(alternative.body, tail, SessionEnd()),
                alternative.intent,
                alternative.within,
            )
            for alternative in alternatives
        ),
    )


def _prefix_fragment(
    kind: type[Interaction] | type[SendTo] | type[RecvFrom],
    sender: Role,
    receiver: Role,
    cases: NonEmptyTuple[Case[SessionType]],
) -> Fragment[SessionType]:
    if sender == receiver:
        raise ValueError(f'{sender.name} cannot talk to itself')
    alternatives = _bodies(cases)

    return Fragment(
        partial(_build_prefix, kind, sender, receiver, alternatives),
        SessionEnd(),
    )
