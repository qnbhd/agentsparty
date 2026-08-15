# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Two agents exchange one note — the shortest live session.

What you will see (sample run):
  === protocol ===
  Writer -> Reviewer : Note(str)
  Reviewer -> Writer : Ack(str)
  end
  === conversation ===
  Writer:Note -> Reviewer 'Ship the typed choreography first.'
  Reviewer:Ack -> Writer 'Received.'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/hello.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import msg

Writer, Reviewer = pa.roles('Writer', 'Reviewer')

Note = pa.Text('Note', 'One short sentence.')
Ack = pa.Text('Ack', 'A one-word acknowledgement.')

protocol = (msg[Writer, Reviewer](Note) >> msg[Reviewer, Writer](Ack)).close()


def main() -> None:
    report = debug.Report()
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    report.protocol(protocol)
    cast = (
        pa
        .Cast(protocol)
        .play(Writer, pa.agent(model, 'Send one short sentence as Note.'))
        .play(Reviewer, pa.agent(model, 'Reply Ack with one short word.'))
    )
    report.conversation(cast.run_sync())


if __name__ == '__main__':
    main()
