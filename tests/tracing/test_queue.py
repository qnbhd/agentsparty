"""QueueTracer and watching: events surface while the session runs."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from agentsparty.kernel.role import Role, roles
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import Label, Text, msg, project
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.runtime import AgentRuntime
from agentsparty.tracing import (
    STEP,
    MemoryTracer,
    QueueTracer,
    describe,
    fanout,
    watching,
)


@dataclass
class Stub:
    role: Role
    endpoint_contract: EndpointType
    alts: list[Choice] = field(default_factory=list)
    received: list[Envelope] = field(default_factory=list)
    gate: asyncio.Event | None = None
    fail: bool = False
    cancelled: list[Cancelled] = field(default_factory=list)

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        if self.gate is not None:
            await self.gate.wait()
        if self.fail:
            raise RuntimeError('peer failed')
        scripted = self.alts.pop(0)
        branch = branches[scripted.label]
        return Chosen(branch=branch, payload=scripted.payload, raw=scripted.payload)

    async def offer(self, envelope: Envelope) -> None:
        self.received.append(envelope)

    async def recall(self, envelope: Envelope) -> None:
        pass

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled.append(notice)


async def test_events_arrive_before_the_session_ends() -> None:
    """session.started is yielded before the run finishes."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    gate = asyncio.Event()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')], gate=gate)
    b = Stub(B, project(proto, B))
    tracer = QueueTracer()
    runtime = AgentRuntime(proto, [a, b], tracer=tracer)

    async def consume() -> list[str]:
        names: list[str] = []
        async with watching(runtime.run(), tracer) as watch:
            names.extend([_name_and_release(event, gate) async for event in watch])
        return names

    def _name_and_release(event, release: asyncio.Event) -> str:
        name = describe(event.signal).name
        if name == 'session.started':
            # session is still running: gate not yet released
            assert not release.is_set()
            release.set()
        return name

    names = await consume()
    assert names[0] == 'session.started'
    assert 'session.finished' in names


async def test_watch_yields_every_recorded_event() -> None:
    """watch sequence equals MemoryTracer for the same run."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()

    mem = MemoryTracer()
    a1 = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b1 = Stub(B, project(proto, B))
    await AgentRuntime(proto, [a1, b1], tracer=mem).run()
    mem_names = mem.names()

    tracer = QueueTracer()
    a2 = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b2 = Stub(B, project(proto, B))
    runtime = AgentRuntime(proto, [a2, b2], tracer=tracer)

    async def collect() -> list[str]:
        async with watching(runtime.run(), tracer) as watch:
            return [describe(e.signal).name async for e in watch]

    assert await collect() == mem_names


async def test_watch_reraises_a_failed_session() -> None:
    """Pre-failure events are yielded; the exception re-raises after drain."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a = Stub(A, project(proto, A), fail=True)
    b = Stub(B, project(proto, B))
    tracer = QueueTracer()
    runtime = AgentRuntime(proto, [a, b], tracer=tracer)

    async def consume() -> list[str]:
        names: list[str] = []
        async with watching(runtime.run(), tracer) as watch:
            names.extend([describe(event.signal).name async for event in watch])
        return names

    with pytest.raises(RuntimeError, match='peer failed'):
        await consume()

    # re-run capturing names up to failure via a dual approach:
    tracer2 = QueueTracer()
    a2 = Stub(A, project(proto, A), fail=True)
    b2 = Stub(B, project(proto, B))
    runtime2 = AgentRuntime(proto, [a2, b2], tracer=tracer2)
    names: list[str] = []

    async def capture() -> None:
        try:
            async with watching(runtime2.run(), tracer2) as watch:
                async for event in watch:
                    names.extend((describe(event.signal).name,))
        except RuntimeError:
            pass

    await capture()
    assert 'session.started' in names
    assert 'step.started' in names
    assert 'failed' in names


async def test_the_result_is_the_watch() -> None:
    """await watch equals what await runtime.run() would return."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b = Stub(B, project(proto, B))
    direct = await AgentRuntime(proto, [a, b]).run()

    a2 = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b2 = Stub(B, project(proto, B))
    tracer = QueueTracer()
    runtime = AgentRuntime(proto, [a2, b2], tracer=tracer)

    async def via_watch():
        async with watching(runtime.run(), tracer) as watch:
            return await watch

    assert await via_watch() == direct


async def test_awaiting_before_iterating_loses_nothing() -> None:
    """await before the loop still yields every name MemoryTracer saw."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()

    mem = MemoryTracer()
    a1 = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b1 = Stub(B, project(proto, B))
    await AgentRuntime(proto, [a1, b1], tracer=mem).run()
    mem_names = mem.names()

    tracer = QueueTracer()
    a2 = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')])
    b2 = Stub(B, project(proto, B))
    runtime = AgentRuntime(proto, [a2, b2], tracer=tracer)

    async def collect() -> list[str]:
        async with watching(runtime.run(), tracer) as watch:
            await watch
            return [describe(e.signal).name async for e in watch]

    assert await collect() == mem_names


async def test_leaving_early_stops_the_session() -> None:
    """Leaving the block on the first event cancels a still-running session."""
    A, B = roles('A', 'B')
    proto = msg[A, B]('Hi', Text).close()
    gate = asyncio.Event()
    a = Stub(A, project(proto, A), alts=[Choice(Label('Hi'), 'yo')], gate=gate)
    b = Stub(B, project(proto, B))
    tracer = QueueTracer()
    runtime = AgentRuntime(proto, [a, b], tracer=tracer)
    task: asyncio.Task[object] | None = None

    async def consume() -> None:
        nonlocal task
        async with watching(runtime.run(), tracer) as watch:
            task = watch._task
            async for event in watch:
                if describe(event.signal).name == 'session.started':
                    break

    await consume()
    assert task is not None
    assert task.cancelled()
    assert b.received == []


async def test_select_is_the_filter() -> None:
    """select(STEP) yields exactly the STEP subsequence of the full tape."""
    A, B = roles('A', 'B')
    proto = (msg[A, B]('Hi', Text) >> msg[B, A]('Bye', Text)).close()
    mem = MemoryTracer()
    queue = QueueTracer()
    tracer = fanout(mem, queue)
    a = Stub(
        A,
        project(proto, A),
        alts=[Choice(Label('Hi'), 'hello')],
    )
    b = Stub(
        B,
        project(proto, B),
        alts=[Choice(Label('Bye'), 'later')],
    )
    runtime = AgentRuntime(proto, [a, b], tracer=tracer)

    async def collect() -> list[str]:
        async with watching(runtime.run(), queue) as watch:
            return [describe(e.signal).name async for e in watch.select(STEP)]

    selected = await collect()
    expected = [describe(e.signal).name for e in mem.events if e.signal in STEP]
    assert selected == expected
    assert selected  # non-trivial partition
    assert all(name.startswith('step.') for name in selected)
