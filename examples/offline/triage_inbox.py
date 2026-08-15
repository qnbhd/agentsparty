# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Inbox triage as guarded recursion with a journalled verdict.

A polling loop is rec/var bounded by Allowance. The mailbox owns its seen set.
The triage verdict (Discard vs Save) is a Decision in the journal.

What you will see (exact):
  === protocol ===
  rec inbox { Owner -> Triage : Check() ... }
  === duties ===
  ...
  === session ===
  Owner:Check -> Triage
  Triage:Fetch -> Mailbox
  Mailbox:Thread -> Triage {...}
  ...
  === skeleton ===
  Owner:Check  Triage:Fetch  Mailbox:Thread  ...
  === replay ===
  N envelopes, 0 model calls, 0 tool calls
  === recursion limit ===
  RecursionLimitError ...

Offline: deterministic double, no API key.

Run::

    uv run python examples/offline/triage_inbox.py
"""

from __future__ import annotations

import json
from contextlib import suppress
from typing import Any

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
    rec,
    var,
)

Owner, Triage, Responder, Mailbox = ap.roles('Owner', 'Triage', 'Responder', 'Mailbox')

THREAD = ap.Text.mapping().having('id', 'sender', 'snippet')
DRAFT = ap.Text.mapping().having('to', 'subject', 'body')

NOTED = 'What the mailbox recorded.'
REPORT = 'Report on this cycle.'


INBOX: tuple[dict[str, str], ...] = (
    {
        'id': 'e1',
        'sender': 'newsletter@example.com',
        'snippet': 'weekly digest',
    },
    {
        'id': 'e2',
        'sender': 'boss@example.com',
        'snippet': 'need the report',
    },
)


Check = ap.Nothing('Check', 'Run one polling cycle.')
Fetch = ap.Nothing('Fetch', 'Ask for the next unseen thread.')
Empty = ap.Nothing('Empty', 'No unseen thread is left.')
Rest = ap.Nothing('Rest', 'Nothing arrived this cycle.')
# Same label "Idle", two payloads: mailbox ack (nothing) vs owner report (text).
IdleAck = ap.Nothing('Idle', 'Acknowledge an empty cycle.')
IdleReport = ap.Text('Idle', REPORT)
Noted = ap.Text('Noted', NOTED)
Quiet = ap.Text('Quiet', 'Report on an empty cycle.')
Thread = THREAD('Thread', 'The next unseen thread.')
Handle = THREAD('Handle', 'The thread to deal with.')
Discard = ap.Text('Discard', 'Thread id and why it needs no reply.')
Ignored = ap.Text('Ignored', 'Why nothing was written.')
Nothing = ap.Text('Nothing', REPORT)
Save = DRAFT('Save', 'The draft to store for the owner.')
Stored = ap.Text('Stored', 'Where the draft was stored.')
Drafted = ap.Text('Drafted', 'What was written.')
Draft = ap.Text('Draft', REPORT)

protocol = rec(
    'inbox',
    msg[Owner, Triage](Check)
    >> msg[Triage, Mailbox](Fetch)
    >> alt[Mailbox, Triage](
        Empty
        >> msg[Triage, Responder](Rest)
        >> alt[Responder, Mailbox](IdleAck)
        >> msg[Mailbox, Responder](Noted)
        >> msg[Responder, Triage](Quiet)
        >> msg[Triage, Owner](IdleReport)
        >> var('inbox'),
        Thread
        >> msg[Triage, Responder](Handle)
        >> alt[Responder, Mailbox](
            Discard
            >> msg[Mailbox, Responder](Noted)
            >> msg[Responder, Triage](Ignored)
            >> msg[Triage, Owner](Nothing)
            >> var('inbox'),
            Save
            >> msg[Mailbox, Responder](Stored)
            >> msg[Responder, Triage](Drafted)
            >> msg[Triage, Owner](Draft)
            >> var('inbox'),
        ),
    ),
).close()


def _answer(label: str, payload: object = None) -> str:
    return json.dumps({'alt': {'label': label, 'payload': payload}})


def _mailbox_tools() -> list[Any]:
    seen: set[str] = set()
    queue = list(INBOX)

    async def fetch(_empty: None) -> ap.Choice:
        remaining = [item for item in queue if item['id'] not in seen]
        if not remaining:
            return ap.reply(Empty, None)
        thread = remaining[0]
        seen.add(thread['id'])
        return ap.reply(Thread, dict(thread))

    async def idle(_empty: None) -> ap.Choice:
        return ap.reply(Noted, 'idle cycle recorded')

    async def discard(reason: str) -> ap.Choice:
        return ap.reply(Noted, f'discarded: {reason}')

    async def save(draft: dict[str, str]) -> ap.Choice:
        return ap.reply(Stored, f'draft for {draft["to"]}')

    return [
        ap.tool_for(Fetch, fetch),
        ap.tool_for(IdleAck, idle),
        ap.tool_for(Discard, discard),
        ap.tool_for(Save, save),
    ]


# deterministic double: scripted model answers
def _default_triage_answers() -> list[str]:
    return [
        _answer('Fetch', None),
        _answer('Handle', dict(INBOX[0])),
        _answer('Nothing', 'ignored newsletter'),
        _answer('Fetch', None),
        _answer('Handle', dict(INBOX[1])),
        _answer('Draft', 'draft ready for boss'),
        _answer('Fetch', None),
        _answer('Rest', None),
        _answer('Idle', 'mailbox empty'),
    ]


def _default_responder_answers() -> list[str]:
    return [
        _answer('Discard', 'e1 is a newsletter'),
        _answer('Ignored', 'no reply needed'),
        _answer(
            'Save',
            {
                'to': 'boss@example.com',
                'subject': 'Re: report',
                'body': 'attached',
            },
        ),
        _answer('Drafted', 'saved a reply draft'),
        _answer('Idle', None),
        _answer('Quiet', 'nothing new'),
    ]


def build(
    *,
    owner_checks: int = 3,
    triage_answers: list[str] | None = None,
    responder_answers: list[str] | None = None,
    journal: ap.MemoryJournal | None = None,
) -> tuple[SessionType, list[ap.Participant], ap.ScriptedHumanIo]:
    # Three cycles: Discard → Save → Empty. Count outbound agent steps on path.
    if triage_answers is None:
        triage_answers = _default_triage_answers()
    if responder_answers is None:
        responder_answers = _default_responder_answers()
    owner_io = ap.ScriptedHumanIo([ap.says(Check, None) for _ in range(owner_checks)])
    participants: list[ap.Participant] = [
        ap.Human(Owner, protocol, owner_io),
        ap.Agent(
            ap.ScriptedLanguageModel(triage_answers),
            Triage,
            'Triage the inbox one cycle at a time.',
            protocol,
        ),
        ap.Agent(
            ap.ScriptedLanguageModel(responder_answers),
            Responder,
            'Discard or draft for each thread.',
            protocol,
        ),
        ap.Toolbox(Mailbox, protocol, _mailbox_tools()),
    ]
    return protocol, participants, owner_io


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)
    report.duties(protocol)

    journal = ap.MemoryJournal()
    _, participants, _owner_io = build(journal=journal)
    # Three live unfoldings complete Discard → Save → Empty; the next var
    # charges a fourth and raises — every branch ends in var by design.
    runtime = ap.AgentRuntime(
        protocol,
        participants,
        journal=journal,
        allowance=ap.Allowance(unfoldings=3),
    )
    with suppress(ap.RecursionLimitError):
        runtime.run_sync()
    trace = list(runtime.trace)
    report.conversation(trace, title='session')
    report.skeleton(trace)

    # Replay journalled decisions; empty scripts; tools are not called again.
    _, replay_parts, _ = build(
        triage_answers=[],
        responder_answers=[],
        owner_checks=0,
    )
    replay_rt = ap.AgentRuntime(
        protocol,
        replay_parts,
        journal=ap.MemoryJournal(journal.script().decisions),
        allowance=ap.Allowance(unfoldings=3),
    )
    with suppress(ap.RecursionLimitError, ap.SelectionError):
        replay_rt.run_sync()
    replayed = list(replay_rt.trace)
    report.note(f'{len(replayed)} envelopes, 0 model calls, 0 tool calls', title='replay')

    # Tight allowance: one unfolding only.
    _, tight_parts, owner_io = build(owner_checks=3)
    tight_rt = ap.AgentRuntime(
        protocol,
        tight_parts,
        allowance=ap.Allowance(unfoldings=1),
    )
    try:
        tight_rt.run_sync()
    except ap.RecursionLimitError as exc:
        report.note(
            f'{type(exc).__name__} {exc}',
            f'owner cancellations: {len(owner_io.cancellations)}',
            title='recursion limit',
        )


if __name__ == '__main__':
    main()
