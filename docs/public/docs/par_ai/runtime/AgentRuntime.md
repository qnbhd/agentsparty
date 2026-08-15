# AgentRuntime (/docs/agentsparty/runtime/AgentRuntime)

Bind roles to peer participants and drive the global protocol.

## Attributes

<PyAttribute name={"proto"} type={"GlobalType"} value={null}>

The choreography this runtime executes.

</PyAttribute>

<PyAttribute name={"participants"} type={"tuple[Participant, ...]"} value={null}>

The participants bound to the protocol roles, in binding order.

</PyAttribute>

<PyAttribute name={"allowance"} type={"Allowance"} value={null}>

What one `run` may spend.

</PyAttribute>

<PyAttribute name={"tracer"} type={"Tracer"} value={null}>

The observability sink for this session.

</PyAttribute>

<PyAttribute name={"journal"} type={"Journal"} value={null}>

The durable record of the alts made.

</PyAttribute>

<PyAttribute name={"trace"} type={"list[Envelope]"} value={null}>

Delivered envelopes in canonical order: root track, then branches.

A linear extension of the causal order, chosen so that the value does
not depend on how the scheduler interleaved independent branches. The
wall-clock order is in the tracer, not here.

</PyAttribute>

## Functions

<PyFunction name={"__init__"} type={"(self, proto, participants, *, allowance=DEFAULT_ALLOWANCE, tracer=NULL_TRACER, journal=NULL_JOURNAL) -> None"}>

Bind *participants* to the roles required by *proto*.

<PySourceCode >

```python
def __init__(
    self,
    proto: SessionType | Fragment[SessionType],
    participants: Sequence[Participant],
    *,
    allowance: Allowance = DEFAULT_ALLOWANCE,
    tracer: Tracer = NULL_TRACER,
    journal: Journal = NULL_JOURNAL,
) -> None:
    """Bind *participants* to the roles required by *proto*.

    Args:
        proto: The choreography to execute. A still-open
            :class:`~agentsparty.protocol.language.core.Fragment` is closed at this
            boundary. Must be guarded (validated via
            :func:`agentsparty.protocol.assert_wellformed`).
        participants: One participant per role. Missing, duplicate or
            extra roles raise :exc:`ValueError`.
        allowance: What one :meth:`run` may spend in unfoldings and
            protocol steps. Replayed decisions from a journal do not
            consume the allowance. Defaults to
            :data:`~agentsparty.kernel.budget.DEFAULT_ALLOWANCE`.
        tracer: Observability sink for the session; defaults to a no-op.
        journal: Durable record of the alts made. Decisions already in
            it are replayed instead of being asked again; new ones are
            appended before they are delivered. Defaults to
            ``NULL_JOURNAL``, which records nothing and replays nothing.

    Raises:
        ValueError: if the protocol is ill-formed or the participants do
            not match the protocol roles.
        RecursionLimitError: if a :meth:`run` exhausts the unfolding
            allowance before the protocol reaches ``end``.
        StepLimitError: if a :meth:`run` exhausts the step allowance.
    """
    closed = ensure_session(proto)
    assert_wellformed(closed)
    self._proto = as_global(closed)
    self._participants = tuple(participants)
    self._allowance = allowance
    self._tracer = tracer
    self._journal = journal
    self._delivered: dict[Track, list[Envelope]] = {}
    self._by_role = _bind_participants(closed, self._participants)
```

</PySourceCode>

<div >

<PyParameter name={"proto"} type={"SessionType | Fragment[SessionType]"} value={undefined}>

The choreography to execute. A still-open
[`Fragment`](/docs/agentsparty/protocol/language/core/Fragment) is closed at this
boundary. Must be guarded (validated via
[`assert_wellformed`](/docs/agentsparty/protocol)).

</PyParameter>
<PyParameter name={"participants"} type={"Sequence[Participant]"} value={undefined}>

One participant per role. Missing, duplicate or
extra roles raise `ValueError`.

</PyParameter>
<PyParameter name={"allowance"} type={"Allowance"} value={"DEFAULT_ALLOWANCE"}>

What one `run` may spend in unfoldings and
protocol steps. Replayed decisions from a journal do not
consume the allowance. Defaults to
[`DEFAULT_ALLOWANCE`](/docs/agentsparty/kernel/budget).

</PyParameter>
<PyParameter name={"tracer"} type={"Tracer"} value={"NULL_TRACER"}>

Observability sink for the session; defaults to a no-op.

</PyParameter>
<PyParameter name={"journal"} type={"Journal"} value={"NULL_JOURNAL"}>

Durable record of the alts made. Decisions already in
it are replayed instead of being asked again; new ones are
appended before they are delivered. Defaults to
``NULL_JOURNAL``, which records nothing and replays nothing.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"run"} type={"(self) -> list[Envelope]"}>

Execute the protocol and return the trace of delivered envelopes.

Decisions already in the journal are replayed: the participant that
made them is reminded via ``recall`` and no model is called. Everything
after the journal's last step is asked live and recorded as it is made,
so an interrupted session resumes by calling ``run()`` again.

A session that ends anywhere other than ``end`` is rolled up: every
bound participant is told once via ``cancel``, ``SessionCancelled`` is
recorded, and the failure is re-raised unchanged. ``KeyboardInterrupt``
and task cancellation are ``BaseException`` and deliberately not
caught.

<PySourceCode >

```python
async def run(self) -> list[Envelope]:
    """Execute the protocol and return the trace of delivered envelopes.

    Decisions already in the journal are replayed: the participant that
    made them is reminded via ``recall`` and no model is called. Everything
    after the journal's last step is asked live and recorded as it is made,
    so an interrupted session resumes by calling ``run()`` again.

    A session that ends anywhere other than ``end`` is rolled up: every
    bound participant is told once via ``cancel``, ``SessionCancelled`` is
    recorded, and the failure is re-raised unchanged. ``KeyboardInterrupt``
    and task cancellation are ``BaseException`` and deliberately not
    caught.

    Returns:
        One envelope per delivered message, in delivery order.
    """
    self._delivered.clear()
    script = self._journal.script()
    with new_scope(self._tracer).open(
        SessionStarted(
            self._proto,
            tuple(participants(self._proto)),
        ),
    ) as session:
        try:
            await self._step(
                self._proto,
                ROOT_TRACK,
                NOTHING_SPENT,
                session,
                script,
            )
        except Exception as error:
            # cancellation is choreography, not the caller's business:
            await self._cancel(Cancelled.of(error), session)
            raise
        if len(self.trace) < script.length:
            raise JournalError(
                f'journal records {script.length} decisions but the '
                f'protocol delivered only {len(self.trace)} envelopes',
            )
        session.record(SessionFinished(len(self.trace)))
    return list(self.trace)
```

</PySourceCode>

<PyFunctionReturn type={"list"}>

One envelope per delivered message, in delivery order.

</PyFunctionReturn>

</PyFunction>

<PyFunction name={"run_sync"} type={"(self) -> list[Envelope]"}>

Run the protocol on a fresh event loop and return the delivery trace.

Thin wrapper over `run` via `run`. Do not call
from a thread that already has a running event loop — use ``await
runtime.run()`` there instead.

<PySourceCode >

```python
def run_sync(self) -> list[Envelope]:
    """Run the protocol on a fresh event loop and return the delivery trace.

    Thin wrapper over :meth:`run` via :func:`asyncio.run`. Do not call
    from a thread that already has a running event loop — use ``await
    runtime.run()`` there instead.

    Returns:
        One envelope per delivered message, in delivery order.
    """
    # pre: no running loop in this thread (asyncio.run enforces it).
    return asyncio.run(self.run())
```

</PySourceCode>

<PyFunctionReturn type={"list"}>

One envelope per delivered message, in delivery order.

</PyFunctionReturn>

</PyFunction>
