"""Human-readable rendering of session and endpoint types.

Unstable format: suitable for diagrams and diagnostics, not for digests.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from typing_extensions import assert_never

from agentsparty.protocol.language.core import Deadline, Fragment, Label
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointBranchCase,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    EndpointVar,
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

__all__ = ['render']

_INDENT: Final = '  '

MICROSECONDS_PER_SECOND: Final = 1_000_000
SECONDS_PER_MINUTE: Final = 60
MINUTES_PER_HOUR: Final = 60
HOURS_PER_DAY: Final = 24
MICROSECONDS_PER_MINUTE: Final = SECONDS_PER_MINUTE * MICROSECONDS_PER_SECOND
MICROSECONDS_PER_HOUR: Final = MINUTES_PER_HOUR * MICROSECONDS_PER_MINUTE
MICROSECONDS_PER_DAY: Final = HOURS_PER_DAY * MICROSECONDS_PER_HOUR


def render(
    node: SessionType | EndpointType | Fragment[SessionType],
    indent: int = 0,
) -> str:
    """Render *node* as an indented text diagram.

    An open session :class:`~agentsparty.protocol.language.core.Fragment` is closed at this
    boundary so callers need not write ``.close()`` only to print a diagram.

    Args:
        node: The protocol to render, or a session fragment that will be closed.
        indent: Number of two-space levels to indent the root.

    Returns:
        The rendered text, one line per protocol node.
    """
    match node:
        case Fragment() as fragment:
            return render(cast(SessionType, fragment.close()), indent=indent)
        case _:
            return _render_node(node, indent)


def _render_node(node: SessionType | EndpointType, indent: int) -> str:
    match node:
        case (
            SessionEnd()
            | SessionVar()
            | SessionRec()
            | Interaction()
            | SendTo()
            | RecvFrom()
            | Parallel()
        ):
            return _render_session_node(node, indent)
        case EndpointEnd() | EndpointVar() | EndpointRec() | EndpointSelect() | EndpointBranch():
            return _render_endpoint_node(node, indent)
        case _:  # pragma: no cover
            assert_never(node)


def _render_session_node(node: SessionType, indent: int) -> str:
    pad = _INDENT * indent
    match node:
        case SessionEnd():
            return f'{pad}end'
        case SessionVar(name=name):
            return f'{pad}{name}'
        case SessionRec(name=name, body=body):
            return f'{pad}rec {name}\n{render(body, indent + 1)}'
        case Interaction() | SendTo() | RecvFrom() as prefix:
            return _render_session_prefix(prefix, indent)
        case Parallel(branches=branches):
            return _render_parallel(branches, indent)
        case _:  # pragma: no cover
            assert_never(node)


def _render_endpoint_node(node: EndpointType, indent: int) -> str:
    pad = _INDENT * indent
    match node:
        case EndpointEnd():
            return f'{pad}end'
        case EndpointVar(name=name):
            return f'{pad}{name}'
        case EndpointRec(name=name, body=body):
            return f'{pad}rec {name}\n{render(body, indent + 1)}'
        case EndpointSelect() | EndpointBranch() as prefix:
            return _render_endpoint_prefix(prefix, indent)
        case _:  # pragma: no cover
            assert_never(node)


def _render_session_prefix(prefix: Interaction | SendTo | RecvFrom, indent: int) -> str:
    match prefix:
        case Interaction(sender=sender, receiver=receiver, branches=branches):
            return _render(f'{sender.name} -> {receiver.name}', branches, indent)
        case SendTo(sender=sender, receiver=receiver, branches=branches):
            return _render(f'{sender.name}!{receiver.name}', branches, indent)
        case RecvFrom(sender=sender, receiver=receiver, branches=branches):
            return _render(f'{sender.name}?{receiver.name}', branches, indent)
        case _:  # pragma: no cover
            assert_never(prefix)


def _render_endpoint_prefix(prefix: EndpointSelect | EndpointBranch, indent: int) -> str:
    match prefix:
        case EndpointSelect(receiver=receiver, branches=branches):
            return _render(f'!{receiver.name}', branches, indent)
        case EndpointBranch(sender=sender, branches=branches):
            return _render(f'?{sender.name}', branches, indent)
        case _:  # pragma: no cover
            assert_never(prefix)


def _render_parallel(branches: tuple[SessionType, ...], indent: int) -> str:
    pad = _INDENT * indent
    lines: list[str] = [f'{pad}par {{']
    for branch in branches:
        lines.extend((f'{pad}  |', render(branch, indent + 2)))
    lines.append(f'{pad}}}')
    return '\n'.join(lines)


def _render(
    head: str,
    branches: Mapping[Label, SessionBranchCase] | Mapping[Label, EndpointBranchCase],
    indent: int,
) -> str:
    pad = _INDENT * indent
    ordered = sorted(branches.values(), key=lambda branch: branch.label)
    if len(ordered) == 1:
        return _render_single(pad, head, ordered[0], indent)
    return _render_alt(pad, head, ordered, indent)


def _render_single(
    pad: str,
    head: str,
    only: SessionBranchCase | EndpointBranchCase,
    indent: int,
) -> str:
    signature = _signature(only)
    body = render(only.continuation, indent)
    return f'{pad}{head} : {signature}\n{body}'


def _render_alt(
    pad: str,
    head: str,
    ordered: list[SessionBranchCase | EndpointBranchCase],
    indent: int,
) -> str:
    lines = [f'{pad}{head} {{']
    lines.extend(_alt_lines(pad, ordered, indent))
    lines.append(f'{pad}}}')
    return '\n'.join(lines)


def _alt_lines(
    pad: str,
    ordered: list[SessionBranchCase | EndpointBranchCase],
    indent: int,
) -> list[str]:
    lines: list[str] = []
    for branch in ordered:
        signature = _signature(branch)
        continuation = render(branch.continuation, indent + 2)
        lines.extend((f'{pad}  {signature}:', continuation))
    return lines


def _signature(branch: SessionBranchCase | EndpointBranchCase) -> str:
    payload_name = branch.payload.name
    if branch.payload.carries_value:
        shape = f'{branch.label}({payload_name})'
    else:
        shape = f'{branch.label}()'
    if branch.within is not None:
        shape = f'{shape} @{_format_within(branch.within)}'
    if not branch.intent:
        return shape
    # `!r` keeps a multi-line intent on one line, so `render` stays
    # one-line-per-node.
    return f'{shape} :: {branch.intent!r}'


def _format_within(window: Deadline) -> str:
    """Compact rendering of a positive wall-clock window (``30m``, ``0.5s``).

    Preserves full :class:`~datetime.timedelta` precision (microseconds) so
    distinct deadlines never collide in ``render`` — e.g. ``500ms`` and
    ``999ms`` become ``0.5s`` and ``0.999s``, not both ``0s``.
    """
    # Integer microseconds avoid float rounding that would re-collapse values.
    micros = (
        window.duration.days * HOURS_PER_DAY * MINUTES_PER_HOUR * SECONDS_PER_MINUTE
        + window.duration.seconds
    ) * MICROSECONDS_PER_SECOND + window.duration.microseconds
    days, micros = divmod(micros, MICROSECONDS_PER_DAY)
    hours, micros = divmod(micros, MICROSECONDS_PER_HOUR)
    minutes, micros = divmod(micros, MICROSECONDS_PER_MINUTE)
    parts: list[str] = []
    if days:
        parts.append(f'{days}d')
    if hours:
        parts.append(f'{hours}h')
    if minutes:
        parts.append(f'{minutes}m')
    if micros or not parts:
        parts.append(_format_seconds(micros))
    return ''.join(parts)


def _format_seconds(micros: int) -> str:
    secs, frac = divmod(micros, MICROSECONDS_PER_SECOND)
    if frac == 0:
        return f'{secs}s'
    return _format_fractional_seconds(secs, frac)


def _format_fractional_seconds(secs: int, frac: int) -> str:
    # Drop trailing zeros in the fractional part only (0.500000 → 0.5).
    fraction = format(frac, '06d')
    formatted = f'{secs}.{fraction}'
    trimmed = formatted.rstrip('0')
    return f'{trimmed}s'
