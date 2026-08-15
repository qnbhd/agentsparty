# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]", "fastapi", "uvicorn", "pydantic"]
# ///
"""Durable FastAPI support triage: one ticket, one protocol session.

This loopback demo has no authentication. Bind it to 127.0.0.1 only
and do not expose it publicly without access control.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from desk import QueueDesk
from fastapi import FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import RedirectResponse
from openai import AsyncOpenAI
from protocol import CATEGORIES, OUTCOMES, build_participants, protocol
from pydantic import BaseModel, Field

import agentsparty as ap
from agentsparty._utils.assertions import post, pre  # noqa: PLC2701
from agentsparty.journal.sqlite import SqliteJournal
from agentsparty.journal.types import Decision, SessionId
from agentsparty.participant import Envelope

MODEL = 'gpt-5.6-luna'
TOKEN_LIMIT = 40_000
ALLOWANCE = ap.Allowance(steps=32, unfoldings=4)
HERE = Path(__file__).resolve().parent


class TicketIn(BaseModel):
    """Ticket data accepted at the HTTP boundary."""

    text: str = Field(min_length=1, max_length=8_000)
    customer_tier: Literal['free', 'standard', 'pro', 'enterprise'] = 'standard'


class TicketCreated(BaseModel):
    """Stable handle returned before background processing finishes."""

    ticket_id: str


class DecisionIn(BaseModel):
    """A human choice offered by the Approver role."""

    label: Literal['Ship', 'Escalate']
    note: str = Field(default='', max_length=2_000)


class TraceItem(BaseModel):
    """One decoded protocol interaction."""

    sender: str
    receiver: str
    label: str
    payload: Any = None


class TicketView(BaseModel):
    """Observable state of a live or journalled ticket."""

    ticket_id: str
    status: Literal['running', 'waiting_approval', 'interrupted', 'done', 'failed']
    category: str | None = None
    severity: int | None = None
    draft: dict[str, Any] | None = None
    outcome: str | None = None
    offered: list[str] = Field(default_factory=list)
    error: str | None = None
    trace: list[TraceItem] = Field(default_factory=list)


@dataclass
class Ticket:
    """In-memory worker state; durable decisions live in SQLite."""

    ticket_id: str
    incoming: TicketIn
    desk: QueueDesk
    runtime: ap.AgentRuntime
    task: asyncio.Task[None] | None = None
    error: str | None = None


def _db_path() -> Path:
    """Resolve the journal path once per application lifespan."""
    return Path(os.environ.get('TRIAGE_DB', HERE / 'tickets.db'))


def _model(client: AsyncOpenAI) -> ap.LanguageModel:
    """Build the real, retried and token-metered model stack."""
    model = ap.Retrying(ap.OpenAIModel(MODEL, client), attempts=2)
    return ap.traced(ap.Metered(model, tokens=TOKEN_LIMIT))


def _journal(ticket_id: str) -> SqliteJournal:
    """Open the durable journal for exactly one ticket id."""
    pre(expr=bool(ticket_id), message='ticket id must not be blank')
    return SqliteJournal(app.state.db, protocol, SessionId(ticket_id))


def _named(trace: list[Envelope], names: frozenset[str]) -> Envelope | None:
    """Return the latest envelope whose label belongs to *names*."""
    return next((item for item in reversed(trace) if str(item.label) in names), None)


def _live_status(
    ticket: Ticket,
) -> Literal['running', 'waiting_approval', 'done', 'failed']:
    """Derive status from the worker without changing it."""
    if ticket.error is not None:
        return 'failed'
    if ticket.task is not None and ticket.task.done():
        return 'done'
    if ticket.desk.waiting:
        return 'waiting_approval'
    return 'running'


def _live_view(ticket: Ticket) -> TicketView:
    """Project a running session into the public response model."""
    trace = ticket.runtime.trace
    category = _named(trace, CATEGORIES)
    draft = _named(trace, frozenset({'Draft'}))
    outcome = _named(trace, OUTCOMES)
    return TicketView(
        ticket_id=ticket.ticket_id,
        status=_live_status(ticket),
        category=None if category is None else str(category.label),
        severity=category.payload if category and isinstance(category.payload, int) else None,
        draft=draft.payload if draft and isinstance(draft.payload, dict) else None,
        outcome=None if outcome is None else str(outcome.label),
        offered=list(ticket.desk.offered),
        error=ticket.error,
        trace=[
            TraceItem(
                sender=item.sender.name,
                receiver=item.receiver.name,
                label=str(item.label),
                payload=jsonable_encoder(item.payload),
            )
            for item in trace
        ],
    )


def _decision_item(decision: Decision) -> TraceItem:
    """Expose a journal decision without invoking a participant or model."""
    return TraceItem(
        sender=decision.sender.name,
        receiver=decision.receiver.name,
        label=str(decision.label),
        payload=jsonable_encoder(decision.raw),
    )


def _journal_view(ticket_id: str) -> TicketView | None:
    """Read a ticket after restart directly from its durable decisions."""
    decisions = list(_journal(ticket_id).script().decisions)
    if not decisions:
        return None
    by_label = {str(item.label): item.raw for item in decisions}
    category = next((name for name in CATEGORIES if name in by_label), None)
    outcome = next((name for name in OUTCOMES if name in by_label), None)
    severity = by_label.get(category) if category else None
    draft = by_label.get('Draft')
    return TicketView(
        ticket_id=ticket_id,
        status='done' if outcome else 'interrupted',
        category=category,
        severity=severity if isinstance(severity, int) else None,
        draft=draft if isinstance(draft, dict) else None,
        outcome=outcome,
        trace=[_decision_item(item) for item in decisions],
    )


async def _drive(ticket: Ticket) -> None:
    """Run a worker and retain failures for status polling."""
    try:
        await ticket.runtime.run()
    except Exception as error:  # The API exposes failure and allows explicit resume.
        ticket.error = f'{type(error).__name__}: {error}'


def _start_ticket(incoming: TicketIn, ticket_id: str) -> Ticket:
    """Construct and start one journalled protocol session."""
    pre(expr=bool(ticket_id), message='ticket id must not be blank')
    desk = QueueDesk()
    runtime = ap.AgentRuntime(
        protocol,
        build_participants(
            _model(app.state.client),
            {
                'text': incoming.text,
                'customer_tier': incoming.customer_tier,
            },
            desk,
        ),
        allowance=ALLOWANCE,
        journal=_journal(ticket_id),
    )
    ticket = Ticket(ticket_id, incoming, desk, runtime)
    ticket.task = asyncio.create_task(_drive(ticket))
    post(expr=ticket.task is not None, message='the ticket worker must be created')
    return ticket


def _incoming_from_journal(ticket_id: str) -> TicketIn | None:
    """Recover the original typed request from the first recorded payload."""
    script = _journal(ticket_id).script()
    if script.length == 0:
        return None
    raw = script.decisions[0].raw
    if not isinstance(raw, dict):
        return None
    return TicketIn.model_validate(raw)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Own the API client, SQLite connection and live worker registry."""
    with closing(sqlite3.connect(_db_path(), check_same_thread=False)) as database:
        async with AsyncOpenAI(
            api_key=os.environ['OPENAI_API_KEY'],
            max_retries=0,
            timeout=30.0,
        ) as client:
            application.state.client = client
            application.state.db = database
            application.state.db.execute('PRAGMA journal_mode=WAL')
            application.state.tickets = {}
            yield


app = FastAPI(
    title='Support Triage API',
    summary=(
        'Loopback demo with no authentication. Do not expose publicly without access control.'
    ),
    lifespan=lifespan,
)


@app.get('/', include_in_schema=False)
def home() -> RedirectResponse:
    """Keep the example focused: its useful interface is the OpenAPI contract."""
    return RedirectResponse('/docs')


@app.post('/tickets', status_code=status.HTTP_202_ACCEPTED)
async def open_ticket(incoming: TicketIn) -> TicketCreated:
    """Accept a ticket and start its durable session in the background."""
    ticket_id = uuid4().hex[:12]
    app.state.tickets[ticket_id] = _start_ticket(incoming, ticket_id)
    await asyncio.sleep(0)
    return TicketCreated(ticket_id=ticket_id)


@app.get('/tickets/{ticket_id}')
def read_ticket(ticket_id: str) -> TicketView:
    """Return live state, or reconstruct it from SQLite after a restart."""
    live = app.state.tickets.get(ticket_id)
    if live is not None:
        return _live_view(live)
    stored = _journal_view(ticket_id)
    if stored is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f'unknown ticket {ticket_id}')
    return stored


@app.post('/tickets/{ticket_id}/decision')
def decide(ticket_id: str, incoming: DecisionIn) -> TicketView:
    """Submit a human decision only while the protocol offers it."""
    ticket = app.state.tickets.get(ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_409_CONFLICT, 'resume this ticket before deciding')
    payload = None if incoming.label == 'Ship' else incoming.note.strip() or 'needs a person'
    if not ticket.desk.submit(incoming.label, payload):
        raise HTTPException(status.HTTP_409_CONFLICT, 'that decision is not currently offered')
    return _live_view(ticket)


@app.post('/tickets/{ticket_id}/resume', status_code=status.HTTP_202_ACCEPTED)
async def resume_ticket(ticket_id: str) -> TicketCreated:
    """Replay recorded decisions and continue only the unfinished work."""
    existing = app.state.tickets.get(ticket_id)
    if existing is not None and existing.task is not None and not existing.task.done():
        raise HTTPException(status.HTTP_409_CONFLICT, 'session is still running')
    incoming = existing.incoming if existing else _incoming_from_journal(ticket_id)
    if incoming is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f'unknown ticket {ticket_id}')
    app.state.tickets[ticket_id] = _start_ticket(incoming, ticket_id)
    await asyncio.sleep(0)
    return TicketCreated(ticket_id=ticket_id)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host='127.0.0.1',
        port=int(os.environ.get('PORT', '8765')),
        reload=False,
    )
