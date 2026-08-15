# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Turn a product idea into a landing page under a fixed workspace root.

What you will see (sample run):
  === protocol ===
  Founder -> Analyst : Idea(str)
  Analyst -> Engineer : Expanded(str)
  ...
  Engineer -> Founder : Site(str)
  end
  === conversation ===
  Founder:Idea -> Analyst 'a landing page for multiparty agent protocols'
  Analyst:Expanded -> Engineer '...'
  Engineer:Templates -> Workspace None
  ...
  Engineer:Site -> Founder '...'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/landing_page.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    msg,
    project_all,
    repeat,
)

Founder, Analyst, Engineer, Workspace = pa.roles(
    'Founder',
    'Analyst',
    'Engineer',
    'Workspace',
)


TEMPLATES = ('keynote', 'salient')
COMPONENTS = ('Hero', 'Features')

TEMPLATE = pa.Text.where('a known template name', lambda name: name in TEMPLATES)

COMPONENT = pa.record('Component', name=str, code=str).where(
    'a known component name and non-empty code',
    lambda c: c.get('name') in COMPONENTS and bool(c.get('code')),
)


Available = pa.Text.many()('Available', 'The template names on offer.')
Components = pa.Text.many()('Components', 'The components to fill in.')
Wrote = pa.Text('Wrote', 'Where the component landed.')
Templates = pa.Nothing('Templates', 'Ask what templates exist.')
Choose = TEMPLATE('Choose', 'The template to copy into the workdir.')
Write = COMPONENT('Write', 'One component and its code.')
Site = pa.Text('Site', 'Where the generated site lives.')
Idea = pa.Text('Idea', 'The product idea in one paragraph.')
Expanded = pa.Text('Expanded', 'The idea, elaborated for a landing page.')

protocol = (
    msg[Founder, Analyst](Idea)
    >> msg[Analyst, Engineer](Expanded)
    >> msg[Engineer, Workspace](Templates)
    >> msg[Workspace, Engineer](Available)
    >> msg[Engineer, Workspace](Choose)
    >> msg[Workspace, Engineer](Components)
    >> repeat(
        2,
        msg[Engineer, Workspace](Write) >> msg[Workspace, Engineer](Wrote),
    )
    >> msg[Engineer, Founder](Site)
).close()


def component_path(root: Path, name: str) -> Path:
    """Path for a codec-validated Hero/Features name under *root*.

    Only those closed names may be written, and only below the workspace root.
    """
    if name not in COMPONENTS:
        raise ValueError(f'refused write: {name!r} is not a closed component name')
    path = (root / f'{name}.txt').resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'refused write outside workspace: {path}')
    return path


def _workspace_tools(root: Path) -> list[Any]:
    async def templates(_empty: None) -> pa.Choice:
        return pa.reply(Available, list(TEMPLATES))

    async def choose(name: str) -> pa.Choice:
        if name not in TEMPLATES:
            raise ValueError(f'refused template: {name!r} is not a closed template name')
        (root / name).mkdir(parents=True, exist_ok=True)
        return pa.reply(Components, list(COMPONENTS))

    async def write(component: dict[str, str]) -> pa.Choice:
        # Only codec-validated Hero/Features names land under the fixed root.
        path = component_path(root, component['name'])
        path.write_text(component['code'], encoding='utf-8')
        return pa.reply(Wrote, str(path))

    return [
        pa.tool_for(Templates, templates),
        pa.tool_for(Choose, choose),
        pa.tool_for(Write, write),
    ]


def main() -> None:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cast = (
            pa
            .Cast(protocol)
            .play(
                Founder,
                pa.human(
                    pa.script(pa.says(Idea, 'a landing page for multiparty agent protocols')),
                ),
            )
            .play(
                Analyst,
                pa.agent(
                    model,
                    'Expand the product idea into a short landing-page brief.',
                ),
            )
            .play(
                Engineer,
                pa.agent(
                    model,
                    (
                        'Ask Templates, then Choose exactly one of: keynote, salient. '
                        "Write exactly two components: dicts with keys 'name' and 'code', "
                        'name must be Hero then Features (only those names). '
                        'Finish with Site as the workdir path string.'
                    ),
                    repair=pa.Repair(2),
                ),
            )
            .play(Workspace, pa.service(*_workspace_tools(root)))
        )
        report.conversation(cast.run_sync())


if __name__ == '__main__':
    main()
