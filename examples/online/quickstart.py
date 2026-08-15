# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Writer drafts a note; Reviewer approves or rejects; Reader receives Final.

What you will see (sample run):
  === protocol ===
  Writer -> Reviewer : Draft(str)
  Reviewer -> Writer {
    Approve():
      Writer -> Reader : Final(str)
      end
    Reject():
      Writer -> Reader : Final(str)
      end
  }
  === conversation ===
  Writer:Draft -> Reviewer 'Ship the typed choreography first.'
  Reviewer:Approve -> Writer
  Writer:Final -> Reader 'Ship the typed choreography first.'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/quickstart.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import alt, msg

Writer, Reviewer, Reader = pa.roles('Writer', 'Reviewer', 'Reader')


Draft = pa.Text('Draft')
Approve = pa.Nothing('Approve')
Final = pa.Text('Final')
Reject = pa.Nothing('Reject')

protocol = (
    msg[Writer, Reviewer](Draft)
    >> alt[Reviewer, Writer](
        Approve >> msg[Writer, Reader](Final),
        Reject >> msg[Writer, Reader](Final),
    )
).close()


def main() -> None:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    report = debug.Report()
    report.protocol(protocol)
    cast = (
        pa
        .Cast(protocol)
        .play(Writer, pa.agent(model, 'Write a one-sentence draft note.'))
        .play(
            Reviewer,
            pa.agent(
                model,
                'Approve or Reject the draft. Prefer Approve when the draft is clear.',
            ),
        )
        .play(Reader, pa.human(pa.script()))
    )
    report.conversation(cast.run_sync())


if __name__ == '__main__':
    main()
