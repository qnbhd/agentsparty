"""Runtime laws for parallel composition: scheduler independence, replay, cancel."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from agentsparty.journal import ROOT_TRACK, MemoryJournal
from agentsparty.kernel.role import Role, roles
from agentsparty.machine import Machine, View
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import Text, msg, par, project
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.runtime import AgentRuntime

Auditor, Scanner, Archivist, Notary = roles('Auditor', 'Scanner', 'Archivist', 'Notary')


def _split_proto():
    return par(
        msg[Auditor, Scanner]('Scan', Text),
        msg[Archivist, Notary]('File', Text),
    ).close()


def _machines():
    def always(view: View) -> Choice:
        return Choice(view.offered[0], 'ok')

    proto = _split_proto()
    return [
        Machine(Auditor, proto, always),
        Machine(Scanner, proto, always),
        Machine(Archivist, proto, always),
        Machine(Notary, proto, always),
    ]


@dataclass
class _SlowPeer:
    role: Role
    endpoint_contract: EndpointType
    delay: float
    selects: int = 0

    async def select(self, receiver, branches):
        self.selects += 1
        await asyncio.sleep(self.delay)
        branch = min(branches.values(), key=lambda b: b.label)
        return Chosen(branch=branch, payload='ok', raw='ok')

    async def offer(self, envelope: Envelope) -> None:
        pass

    async def recall(self, envelope: Envelope) -> None:
        pass

    async def cancel(self, notice: Cancelled) -> None:
        pass


async def _scheduler_result(proto, delays) -> tuple:
    roles_ = [Auditor, Scanner, Archivist, Notary]
    peers = [
        _SlowPeer(role, project(proto, role), delay)
        for role, delay in zip(roles_, delays, strict=True)
    ]
    journal = MemoryJournal()
    trace = await AgentRuntime(proto, peers, journal=journal).run()
    return (
        tuple(
            (d.step.track.path, d.step.position, d.label.name, d.raw)
            for d in journal.script().decisions
        ),
        tuple((e.sender.name, e.receiver.name, e.label.name) for e in trace),
    )


async def test_parallel_session_runs_to_end() -> None:
    """A protocol with par delivers both branch messages in canonical order."""
    proto = _split_proto()
    journal = MemoryJournal()
    trace = await AgentRuntime(proto, _machines(), journal=journal).run()
    labels = [envelope.label.name for envelope in trace]
    # Canonical track order: branch 0 then branch 1 after monoid sort by roles.
    # Archivist/Notary sort before Auditor/Scanner alphabetically on first role.
    assert set(labels) == {'Scan', 'File'}
    assert len(trace) == 2
    script = journal.script()
    assert script.length == 2
    # two tracks under root
    tracks = set(script.words)
    assert len(tracks) == 2
    assert ROOT_TRACK not in tracks or script.length_of(ROOT_TRACK) == 0


async def test_full_replay_makes_zero_selects() -> None:
    """Full journal reproduces trace without select."""
    proto = _split_proto()
    full = MemoryJournal()
    baseline = await AgentRuntime(proto, _machines(), journal=full).run()

    @dataclass
    class Counting:
        role: Role
        endpoint_contract: EndpointType
        selects: int = 0

        async def select(self, receiver, branches):
            self.selects += 1
            branch = min(branches.values(), key=lambda b: b.label)
            return Chosen(branch=branch, payload='ok', raw='ok')

        async def offer(self, envelope: Envelope) -> None:
            pass

        async def recall(self, envelope: Envelope) -> None:
            pass

        async def cancel(self, notice: Cancelled) -> None:
            pass

    peers = [Counting(role, project(proto, role)) for role in [Auditor, Scanner, Archivist, Notary]]
    trace = await AgentRuntime(proto, peers, journal=MemoryJournal(full.script().decisions)).run()
    assert trace == baseline
    assert all(peer.selects == 0 for peer in peers)


async def test_partial_track_resume() -> None:
    """Dropping one track continues only that track; sibling is not re-asked."""
    from types import MappingProxyType

    from agentsparty.journal.types import Script

    proto = _split_proto()
    full = MemoryJournal()
    await AgentRuntime(proto, _machines(), journal=full).run()
    script = full.script()
    missing = next(iter(script.words))
    kept = {t: w for t, w in script.words.items() if t != missing}
    partial = Script(MappingProxyType(kept))
    selects: dict[str, int] = {r.name: 0 for r in [Auditor, Scanner, Archivist, Notary]}

    @dataclass
    class Peer:
        role: Role
        endpoint_contract: EndpointType

        async def select(self, receiver, branches):
            selects[self.role.name] += 1
            branch = min(branches.values(), key=lambda b: b.label)
            return Chosen(branch=branch, payload='ok', raw='ok')

        async def offer(self, envelope: Envelope) -> None:
            pass

        async def recall(self, envelope: Envelope) -> None:
            pass

        async def cancel(self, notice: Cancelled) -> None:
            pass

    peers = [Peer(role, project(proto, role)) for role in [Auditor, Scanner, Archivist, Notary]]
    await AgentRuntime(proto, peers, journal=MemoryJournal(partial.decisions)).run()
    assert sum(1 for count in selects.values() if count > 0) >= 1
    kept_track = next(t for t in script.words if t != missing)
    for name in {d.sender.name for d in script.words[kept_track]}:
        assert selects[name] == 0


async def test_canonical_concatenation() -> None:
    """Trace(par(A,B)) is track-major order of the branch traces."""
    proto = _split_proto()
    journal = MemoryJournal()
    trace = await AgentRuntime(proto, _machines(), journal=journal).run()
    # run each branch alone
    left = msg[Auditor, Scanner]('Scan', Text).close()
    right = msg[Archivist, Notary]('File', Text).close()

    async def run_one(p, roles_):
        def always(view: View) -> Choice:
            return Choice(view.offered[0], 'ok')

        peers = [Machine(r, p, always) for r in roles_]
        return await AgentRuntime(p, peers).run()

    from agentsparty.protocol import participants
    from agentsparty.protocol.session._syntax import _branch_order_key

    ordered = sorted([left, right], key=_branch_order_key)
    expected = []
    for branch in ordered:
        roles_ = list(participants(branch))
        expected.extend(await run_one(branch, roles_))
    assert [e.label.name for e in trace] == [e.label.name for e in expected]


async def test_role_per_track() -> None:
    """Roles on different tracks are pairwise disjoint."""
    proto = _split_proto()
    journal = MemoryJournal()
    await AgentRuntime(proto, _machines(), journal=journal).run()
    by_track: dict = {}
    for decision in journal.script().decisions:
        by_track.setdefault(decision.step.track, set()).update(
            {decision.sender.name, decision.receiver.name},
        )
    tracks = list(by_track.values())
    for i, a in enumerate(tracks):
        for b in tracks[i + 1 :]:
            assert a.isdisjoint(b)


async def test_scheduler_independence() -> None:
    """Different artificial delays still yield the same Script and trace."""
    proto = _split_proto()

    results = [
        await _scheduler_result(proto, delays)
        for delays in (
            (0.0, 0.0, 0.0, 0.0),
            (0.02, 0.0, 0.01, 0.0),
            (0.0, 0.03, 0.0, 0.01),
            (0.01, 0.01, 0.02, 0.0),
        )
    ]
    first = results[0]
    for other in results[1:]:
        assert other == first


@dataclass
class _CancellationPeer:
    role: Role
    endpoint_contract: EndpointType
    cancelled: dict[str, int]
    fail: bool = False
    selected_after_cancel: bool = False
    _cancelled: bool = False

    async def select(self, receiver, branches):
        if self._cancelled:
            self.selected_after_cancel = True
        if self.fail:
            raise RuntimeError('branch failed')
        await asyncio.sleep(0.05)
        branch = min(branches.values(), key=lambda b: b.label)
        return Chosen(branch=branch, payload='ok', raw='ok')

    async def offer(self, envelope: Envelope) -> None:
        pass

    async def recall(self, envelope: Envelope) -> None:
        pass

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled[self.role.name] += 1
        self._cancelled = True


async def test_sibling_cancellation() -> None:
    """A failing branch cancels siblings; each participant cancels once."""
    proto = _split_proto()
    cancelled: dict[str, int] = {r.name: 0 for r in [Auditor, Scanner, Archivist, Notary]}

    # Fail the Auditor (sends Scan); Archivist side should be cancelled.
    peers = [
        _CancellationPeer(Auditor, project(proto, Auditor), cancelled, fail=True),
        _CancellationPeer(Scanner, project(proto, Scanner), cancelled),
        _CancellationPeer(Archivist, project(proto, Archivist), cancelled),
        _CancellationPeer(Notary, project(proto, Notary), cancelled),
    ]
    with pytest.raises(RuntimeError, match='branch failed'):
        await AgentRuntime(proto, peers).run()
    assert all(count == 1 for count in cancelled.values())
    assert not any(p.selected_after_cancel for p in peers)
