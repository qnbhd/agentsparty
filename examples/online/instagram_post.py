# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Compose a product Instagram post: research, angle, copy, then a shot.

What you will see (sample run):
  === protocol ===
  Brand -> Analyst : Product(str)
  Analyst -> Strategist : Findings(str)
  ...
  Photographer -> Brand : Post({str: str})
  end
  === conversation ===
  Brand:Product -> Analyst 'agentsparty: multiparty session types for agents'
  Analyst:Findings -> Strategist '...'
  ...
  Photographer:Post -> Brand {'hook': '...', 'body': '...'}

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/instagram_post.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    compose,
    equal_session,
    ipart,
    localise,
    msg,
    owning,
    project_all,
    project_onto,
    render,
)

Brand, Analyst, Strategist, Copywriter, Photographer, Director = pa.roles(
    'Brand',
    'Analyst',
    'Strategist',
    'Copywriter',
    'Photographer',
    'Director',
)


COPY = pa.record('Copy', hook=str, body=str)
SHOT = pa.Text.where(
    'one paragraph, no product in frame',
    lambda s: '\n' not in s.strip(),
)


Copy = COPY('Copy', 'Hook and body for the post.')
Post = COPY('Post', 'The finished post.')
Angle = pa.Text('Angle', 'The campaign angle.')
Approved = SHOT('Approved', 'The approved photograph description.')
Product = pa.Text('Product', 'The product page and extra details.')
WRONG = COPY('WRONG', 'Hook and body for the post.')
Findings = pa.Text('Findings', 'Selling points and competitors.')
Shot = SHOT('Shot', 'One paragraph describing the photograph.')

TEXT_COMPONENT = owning(Analyst, Strategist, Copywriter).defining(
    msg[Brand, Analyst](Product)
    >> msg[Analyst, Strategist](Findings)
    >> msg[Strategist, Copywriter](Angle)
    >> msg[Copywriter, Photographer](Copy),
)

IMAGE_COMPONENT = owning(Photographer, Director).defining(
    msg[Copywriter, Photographer](Copy)
    >> msg[Photographer, Director](Shot)
    >> msg[Director, Photographer](Approved)
    >> msg[Photographer, Brand](Post),
)

CONTRACT = (
    msg[Brand, Analyst](Product)
    >> msg[Copywriter, Photographer](Copy)
    >> msg[Photographer, Brand](Post)
).close()


protocol = compose(CONTRACT, [TEXT_COMPONENT, IMAGE_COMPONENT])


def build() -> tuple[SessionType, list[pa.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    strict = pa.Repair(attempts=2)
    analyst = pa.Agent(
        model,
        Analyst,
        'Summarise selling points and competitors in one short Findings sentence.',
        protocol,
    )
    strategist = pa.Agent(
        model,
        Strategist,
        'Pick one clear campaign Angle in a short phrase for agent-tooling authors.',
        protocol,
    )
    copywriter = pa.Agent(
        model,
        Copywriter,
        "Write Copy as a dict with exactly keys 'hook' and 'body' (short strings).",
        protocol,
        repair=strict,
    )
    photographer = pa.Agent(
        model,
        Photographer,
        (
            'Describe Shot as one paragraph with no newlines and no product in frame; '
            "after approval, deliver Post as a dict with keys 'hook' and 'body'."
        ),
        protocol,
        repair=strict,
    )
    director = pa.Agent(
        model,
        Director,
        (
            'Approve the shot: reply Approved with one paragraph, no newlines, '
            'and no product in frame.'
        ),
        protocol,
        repair=strict,
    )
    brand = pa.Human(
        Brand,
        protocol,
        pa.ScriptedHumanIo([pa.says(Product, 'agentsparty: multiparty session types for agents')]),
    )
    return protocol, [brand, analyst, strategist, copywriter, photographer, director]


def main() -> None:
    report = debug.Report()
    report.protocol(protocol)
    report.note(
        f'text component: {render(localise(TEXT_COMPONENT)).splitlines()[0]} ...',
        title='component',
    )
    kept = equal_session(project_onto(protocol, ipart(TEXT_COMPONENT)), TEXT_COMPONENT)
    report.note(f'projection preserved for text component: {kept}', title='projection')
    project_all(protocol)

    _, participants = build()
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())

    broken = owning(Analyst, Strategist, Copywriter).defining(
        msg[Brand, Analyst](Product)
        >> msg[Analyst, Strategist](Findings)
        >> msg[Strategist, Copywriter](Angle)
        >> msg[Copywriter, Photographer](WRONG),
    )
    with report.refusing(pa.CompositionError, title='an incompatible component'):
        compose(CONTRACT, [broken, IMAGE_COMPONENT])


if __name__ == '__main__':
    main()
