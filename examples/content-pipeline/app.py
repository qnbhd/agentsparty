# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]", "ddgs", "gradio"]
# ///
"""A small Gradio studio for a protocol-driven content review."""

from __future__ import annotations

import asyncio
import html
import os
from dataclasses import dataclass, field
from typing import cast
from urllib.parse import urlparse

import gradio as gr
from desk import QueueDesk
from gradio.themes import GoogleFont, Soft
from openai import AsyncOpenAI
from protocol import build_participants, protocol

import agentsparty as pa

MODEL = 'gpt-5.6-luna'
TOKEN_LIMIT = 80_000
ALLOWANCE = pa.Allowance(steps=40, unfoldings=3)
HERO = '# Content pipeline\nFrom a brief to approved copy, with a human decision in the loop.'


@dataclass
class Studio:
    """One in-process content session shared by the demo UI."""

    client: AsyncOpenAI | None = None
    desk: QueueDesk = field(default_factory=QueueDesk)
    runtime: pa.AgentRuntime | None = None
    task: asyncio.Task[None] | None = None
    error: str | None = None
    revision: int = 0

    def model(self) -> pa.LanguageModel:
        """Return the metered real model, creating its client on first use."""
        if self.client is None:
            self.client = AsyncOpenAI(
                api_key=os.environ['OPENAI_API_KEY'], max_retries=0, timeout=30.0
            )
        model = pa.OpenAIModel(MODEL, self.client)
        return pa.traced(pa.Metered(model, tokens=TOKEN_LIMIT))

    def start(self, topic: str, audience: str) -> None:
        """Start a fresh session for a non-empty brief."""
        brief = f'Topic: {topic.strip()}\nAudience: {audience.strip() or "General readers"}'
        self.desk = QueueDesk()
        self.error = None
        self.revision = 0
        self.runtime = pa.AgentRuntime(
            protocol,
            build_participants(self.model(), brief, self.desk),
            allowance=ALLOWANCE,
        )
        self.task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        """Drive the runtime and retain an error for the UI boundary."""
        runtime = cast(pa.AgentRuntime, self.runtime)
        try:
            await runtime.run()
        except Exception as error:  # Gradio renders the failure; the server stays alive.
            self.error = f'{type(error).__name__}: {error}'

    def payload(self, label: str) -> object | None:
        """Return the latest decoded payload with *label*."""
        if self.runtime is None:
            return None
        return next(
            (item.payload for item in reversed(self.runtime.trace) if str(item.label) == label),
            None,
        )


studio = Studio()


def _phase() -> tuple[str, int]:
    """Return the user-facing phase and its zero-based progress index."""
    if studio.error:
        return 'Pipeline failed', 0
    if studio.task is None:
        return 'Ready for a brief', 0
    if studio.payload('Final') is not None:
        return 'Approved and published', 3
    if studio.desk.waiting:
        return 'Waiting for your review', 2
    if studio.payload('Findings') is not None:
        return 'Writer is drafting', 1
    return 'Researcher is working', 0


def _progress() -> str:
    """Render the four protocol roles as a compact progress indicator."""
    _, current = _phase()
    roles = ('Research', 'Write', 'Review', 'Publish')
    cells = ''.join(
        f'<div class="step {"done" if index < current else "active" if index == current else ""}">'
        f'<span>{index + 1}</span>{role}</div>'
        for index, role in enumerate(roles)
    )
    return f'<div class="progress">{cells}</div>'


def _document() -> str:
    """Render the latest draft or final copy without invented metadata."""
    final = studio.payload('Final')
    draft = studio.desk.latest('Draft')
    content = final if isinstance(final, str) else draft
    if not isinstance(content, str):
        return '### Your draft will appear here\n\nStart the pipeline and follow its progress.'
    title = 'Final copy' if isinstance(final, str) else f'Draft {studio.revision + 1}'
    return f'### {title}\n\n{content}'


def _source_row(item: dict[str, str]) -> str:
    """One search result: the source site's icon and its brief, one line."""
    host = urlparse(item.get('href', '')).netloc or 'source'
    icon = f'https://icons.duckduckgo.com/ip3/{host}.ico'
    title = html.escape(item.get('title', ''))
    note = html.escape(item.get('body', ''))
    href = html.escape(item.get('href', ''), quote=True)
    return (
        f'<li><img src="{icon}" alt="">'
        f'<a href="{href}" target="_blank" rel="noopener">{title}</a>'
        f'<span class="s-note">{note}</span></li>'
    )


def _sources() -> str:
    """Render the research sources once the live search has answered."""
    results = studio.payload('Results')
    if not isinstance(results, list):
        return ''
    rows = ''.join(_source_row(item) for item in results if isinstance(item, dict))
    return f'<h2>Sources</h2><ul class="sources">{rows}</ul>' if rows else ''


def _status() -> str:
    """Explain only the action currently available to the user."""
    phase, _ = _phase()
    if studio.error:
        return f'**{phase}.** `{studio.error}`'
    if studio.desk.waiting:
        return f'**{phase}.** Approve the draft or send one clear revision note.'
    if studio.payload('Final') is not None:
        return f'**{phase}.** The protocol is complete.'
    return f'**{phase}.** Review controls unlock when the Editor receives a draft.'


def _view() -> tuple[object, ...]:
    """Build one consistent snapshot for every Gradio refresh."""
    waiting = studio.desk.waiting
    running = studio.task is not None and not studio.task.done()
    return (
        _status(),
        _progress(),
        _sources(),
        _document(),
        gr.update(interactive=not running),
        gr.update(interactive=waiting),
        gr.update(interactive=waiting),
        gr.update(interactive=waiting),
    )


async def start_pipeline(topic: str, audience: str) -> tuple[object, ...]:
    """Validate the UI boundary and begin a pipeline session."""
    if not topic.strip():
        raise gr.Error('Enter a topic first.')
    studio.start(topic, audience)
    await asyncio.sleep(0)
    return _view()


async def approve() -> tuple[object, ...]:
    """Choose Approve only while that protocol branch is offered."""
    if not studio.desk.submit('Approve'):
        raise gr.Error('Approve is not available at this point in the protocol.')
    await asyncio.sleep(0)
    return _view()


async def revise(note: str) -> tuple[object, ...]:
    """Send a non-empty revision note through the offered Revise branch."""
    if not note.strip():
        raise gr.Error('Describe what the writer should revise.')
    if not studio.desk.submit('Revise', note.strip()):
        raise gr.Error('Revise is not available at this point in the protocol.')
    studio.revision += 1
    await asyncio.sleep(0)
    return _view()


CSS = """
:root { --paper: #fff; --ink: #1f1f1f; --muted: #707070; --line: #dedede; --accent: #008e52; }
html, body, .gradio-container {
  min-height: 100%; color-scheme: light !important;
  background: var(--paper) !important; color: var(--ink) !important;
  font-family: var(--font) !important;
}
body { margin: 0 !important; }
.gradio-container {
  width: 100% !important; max-width: none !important; min-height: 100vh !important;
  padding: 48px 28px 64px !important;
}
#hero, #workspace { width: min(1360px, 100%); margin-inline: auto !important; }
footer { display: none !important; }
#hero h1 {
  font-size: 16pt; line-height: .98;
  letter-spacing: -.05em; margin-bottom: 14px;
}
#hero p { color: var(--muted); max-width: 620px; font-size: 1.05rem; }
#workspace { gap: 28px; align-items: stretch; margin-top: 32px; }
#sidebar, #editor { gap: 16px; }
#sidebar { border-right: 1px solid var(--line); padding-right: 28px; }
#document { border: 1px solid var(--line) !important; background: #fff !important; }
#document { min-height: calc(100vh - 250px); padding: 42px 48px; }
#document h3 { font-size: 1.5rem; margin-bottom: 24px; }
#document p { max-width: 66ch; line-height: 1.75; }
.progress { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; }
.step {
  padding: 11px 12px; color: var(--muted);
  border-top: 2px solid var(--line); font-size: .8rem;
}
.step span { display: block; font-size: .7rem; margin-bottom: 3px; }
.step.active, .step.done { color: var(--accent); border-color: var(--accent); }
#sources h2 { font-size: 1.1rem; margin: 20px 0 4px; }
#sources ul { list-style: none; margin: 0; padding: 0; }
#sources li {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 0; border-top: 1px solid var(--line); font-size: .8rem;
}
#sources img { width: 14px; height: 14px; flex: none; }
#sources a {
  color: var(--ink); text-decoration: none;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: none; max-width: 40%;
}
#sources .s-note {
  color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
#status { min-height: 34px; }
#run, #approve { background: var(--accent) !important; border-color: var(--accent) !important; }
.gradio-container button, .gradio-container input, .gradio-container textarea {
  border-radius: 0 !important; box-shadow: none !important; font-family: var(--font) !important;
}
.gradio-container button { font-size: 14px !important; font-weight: 400 !important; }
.gradio-container .form {
  background: transparent !important; border: 0 !important; box-shadow: none !important;
}
.gradio-container .form > .block {
  padding: 0 !important; background: transparent !important;
  border: 0 !important; box-shadow: none !important;
}
.gradio-container .prose, .gradio-container h1, .gradio-container h2,
.gradio-container h3, .gradio-container p, .gradio-container strong {
  color: var(--ink) !important;
}
.gradio-container textarea, .gradio-container input {
  border: 1px solid var(--line) !important; border-radius: 0 !important;
  background: #fff !important; box-shadow: none !important; color: var(--ink) !important;
  -webkit-text-fill-color: var(--ink) !important;
}
.gradio-container textarea::placeholder, .gradio-container input::placeholder {
  color: var(--muted) !important; opacity: .65;
}
@media (max-width: 760px) {
  .gradio-container { padding: 24px 16px 40px !important; }
  #workspace { flex-direction: column; }
  #sidebar { border-right: 0; border-bottom: 1px solid var(--line); padding: 0 0 24px; }
  .progress { grid-template-columns: repeat(2,1fr); }
}
"""
THEME = Soft(
    primary_hue='emerald',
    neutral_hue='stone',
    font=GoogleFont('Geist'),
)


def build_ui() -> gr.Blocks:
    """Create the Gradio Blocks application and wire protocol-safe actions."""
    with gr.Blocks(title='Content pipeline') as demo:
        gr.Markdown(HERO, elem_id='hero')
        with gr.Row(elem_id='workspace', equal_height=False):
            with gr.Column(scale=3, min_width=280, elem_id='sidebar'):
                gr.Markdown('## Brief')
                topic = gr.Textbox(
                    label='Topic',
                    placeholder='Topic',
                    lines=3,
                    show_label=False,
                )
                audience = gr.Textbox(
                    label='Audience',
                    placeholder='Audience',
                    show_label=False,
                )
                run = gr.Button('Create draft', variant='primary', elem_id='run')
                status = gr.Markdown(_status(), elem_id='status')
                progress = gr.HTML(_progress())
                sources = gr.HTML(_sources(), elem_id='sources')
                gr.Markdown('## User revision')
                note = gr.Textbox(
                    label='Revision note',
                    placeholder='Revision note',
                    lines=2,
                    interactive=False,
                    show_label=False,
                )
                revise_button = gr.Button('Request revision', interactive=False)
                approve_button = gr.Button(
                    'Approve', variant='primary', interactive=False, elem_id='approve'
                )
            with gr.Column(scale=9, min_width=620, elem_id='editor'):
                document = gr.Markdown(_document(), elem_id='document')

        outputs = [status, progress, sources, document, run, approve_button, revise_button, note]
        run.click(start_pipeline, [topic, audience], outputs, concurrency_limit=1)
        approve_button.click(approve, outputs=outputs, concurrency_limit=1)
        revise_button.click(revise, note, outputs, concurrency_limit=1)
        gr.Timer(0.5).tick(_view, outputs=outputs, show_progress='hidden')
    return demo


if __name__ == '__main__':
    build_ui().queue().launch(
        server_name='127.0.0.1',
        server_port=int(os.environ.get('PORT', '7860')),
        show_error=True,
        theme=THEME,
        css=CSS,
        footer_links=[],
    )
