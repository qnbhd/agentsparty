"""Tool as a role with a protocol surface; replay skips the paid tool call.

Planner is an Agent (scripted double); Tools is a Toolbox. On replay the
tool is not run again — decisions come from the journal.

What you will see (exact):
  === protocol ===
  User -> Planner : ask(str)
  Planner -> Tools {
    search(str):
      Tools -> Planner {
        hits(list[str]):
          Planner -> User : answer(str)
          end
        offline(str):
          Planner -> User : answer(str)
          end
      }
  }
  === conversation ===
  User -> Planner : ask('mpst')
  Planner -> Tools : search('mpst')
  Tools -> Planner : hits([...])
  Planner -> User : answer('1 source(s) found')
  replaying — the tool is not run again
  4 envelopes, 0 tool calls

Offline: deterministic double, no API key.

Run::

    uv run python examples/offline/toolbox.py
"""

from __future__ import annotations

import json

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    RawValue,
    alt,
    msg,
    seq,
)

User, Planner, Tools = pa.roles('User', 'Planner', 'Tools')


Hits = pa.Text.many()('hits')
Offline = pa.Text('offline')
Ask = pa.Text('ask')
Answer = pa.Text('answer')
Search = pa.Text('search')

protocol = seq(
    msg[User, Planner](Ask),
    alt[Planner, Tools](
        Search >> alt[Tools, Planner](Hits, Offline) >> msg[Planner, User](Answer),
    ),
).close()

INDEX: dict[str, RawValue] = {
    'mpst': ['Honda et al., Multiparty Asynchronous Session Types'],
}


async def search(query: str) -> pa.Choice:
    """Answer a search request out of a tiny in-memory index."""
    hits = INDEX.get(query)
    if hits is None:
        return pa.reply(Offline, f'nothing indexed for {query!r}')
    return pa.reply(Hits, hits)


def _planner(answers: list[str]) -> pa.Agent:
    return pa.Agent(
        pa.ScriptedLanguageModel(answers),
        Planner,
        'Search then answer the user.',
        protocol,
    )


def main() -> None:
    """Run the choreography live, then replay it from its own journal."""
    report = debug.Report()
    report.protocol(protocol)
    journal = pa.MemoryJournal()
    # deterministic double: scripted model answers
    planner_script = [
        json.dumps({'alt': {'label': 'search', 'payload': 'mpst'}}),
        json.dumps({'alt': {'label': 'answer', 'payload': '1 source(s) found'}}),
    ]
    cast = (
        pa
        .Cast(protocol)
        .play(User, pa.human(pa.script(pa.says(Ask, 'mpst'))))
        .play(
            Planner,
            pa.agent(pa.ScriptedLanguageModel(planner_script), 'Search then answer.'),
        )
        .play(Tools, pa.service(pa.tool_for(Search, search)))
    )
    runtime = cast.runtime(journal=journal)
    report.conversation(runtime.run_sync())
    report.note('replaying — the tool is not run again', title='replay')
    replayed = pa.AgentRuntime(
        protocol,
        [
            pa.Human(User, protocol, pa.ScriptedHumanIo([])),
            _planner([]),
            pa.Toolbox(Tools, protocol, [pa.tool_for(Search, search)]),
        ],
        journal=pa.MemoryJournal(journal.script().decisions),
    )
    report.note(f'{len(replayed.run_sync())} envelopes, 0 tool calls', title='counts')


if __name__ == '__main__':
    main()
