# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Canonical first run: two roles, Cast + factories, with an OpenAI model.

# docs: start protocol
What you will see (exact)::

    === protocol ===
    Writer -> Reader : Note(str)
    end
    === conversation ===
    Writer -> Reader : Note('hello')

"""

from __future__ import annotations

from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.choreography import Chor, choreography
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty.protocol import render
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Writer, Reader = roles('Writer', 'Reader')


@choreography
def note(c: Chor) -> None:
    c.say(Writer, Reader, 'Note')


protocol = note()
# docs: end protocol


def main() -> None:
    """Bind participants and print the delivery trace."""
    print('=== protocol ===')
    print(render(protocol))
    model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
    # docs: start run
    cast = (
        Cast(protocol)
        .play(Writer, agent(model, 'Send a short note.'))
        .play(Reader, human(script()))
    )
    print('=== conversation ===')
    for envelope in cast.run_sync():
        print(
            f'{envelope.sender.name} -> {envelope.receiver.name} : '
            f'{envelope.label}({envelope.payload!r})',
        )
    # docs: end run


if __name__ == '__main__':
    main()
