# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Answer a product question only from indexed passages, then audit grounding.

What you will see (sample run):
  === protocol ===
  Asker -> Librarian : Question(str)
  Librarian -> Index : Lookup(str)
  Index -> Librarian {
    Passages([str]):
      Librarian -> Auditor : Answer(str)
      ...
    Nothing(str):
      ...
  }
  === conversation ===
  Asker:Question -> Librarian 'How long is the battery life?'
  Librarian:Lookup -> Index 'battery'
  Index:Passages -> Librarian ['[p1] The headset ships with a 2-hour battery...', ...]
  Librarian:Answer -> Auditor 'Battery lasts about two hours under mixed use [p1].'
  Auditor:Sound -> Librarian None
  Librarian:Answer -> Asker 'Battery lasts about two hours under mixed use [p1].'
  replay: N envelopes, 0 index calls

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/retrieval_qa.py
"""

from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    RawValue,
    SessionType,
    project_all,
)

Asker, Librarian, Index, Auditor = pa.roles('Asker', 'Librarian', 'Index', 'Auditor')

PASSAGES = pa.Text.many(1, 5)
GROUNDED = pa.Text.where(
    'cites at least one passage as [p1]',
    lambda s: any(f'[p{n}]' in s for n in range(1, 6)),
)

NO_ANSWER = 'Why the question cannot be answered from the index.'


Nothing = pa.Text('Nothing', 'Why the query matched no passage.')
Lookup = pa.Text('Lookup', 'A search query for the index.')
Passages = PASSAGES('Passages', 'Passages that match the query.')
Question = pa.Text('Question', 'What the reader wants to know.')
NoAnswer = pa.Text('No answer', NO_ANSWER)
Answer = GROUNDED('Answer', 'An answer citing the passages.')
Noted = pa.Nothing('Noted', 'Auditor acknowledgement.')
Sound = pa.Nothing('Sound', 'The answer is supported by the passages.')
Unsupported = pa.Text('Unsupported', 'Which claim the passages do not support.')
Blocked = pa.Text('Blocked', 'Why no answer will be attempted.')


@pa.choreography
def retrieval_qa(c: pa.Chor) -> None:
    c.say(Asker, Librarian, Question)
    c.say(Librarian, Index, Lookup)
    with c.decide(Index, Librarian) as found:
        with found.case(Passages):
            c.say(Librarian, Auditor, Answer)
            with c.decide(Auditor, Librarian) as audit:
                with audit.case(Sound):
                    c.say(Librarian, Asker, Answer)
                with audit.case(Unsupported):
                    c.say(Librarian, Asker, NoAnswer)
        with found.case(Nothing):
            c.say(Librarian, Auditor, Blocked)
            c.say(Auditor, Librarian, Noted)
            c.say(Librarian, Asker, NoAnswer)


protocol = retrieval_qa()

MANUAL: tuple[str, ...] = (
    '[p1] The headset ships with a 2-hour battery under mixed use.',
    '[p2] Guardian sets a virtual boundary you walk inside.',
    '[p3] Cast mirrors the headset view to a phone on the same Wi-Fi.',
    '[p4] Hand tracking works without controllers in supported apps.',
)


def _index_tools(calls: list[str]) -> list[Any]:
    async def lookup(query: str) -> pa.Choice:
        calls.append(query)
        words = query.lower().split()
        hits = [
            passage
            for passage in MANUAL
            if any(word in passage.lower() for word in words if len(word) > 2)
        ]
        if hits:
            passages: list[RawValue] = list(hits[:5])
            return pa.reply(Passages, passages)
        return pa.reply(Nothing, f'no passage matched {query!r}')

    return [pa.tool_for(Lookup, lookup)]


def build(
    *,
    index_calls: list[str] | None = None,
) -> tuple[SessionType, list[pa.Participant], list[str]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    strict = pa.Repair(attempts=2)
    if index_calls is None:
        index_calls = []
    librarian = pa.Agent(
        model,
        Librarian,
        (
            'Lookup a short search query. '
            'When passages arrive, Answer must cite at least one as [p1]..[p5] '
            "in the text (example: '... two hours [p1].'). "
            'After Sound, send the same grounded Answer to the Asker. '
            'On Unsupported or Nothing, send No answer explaining why.'
        ),
        protocol,
        repair=strict,
    )
    auditor = pa.Agent(
        model,
        Auditor,
        (
            'Choose Sound only if every claim is supported by a cited passage; '
            'otherwise Unsupported with a short reason.'
        ),
        protocol,
    )
    asker = pa.Human(
        Asker,
        protocol,
        pa.ScriptedHumanIo([pa.says(Question, 'How long is the battery life?')]),
    )
    participants: list[pa.Participant] = [
        asker,
        librarian,
        auditor,
        pa.Toolbox(Index, protocol, _index_tools(index_calls)),
    ]
    return protocol, participants, index_calls


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)

    journal = pa.MemoryJournal()
    _, participants, _ = build()
    runtime = pa.AgentRuntime(protocol, participants, journal=journal)
    report.conversation(runtime.run_sync())

    # Replay spends no index calls: decisions are journalled.
    replay_calls: list[str] = []
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    replay_runtime = pa.AgentRuntime(
        protocol,
        [
            pa.Human(Asker, protocol, pa.ScriptedHumanIo([])),
            pa.Agent(model, Librarian, 'replay', protocol),
            pa.Agent(model, Auditor, 'replay', protocol),
            pa.Toolbox(Index, protocol, _index_tools(replay_calls)),
        ],
        journal=pa.MemoryJournal(journal.script().decisions),
    )
    replayed = replay_runtime.run_sync()
    report.note(
        f'replay: {len(replayed)} envelopes, {len(replay_calls)} index calls',
        title='replay',
    )


if __name__ == '__main__':
    main()
