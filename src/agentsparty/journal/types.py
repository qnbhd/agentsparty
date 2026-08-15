"""The journal contract: what a recorded decision is and where it goes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Protocol, TypeVar

from agentsparty._utils.assertions import pre, require_positive
from agentsparty.journal._canonical import canonical_protocol
from agentsparty.kernel.errors import JournalError
from agentsparty.protocol.language.core import BranchCodec, Label, RawValue
from agentsparty.protocol.session.types import SessionType

__all__ = [
    'EMPTY_SCRIPT',
    'FIRST_STEP',
    'NULL_JOURNAL',
    'ROOT_TRACK',
    'Decision',
    'Digest',
    'Journal',
    'NoJournal',
    'Script',
    'SessionId',
    'StepIndex',
    'Track',
    'digest_of',
]
from agentsparty.kernel.role import Role

BC = TypeVar('BC', bound=BranchCodec)
DIGEST_LENGTH = 16
"""Number of hexadecimal characters retained in a protocol digest."""


@dataclass(frozen=True, order=True, slots=True)
class Track:
    """Which independent branch of a protocol a decision belongs to.

    The empty path is the session's root track; entering branch *index* of a
    :class:`~agentsparty.protocol.session.Parallel` appends *index*. Parallel
    branches own disjoint roles, so every role — and therefore every
    participant — belongs to exactly one track, and a track's own decisions
    are totally ordered whatever the scheduler does.
    """

    path: tuple[int, ...]

    def branch(self, index: int) -> Track:
        """The track of parallel branch *index* inside this one.

        Args:
            index: Position of the branch in its parallel node.
        """
        pre(expr=index >= 0, message='a branch index counts from zero')
        return Track((*self.path, index))

    def under(self, other: Track) -> bool:
        """Whether this track is *other* or a branch nested inside it.

        Args:
            other: The candidate ancestor.
        """
        return self.path[: len(other.path)] == other.path


ROOT_TRACK: Track = Track(())
"""The track a session starts on: everything before the first parallel node."""


@dataclass(frozen=True, order=True, slots=True)
class StepIndex:
    """Where a decision sits: which track, and which position within it.

    Ordering is the *canonical* order — track-major, then position. It is a
    linear extension of the causal order, not the causal order itself: two
    steps on different tracks compare, but neither happened before the other.
    """

    track: Track
    position: int

    def __post_init__(self) -> None:
        """Reject a position before the first message on a track."""
        require_positive('step position starts at one', self.position)

    def next(self) -> StepIndex:
        """The position of the next message on the same track."""
        return StepIndex(self.track, self.position + 1)


FIRST_STEP: StepIndex = StepIndex(ROOT_TRACK, 1)
"""The position of the first message on the root track."""


@dataclass(frozen=True, slots=True)
class Digest:
    """Fingerprint of the protocol a journal belongs to."""

    value: str


def digest_of(proto: SessionType) -> Digest:
    """Fingerprint *proto* by its canonical structural encoding.

    Two protocols share a digest exactly when they have the same roles, labels,
    branch structure, payload codec names, intents and deadlines. Arm and
    ``Parallel`` branch order do not matter. A journal carries the digest of
    the protocol it was written under, so replaying it against a changed
    protocol fails at the boundary instead of decoding into the wrong session.

    Args:
        proto: The choreography to fingerprint.
    """
    return Digest(sha256(canonical_protocol(proto)).hexdigest()[:DIGEST_LENGTH])


@dataclass(frozen=True, slots=True)
class SessionId:
    """Identity of one recorded session."""

    value: str


@dataclass(frozen=True, slots=True)
class Decision:
    """One authored alt: the only fact a session cannot recompute.

    The roles, the label and the codec name are implied by the protocol and
    the steps before this one; they are recorded anyway, as a checksum against
    an edited or foreign journal, and so the file reads on its own.
    """

    step: StepIndex
    sender: Role
    receiver: Role
    label: Label
    codec: str
    raw: RawValue

    def branch_in(
        self,
        sender: Role,
        receiver: Role,
        branches: Mapping[Label, BC],
    ) -> BC:
        """The branch this decision names at the node reached at its step.

        Args:
            sender: The sender of the interaction reached at this step.
            receiver: The receiver of that interaction.
            branches: The labelled alternatives that interaction offers.

        Returns:
            The recorded branch.

        Raises:
            JournalError: if the recorded roles, label or codec do not fit that
                node — the journal was edited, or belongs to another protocol.
        """
        where = _step_where(self.step)
        if (sender, receiver) != (self.sender, self.receiver):
            recorded = _role_pair(self.sender, self.receiver)
            actual = _role_pair(sender, receiver)
            raise JournalError(
                f'step {where} was recorded as {recorded}, but the protocol reaches {actual} there',
            )
        if self.label not in branches:
            raise JournalError(
                f'step {where} recorded label {self.label}, '
                f'but the protocol offers: {_offered_labels(branches)}',
            )
        branch = branches[self.label]
        if self.codec != branch.payload.name:
            payload_name = branch.payload.name
            raise JournalError(
                f'step {where} recorded codec {self.codec!r}, but the '
                f'protocol offers {payload_name!r} there',
            )
        return branch


def _step_where(step: StepIndex) -> str:
    track_path = step.track.path
    position = step.position
    return f'{track_path} #{position}'


def _role_pair(sender: Role, receiver: Role) -> str:
    sender_name = sender.name
    receiver_name = receiver.name
    return f'{sender_name} -> {receiver_name}'


def _offered_labels(branches: Mapping[Label, BC]) -> str:
    return ', '.join(str(label) for label in branches)


def _group_by_track(entries: Iterable[Decision]) -> dict[Track, list[Decision]]:
    grouped: dict[Track, list[Decision]] = {}
    for decision in entries:
        grouped.setdefault(decision.step.track, []).append(decision)
    return grouped


def _word(track: Track, group: list[Decision]) -> tuple[Decision, ...]:
    numbers = tuple(decision.step.position for decision in group)
    expected = tuple(range(1, len(group) + 1))
    if numbers != expected:
        raise JournalError(
            f'journal steps on track {track.path} must run 1..{len(group)} in order, got {numbers}',
        )
    return tuple(group)


@dataclass(frozen=True, slots=True)
class Script:
    """The decisions of one session: one contiguous word per track.

    A journal *file* is a linearisation: entries from independent tracks may
    interleave in any order, because the protocol never ordered them. This is
    the boundary that turns that word back into the trace it denotes —
    :meth:`of` groups entries by track and requires ``1..n`` inside each
    group. Nothing downstream re-checks.
    """

    words: Mapping[Track, tuple[Decision, ...]]

    @classmethod
    def of(cls, entries: Iterable[Decision]) -> Script:
        """Parse *entries* into a script.

        Groups by track, preserving appearance order within each group, and
        requires positions ``1..n`` inside every group. Order between groups is
        free: independent tracks have no causal order.

        Args:
            entries: Recorded decisions, free interleaving across tracks.

        Returns:
            The parsed script.

        Raises:
            JournalError: if positions on any track are not ``1..n`` in order.
        """
        grouped = _group_by_track(entries)
        words = {track: _word(track, group) for track, group in grouped.items()}
        return cls(MappingProxyType(words))

    @property
    def decisions(self) -> tuple[Decision, ...]:
        """Every decision in canonical order (track-major, then position)."""
        ordered_tracks = sorted(self.words)
        decisions = (decision for track in ordered_tracks for decision in self.words[track])
        return tuple(decisions)

    @property
    def length(self) -> int:
        """How many decisions this script holds, over every track."""
        return sum(len(word) for word in self.words.values())

    def length_of(self, track: Track) -> int:
        """How many steps this script already decides on *track*."""
        return len(self.words.get(track, ()))

    def at(self, step: StepIndex) -> Decision:
        """The decision recorded for *step*.

        Args:
            step: A position this script decides.
        """
        word = self.words.get(step.track, ())
        track_path = step.track.path
        position = step.position
        pre(
            expr=position <= len(word),
            message=f'step {track_path} #{position} is not in the script',
        )
        return word[step.position - 1]

    def upto(self, step: StepIndex) -> Script:
        """The causal prefix that ends at *step* — the fork operation.

        The track of *step* is truncated to *step.position*. Strict
        descendants of that track are dropped only when the truncation
        actually removes something (they exist only because the parent
        reached its parallel node). Independent tracks are left untouched:
        they share no causal order with *step*.

        Args:
            step: The last position to keep on its track.
        """
        where = _step_where(step)
        pre(
            expr=step.position <= self.length_of(step.track),
            message=f'step {where} is not in the script',
        )
        truncated = step.position < self.length_of(step.track)
        kept: dict[Track, tuple[Decision, ...]] = {}
        for track, word in self.words.items():
            if track == step.track:
                kept[track] = word[: step.position]
            elif truncated and track.under(step.track) and track != step.track:
                continue
            else:
                kept[track] = word
        return Script(MappingProxyType(kept))


def _check_append(script: Script, decision: Decision) -> None:
    """Require *decision* to extend its track by exactly one step."""
    # resolve the next position on the decision's track:
    recorded = script.length_of(decision.step.track)
    track_path = decision.step.track.path
    position = decision.step.position
    next_position = recorded + 1
    pre(
        expr=position == next_position,
        message=f'append must extend track {track_path} step {next_position}, got {position}',
    )


EMPTY_SCRIPT: Script = Script(MappingProxyType({}))
"""The script of a session that has not decided anything yet."""


class Journal(Protocol):
    """Durable, append-only record of the decisions a session made."""

    def script(self) -> Script:
        """Everything decided so far, in step order."""
        ...

    def append(self, decision: Decision) -> None:
        """Record *decision* durably.

        Called before the message is delivered, so a crash during delivery
        cannot lose an answer that was already paid for. Unlike
        :meth:`~agentsparty.tracing.types.Tracer.record`, ``append`` may not drop:
        a decision that is not durable is a decision the session cannot
        recover.

        Args:
            decision: The alt to record.
        """
        ...


class NoJournal:
    """Journal that records nothing; the runtime default."""

    def script(self) -> Script:
        """Return the empty script: nothing was ever recorded."""
        return EMPTY_SCRIPT

    def append(self, decision: Decision) -> None:
        """Discard *decision*.

        Args:
            decision: The alt to discard.
        """


NULL_JOURNAL: Journal = NoJournal()
"""The journal used when persistence is not switched on."""
