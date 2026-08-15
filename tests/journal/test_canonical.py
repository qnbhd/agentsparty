"""Laws for protocol digest canonical encoding (version 1)."""

from __future__ import annotations

from datetime import timedelta

from agentsparty.journal._canonical import canonical_protocol
from agentsparty.journal.types import digest_of
from agentsparty.kernel.role import roles
from agentsparty.protocol import Deadline, Text, alt, case, msg, par, rec, var
from agentsparty.protocol.language.core import Label, branches_map
from agentsparty.protocol.session import Interaction, SessionBranchCase, SessionEnd

_PREFIX = b'agentsparty/protocol-digest/1\0'


def test_canonical_version_1_prefix_and_golden() -> None:
    """Golden for a minimal closed protocol under canonical version 1."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    raw = canonical_protocol(proto)
    assert raw.startswith(_PREFIX)
    # Fixed structural shape; hash of full bytes is the public digest.
    assert digest_of(proto).value == '114992761c1eb713'
    assert len(digest_of(proto).value) == 16


def test_arm_order_does_not_affect_digest() -> None:
    A, B = roles('A', 'B')
    yes = SessionBranchCase(Label('yes'), Text, SessionEnd())
    no = SessionBranchCase(Label('no'), Text, SessionEnd())
    first = Interaction(A, B, branches_map([yes, no]))
    second = Interaction(A, B, branches_map([no, yes]))
    assert canonical_protocol(first) == canonical_protocol(second)
    assert digest_of(first) == digest_of(second)


def test_parallel_order_does_not_affect_digest() -> None:
    A, B, C, D = roles('A', 'B', 'C', 'D')
    left = msg[A, B]('L', Text)
    right = msg[C, D]('R', Text)
    assert digest_of(par(left, right).close()) == digest_of(par(right, left).close())
    assert canonical_protocol(par(left, right).close()) == canonical_protocol(
        par(right, left).close(),
    )


def test_structural_change_changes_digest() -> None:
    A, B = roles('A', 'B')
    X, Y = roles('X', 'Y')
    base = msg[A, B]('Hi', Text).close()
    variants = [
        msg[A, B]('Bye', Text).close(),
        msg[X, Y]('Hi', Text).close(),
        msg[A, B]('Hi', Text, 'say hello').close(),
        msg[A, B]('Hi', Text, within=Deadline(timedelta(seconds=1))).close(),
        (msg[A, B]('Hi', Text) >> msg[A, B]('Ok')).close(),
    ]
    for other in variants:
        assert digest_of(base) != digest_of(other)


def test_codec_name_change_changes_digest() -> None:
    from agentsparty.protocol import Nothing

    A, B = roles('A', 'B')
    with_text = msg[A, B]('Hi', Text).close()
    with_nothing = msg[A, B]('Hi', Nothing).close()
    assert digest_of(with_text) != digest_of(with_nothing)


def test_rec_continuation_in_digest() -> None:
    A, B = roles('A', 'B')
    looped = rec('t', msg[A, B]('Hi') >> var('t')).close()
    once = msg[A, B]('Hi').close()
    assert digest_of(looped) != digest_of(once)
    assert canonical_protocol(looped).startswith(_PREFIX)


def test_alt_arm_labels_sorted() -> None:
    """alt arms in different declaration order share a digest."""
    A, B = roles('A', 'B')
    first = alt[A, B](
        case('yes', Text),
        case('no', Text),
    ).close()
    second = alt[A, B](
        case('no', Text),
        case('yes', Text),
    ).close()
    assert digest_of(first) == digest_of(second)
