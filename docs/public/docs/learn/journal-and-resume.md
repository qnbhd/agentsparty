# Journal and resume (/docs/learn/journal-and-resume)

# 6 — Journal and resume

The session dies in the middle — a crash, a cancelled run. Restarting it
should not re-ask the model for decisions it already made. A journal records
the authored decisions; a resume restores them.

Durability is about authored decisions, not a screenshot of every runtime
event. The first run writes the selected branch to a journal; the second run
restores that decision without asking the model again.

## Run, then replay

```python compile
from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty.journal import MemoryJournal
from agentsparty import OpenAIModel
from agentsparty.protocol import Text, case, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

A, B = roles('A', 'B')
# The journal will capture the decision for this one-message session.
protocol = msg[A, B](Text('Note'))
journal = MemoryJournal()
first_model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0))
Cast(protocol).play(A, agent(first_model, 'n')).play(
    B, human(script())
).run_sync(journal=journal)

# Re-run from the journal; the recorded decision avoids a new model call.
replay_model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0))
replay_journal = MemoryJournal(journal.script().decisions)
trace = (
    Cast(protocol)
    .play(A, agent(replay_model, 'n'))
    .play(B, human(script()))
    .run_sync(journal=replay_journal)
)
assert trace[0].payload == 'durable'
print('replayed', trace[0].payload)
```

The recorded decision is the proof: replay did not invoke the model. The
journal supplied every decision the session needed.

## What a journal is not

- It is not a trace. A journal stores **decisions** for replay; a tracer
  stores observations for humans. Do not mix the terms.
- It does not cover external side effects. A tool call already performed on
  the first run is an application-level concern — journaled decisions make
  replay deterministic, they do not make external APIs idempotent.

`MemoryJournal` is for tests; `JsonlJournal` and `SqliteJournal` persist to
disk. The complete step is `docs/examples/tutorial/04_durable_session.py`.

Next: [observable session](/docs/learn/observable-session).

