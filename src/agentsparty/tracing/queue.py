"""Queue sink and the watch over a running session."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Generator
from contextlib import asynccontextmanager, suppress
from typing import Generic, TypeVar

from agentsparty.tracing.facet import Facet
from agentsparty.tracing.types import Event

__all__ = ['QueueTracer', 'Watch', 'watching']

R = TypeVar('R')


class QueueTracer:
    """Tracer that publishes events to an unbounded queue for a consumer.

    The counterpart of the industry's ``agent.iter()`` and ``streamevents``.
    It observes only. agentsparty offers no hook that edits a step before it runs,
    because the protocol routes the session: a consumer that could rewrite a
    node would be routing it, and the whole point of a choreography is that it
    was decided before anyone was asked.
    """

    def __init__(self) -> None:
        """Create a sink with an empty queue."""
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    def record(self, event: Event) -> None:
        """Publish *event*.

        The queue is unbounded, so this never blocks and never raises, as the
        ``Tracer`` contract requires.

        Args:
            event: The event to publish.
        """
        self._queue.put_nowait(event)

    async def take(self) -> Event:
        """The next published event, waiting for one if the queue is empty."""
        return await self._queue.get()

    def pending(self) -> int:
        """How many published events have not been taken yet."""
        return self._queue.qsize()


async def _next_event(task: asyncio.Task[object], tracer: QueueTracer) -> Event | None:
    """Wait for either an event or the session task to finish.

    Returns:
        The next event, or ``None`` when the session is done and the queue
        is empty.
    """
    if tracer.pending() > 0:
        return await tracer.take()
    if task.done():
        return None
    take_task = asyncio.create_task(tracer.take())
    done, _pending = await asyncio.wait(
        {task, take_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    if take_task in done:
        return take_task.result()
    take_task.cancel()
    await asyncio.gather(take_task, return_exceptions=True)
    if tracer.pending() > 0:
        return await tracer.take()
    return None


class Watch(Generic[R]):
    """A session being watched: events while it runs, and what it returned.

    Two ways to read one run, and they do not compete:

    - ``async for event in watch`` — every recorded event as it arrives;
    - ``await watch`` — what the session returned.

    Awaiting before iterating is **not** an error. ``QueueTracer`` is
    unbounded and ``Tracer.record`` never blocks, so a session never waits for
    its audience: awaiting first means you watch a recording instead of a
    broadcast, and no event is lost. This is why agentsparty has no "result read too
    early" failure and no ``is_completed`` flag.

    One consumer per watch. Two iterators over the same watch would split the
    events between them, because a queue hands each event to exactly one
    taker; to feed two consumers, ``fanout`` two ``QueueTracer``s.

    Construct one with :func:`watching`, which also stops it. Constructing a
    ``Watch`` directly starts the session with nobody responsible for
    cancelling it.
    """

    def __init__(self, session: Awaitable[R], tracer: QueueTracer) -> None:
        """Run *session* as a task and read what it records into *tracer*.

        Args:
            session: The awaitable to watch — usually ``runtime.run()``.
            tracer: The sink *session* was built with.
        """
        self._task = asyncio.ensure_future(session)
        self._tracer = tracer

    def __await__(self) -> Generator[object, None, R]:
        """Wait for the session and return what it returned.

        Raises:
            Exception: whatever the session raised.
        """
        return self._task.__await__()

    def __aiter__(self) -> AsyncIterator[Event]:
        """Every recorded event, in recording order, while the session runs."""
        return self._recorded()

    def select(self, facet: Facet) -> AsyncIterator[Event]:
        """Only the events *facet* watches, in the order they were recorded.

        This one method is the industry's five channel projections plus
        ``interleave([...])``: the latter is ``select(a | b)``. Because a
        facet is a set, ``select(~MODEL)`` — "everything but the model
        chatter" — is expressible too, which no surveyed framework offers.

        Args:
            facet: The side of the session to watch.
        """
        return (event async for event in self if event.signal in facet)

    async def _recorded(self) -> AsyncIterator[Event]:
        """Drain the queue until the session ends, then surface its failure.

        The failure is raised *after* the drain so a consumer sees everything
        that happened before it, including the ``Failed`` signal the scope
        recorded.
        """
        while True:
            event = await _next_event(self._task, self._tracer)
            if event is None:
                break
            yield event
        await self._task

    async def _stop(self) -> None:
        """Cancel a session that is still running; leave a finished one alone.

        Called by :func:`watching` on the way out of its block, and nowhere
        else: cancellation is the boundary of a scope, not a method a consumer
        calls.
        """
        if self._task.done():
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task


@asynccontextmanager
async def watching(
    session: Awaitable[R],
    tracer: QueueTracer,
) -> AsyncIterator[Watch[R]]:
    """Watch *session* for the length of the block, stopping it on the way out.

    Leaving the block early — a ``break``, a client that disconnected, an
    exception — cancels a session that is still running, so no task outlives
    the block that started it and no provider call is left paying for output
    nobody reads. A session that already finished is left alone: there is
    nothing to cancel and ``await watch`` still gives its result.

    Args:
        session: The awaitable to watch — usually ``runtime.run()``.
        tracer: The sink *session* was built with.

    Yields:
        The watch over *session*.
    """
    watch = Watch(session, tracer)
    try:
        yield watch
    finally:
        await watch._stop()
