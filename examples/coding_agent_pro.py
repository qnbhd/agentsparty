# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]", "textual>=8.2"]
# ///
"""A coding agent that works on a real directory, watched live in the terminal.

The protocol is the control. During planning the local type offers List and
Read against the working directory — Write is unrepresentable, so the planner
*cannot* touch a file however it is prompted. The implementer then writes as
often as it needs. The reviewer then reads the written files back from the
workspace and takes exactly one verdict: Ship, or one Fix.

Everything the roles say to each other is drawn from the session's own trace:
one ``QueueTracer`` feeds the stream, so what is on screen is what was
recorded, badged with its label, routed ``sender ❯ receiver`` and summarised
in one line.

The workspace is the directory given on the command line (the current one by
default). Files are really read and really written there.

Run::

    export OPENAI_API_KEY=...
    uv run --group examples python examples/coding_agent_pro.py [directory]
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, ClassVar

from openai import AsyncOpenAI
from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

import agentsparty as ap
from agentsparty.kernel.errors import PayloadError
from agentsparty.kernel.role import Role
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol import Chosen, alt, msg, rec, var
from agentsparty.protocol.language.core import BranchCodec, Label
from agentsparty.tracing import FAILURE, MODEL, SESSION, STEP
from agentsparty.tracing.signals import Signal

# ── the choreography ────────────────────────────────────────────────────────

Client, Planner, Workspace, Coder, Reviewer = ap.roles(
    'Client',
    'Planner',
    'Workspace',
    'Coder',
    'Reviewer',
)

MODEL_NAME = 'gpt-5.6-luna'

RelPath = ap.Text.where(
    'a relative path that stays in the workspace',
    lambda p: not Path(p).is_absolute() and '..' not in Path(p).parts,
)

Task = ap.Text('Task', 'The coding task in one sentence.')
List = RelPath('List', 'Relative directory to list.')
Listing = ap.Text.many()('Listing', 'Relative paths under that directory.')
Read = RelPath('Read', 'Relative file path to read.')
Source = ap.Text('Source', 'File contents, or a missing-file note.')
Ready = ap.Nothing('Ready', 'Planning is finished.')
Noted = ap.Nothing('Noted', 'Workspace acknowledgement.')
Looking = ap.Nothing('Looking', 'Planner is still reading.')
Outline = ap.Text('Outline', 'The plan, visible to everyone who waits.')
Plan = ap.Text('Plan', 'What the coder should implement.')
Write = ap.record('Write', path=str, content=str)(
    'Write',
    'Relative path and the full file contents.',
)
Saved = ap.Text('Saved', 'Where the write landed.')
Done = ap.Nothing('Done', 'Implementation is ready for review.')
Working = ap.Nothing('Working', 'Coder is still writing.')
Patch = ap.Text('Patch', 'What changed, for review.')
Verifying = ap.Nothing('Verifying', 'Reviewer is still reading files.')
Checked = ap.Nothing('Checked', 'File reading is finished.')
Ship = ap.Nothing('Ship', 'Accept the work as it stands.')
Fix = ap.Text('Fix', 'One concrete change, at most twenty words.')
Idle = ap.Nothing('Idle', 'No further write.')
Delivered = ap.Text('Delivered', 'The accepted result.')


def _still_reading():
    # Silent roles hear Looking so the explore alt is mergeable.
    return (
        msg[Planner, Client](Looking)
        >> msg[Planner, Coder](Looking)
        >> msg[Planner, Reviewer](Looking)
        >> var('explore')
    )


def _handoff():
    # The reviewer hears the task itself, so its verdict is judged against it.
    return (
        msg[Planner, Coder](Plan)
        >> msg[Planner, Client](Outline)
        >> msg[Planner, Reviewer](Task)
        >> msg[Planner, Reviewer](Outline)
    )


def _still_writing():
    return msg[Coder, Client](Working) >> msg[Coder, Reviewer](Working) >> var('implement')


def _still_verifying():
    # Silent roles hear Verifying so the verify alt is mergeable.
    return msg[Reviewer, Client](Verifying) >> msg[Reviewer, Coder](Verifying) >> var('verify')


verdict = alt[Reviewer, Coder](
    Ship
    >> msg[Coder, Workspace](Idle)
    >> msg[Workspace, Coder](Noted)
    >> msg[Coder, Client](Delivered),
    Fix
    >> msg[Coder, Workspace](Write)
    >> msg[Workspace, Coder](Saved)
    >> msg[Coder, Client](Delivered),
)

review = rec(
    'verify',
    alt[Reviewer, Workspace](
        Read >> msg[Workspace, Reviewer](Source) >> _still_verifying(),
        Checked
        >> msg[Workspace, Reviewer](Noted)
        # the Client must hear which branch was taken before the verdict splits
        >> msg[Reviewer, Client](Checked)
        >> verdict,
    ),
)

implement = rec(
    'implement',
    alt[Coder, Workspace](
        Write >> msg[Workspace, Coder](Saved) >> _still_writing(),
        Done
        >> msg[Workspace, Coder](Noted)
        >> msg[Coder, Reviewer](Patch)
        >> msg[Coder, Client](Patch)
        >> review,
    ),
)

protocol = (
    msg[Client, Planner](Task)
    >> rec(
        'explore',
        alt[Planner, Workspace](
            List >> msg[Workspace, Planner](Listing) >> _still_reading(),
            Read >> msg[Workspace, Planner](Source) >> _still_reading(),
            Ready >> msg[Workspace, Planner](Noted) >> _handoff() >> implement,
        ),
    )
).close()

# ── the workspace, on real files ────────────────────────────────────────────

SKIPPED = {'.git', '.venv', '__pycache__', 'node_modules'}


def _inside(root: Path, rel: str) -> Path | None:
    """Resolve *rel* under *root*, or None when it would escape."""
    candidate = (root / (rel or '.')).resolve()
    if not candidate.is_relative_to(root.resolve()):
        return None
    return candidate


def _visible(path: Path) -> bool:
    """Whether *path* is worth showing an agent, rather than machinery."""
    return path.name not in SKIPPED and not path.name.startswith('.')


async def _ack(_empty: None) -> ap.Choice:
    return ap.reply(Noted, None)


def _list_dir(root: Path, rel: str) -> ap.Choice:
    path = _inside(root, rel)
    if path is None or not path.is_dir():
        return ap.reply(Listing, [])
    entries = (child for child in path.iterdir() if _visible(child))
    names = sorted(
        f'{child.relative_to(root).as_posix()}{"/" if child.is_dir() else ""}' for child in entries
    )
    return ap.reply(Listing, names)


def _read_file(root: Path, rel: str) -> ap.Choice:
    path = _inside(root, rel)
    if path is None or not path.is_file():
        return ap.reply(Source, f'missing: {rel}')
    return ap.reply(Source, path.read_text(encoding='utf-8'))


def _write_file(root: Path, payload: dict[str, str]) -> ap.Choice:
    path = _inside(root, payload['path'])
    if path is None:
        return ap.reply(Saved, 'refused: path escapes the workspace')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload['content'], encoding='utf-8')
    return ap.reply(Saved, path.relative_to(root).as_posix())


def workspace_tools(root: Path) -> list[Any]:
    """Read tools plus write tools for one workspace directory."""

    async def list_dir(rel: str) -> ap.Choice:
        return _list_dir(root, rel)

    async def read_file(rel: str) -> ap.Choice:
        return _read_file(root, rel)

    async def write(payload: dict[str, str]) -> ap.Choice:
        return _write_file(root, payload)

    return [
        ap.tool_for(List, list_dir),
        ap.tool_for(Read, read_file),
        ap.tool_for(Ready, _ack),
        ap.tool_for(Write, write),
        ap.tool_for(Done, _ack),
        ap.tool_for(Checked, _ack),
        ap.tool_for(Idle, _ack),
    ]


PLANNER_BRIEF = (
    'Explore with List and Read only. List the workspace, read every file you '
    'intend to change and the ones it depends on, then Ready and send Plan: '
    'what to change, in which file, and how. Do not invent files you have not '
    'read.'
)
CODER_BRIEF = (
    'Carry out Plan. Write the full file contents every time — a Write '
    'replaces the file. Write as many files as the plan needs, one Write each. '
    'When the change is in place, Done and send Patch describing what changed. '
    'After Ship, send Idle then Delivered. After Fix, Write once more, then '
    'Delivered.'
)
REVIEWER_BRIEF = (
    'Judge the real files, not the description. You know the Task and the '
    'Plan outline; when Patch arrives, Read every file it mentions and check '
    'the actual contents. Then Checked, and tell the Coder: Ship when the '
    'implementation fulfils the task, or Fix — at most twenty words, one '
    'review.'
)


def build_cast(root: Path, client_io: Any, model: ap.LanguageModel) -> ap.Cast:
    """Bind every role for an interactive run against *root*."""
    return (
        ap
        .Cast(protocol)
        .play(Client, ap.human(client_io))
        .play(
            Planner, ap.agent(model, PLANNER_BRIEF, effort='medium', repair=ap.Repair(attempts=2))
        )
        .play(Coder, ap.agent(model, CODER_BRIEF, effort='medium', repair=ap.Repair(attempts=2)))
        .play(Reviewer, ap.agent(model, REVIEWER_BRIEF, repair=ap.Repair(attempts=2)))
        .play(Workspace, ap.service(*workspace_tools(root)))
    )


# ── the view ────────────────────────────────────────────────────────────────

BANNER = """\
██████   ████   ██████      ████  ██
██   ██ ██  ██  ██   ██    ██  ██ ██
██████  ██████  ██████  ██ ██████ ██
██      ██  ██  ██  ██     ██  ██ ██
██      ██  ██  ██   ██    ██  ██ ██"""

ACCENT = '#d9ff66'  # fd-primary
TEXT = '#ebebeb'  # fd-foreground
MUTED = '#a3a3a3'  # fd-muted-foreground
RULE = '#2b2b2b'  # fd-border
INK = '#212c02'  # fd-primary-foreground
PANEL = '#0f0f0f'  # fd-card
ALARM = '#ff5f5f'  # semantic error; intentionally outside theme palette
COLOURS = {
    'Client': '#ff6b6b',  # coral red
    'Planner': '#d9ff66',  # lime — primary accent
    'Workspace': '#55e6c1',  # mint / teal
    'Coder': '#5fa8ff',  # electric blue
    'Reviewer': '#c77dff',  # violet
}
PULSE = '·✢✳✻✽✻✳✢'
BODY_LINES = 4
BRIEF_WIDTH = 68


def _openai_model() -> ap.LanguageModel:
    """The configured model. Built by the caller rather than inside the app so
    a missing key fails before the screen opens, and so ``traced`` observes the
    one instance every agent speaks through.
    """
    client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'], max_retries=0, timeout=30.0)
    return ap.OpenAIModel(MODEL_NAME, client)


def _measure(text: str) -> str:
    """How much *text* is, for a payload the digest cannot fit on one line."""
    body = text.rstrip()
    return f'{body.count(chr(10)) + 1} lines · {len(body)} chars'


def _brief(text: str) -> str:
    """*text* on one line: itself when it fits, its measure when it does not.

    A multi-line payload is measured rather than quoted, because the lines
    themselves follow underneath — repeating the first one says nothing.
    """
    line, newline, _rest = text.partition('\n')
    if newline:
        return _measure(text)
    return line if len(line) <= BRIEF_WIDTH else f'{line[:BRIEF_WIDTH].rstrip()} …'


def _digest_many(items: list[object]) -> str:
    head = ', '.join(str(item) for item in items[:3])
    return f'{len(items)} items · {head}{" …" if len(items) > 3 else ""}'


def _digest_record(fields: dict[str, object]) -> str:
    return ' · '.join(f'{key}: {_brief(str(value))}' for key, value in fields.items())


# Payloads arrive from the trace as plain values, so the shape is read from the
# value itself; a codec this example does not use falls through to text.
_DIGESTS: dict[type, Callable[..., str]] = {list: _digest_many, dict: _digest_record}
_TEXTS: dict[type, Callable[..., str]] = {
    list: lambda items: '\n'.join(str(item) for item in items),
    dict: lambda fields: '\n'.join(f'{key}: {value}' for key, value in fields.items()),
}


# Signals carry no payload, so the line says what the label means instead;
# everything else quotes or measures the artifact it carries.
_SILENT: dict[str, str] = {
    'Looking': 'planner is still reading the workspace',
    'Ready': 'planner is done exploring',
    'Noted': 'workspace acknowledged',
    'Working': 'coder is still writing files',
    'Done': 'coder finished the implementation',
    'Verifying': 'reviewer is still reading files',
    'Checked': 'reviewer finished reading',
    'Ship': 'reviewer accepted the implementation',
    'Idle': 'no further writes',
}


def _digest(envelope: Envelope) -> str:
    """One line saying what this message carries."""
    if envelope.payload is None:
        return _SILENT.get(str(envelope.label), 'signal')
    payload = envelope.payload
    return _DIGESTS.get(type(payload), lambda value: _brief(str(value)))(payload)


def _abridged(payload: object) -> list[str]:
    """The payload's own lines under the digest — none when the digest said it all."""
    if payload is None:
        return []
    lines = _TEXTS.get(type(payload), str)(payload).rstrip().splitlines()
    if len(lines) <= 1:
        return []
    if len(lines) <= BODY_LINES:
        return lines
    return [*lines[:BODY_LINES], f'… +{len(lines) - BODY_LINES} lines']


def _ruled(rows: Sequence[str]) -> list[str]:
    """*rows* down a left rule, the last one closing it."""
    last = len(rows) - 1
    glyphs = ['└' if index == last else '│' for index in range(len(rows))]
    return [
        f'  [{RULE}]{glyph}[/] [{MUTED}]{escape(row)}[/]'
        for glyph, row in zip(glyphs, rows, strict=True)
    ]


class Card(Static):
    """One message between agents: label, route, and what it carries."""

    def __init__(self, envelope: Envelope) -> None:
        """Render *envelope* once; a delivered message never changes."""
        sender, receiver = envelope.sender.name, envelope.receiver.name
        head = (
            f'[on {COLOURS[sender]} {INK} b] {str(envelope.label).upper()} [/]  '
            f'[{COLOURS[sender]}]{sender}[/] [{RULE}]❯[/] [{COLOURS[receiver]}]{receiver}[/]'
        )
        rows = [_digest(envelope), *_abridged(envelope.payload)]
        super().__init__('\n'.join([head, *_ruled(rows)]), classes='card')


class Prompt(Static):
    """What the human sent, echoed the way a shell echoes a typed line."""

    def __init__(self, envelope: Envelope) -> None:
        """Render *envelope* as the line the human typed."""
        said = escape(_brief(str(envelope.payload)))
        super().__init__(f'[{ACCENT}]❯[/] [{TEXT}]{said}[/]', classes='said')


class Note(Static):
    """A remark the session made about itself: an unfolding, a failure."""

    def __init__(self, text: str, colour: str) -> None:
        """Render one dim line marked in *colour*."""
        super().__init__(f'[{colour}]✻[/] [{MUTED}]{escape(text)}[/]', classes='note')


def _entry(envelope: Envelope) -> Static:
    """The stream entry for *envelope*: the human's own line, or a card."""
    if envelope.sender == Client:
        return Prompt(envelope)
    return Card(envelope)


class Pulse(Static):
    """The line under the stream: what the session is waiting on, breathing."""

    def __init__(self) -> None:
        """Start breathing, with nothing yet to wait on."""
        super().__init__()
        self._frame = 0
        self._line = f'[{MUTED}]waiting for the session to start[/]'
        self._live = True

    def on_mount(self) -> None:
        """Draw once, then keep the glyph moving while a step is open."""
        self._tick()
        self.set_interval(1 / 8, self._tick)

    def waiting(self, sender: Role, offered: Sequence[Label]) -> None:
        """Announce that *sender* is choosing between *offered*."""
        choices = ' · '.join(str(label) for label in offered)
        self._line = (
            f'[{COLOURS[sender.name]}]{sender.name}[/] [{TEXT}]is deciding[/]  [{RULE}]{choices}[/]'
        )
        self._live = True
        self._tick()

    def settle(self, line: str) -> None:
        """Show *line* and stop breathing: nothing is pending any more."""
        self._line = f'[{MUTED}]{escape(line)}[/]'
        self._live = False
        self._tick()

    def _tick(self) -> None:
        self._frame += 1
        glyph = PULSE[self._frame % len(PULSE)] if self._live else '✻'
        self.update(f'[{ACCENT}]{glyph}[/] {self._line}')


class Composer(Vertical):
    """Where the human speaks: the offered branches, then the payload.

    Deliberately not a general prompt — it shows exactly what the endpoint
    type offers at this point of the session, and nothing else.
    """

    def __init__(self) -> None:
        """Create a composer with nobody waiting on it."""
        super().__init__()
        self._waiting: asyncio.Future[str] | None = None

    def compose(self) -> ComposeResult:
        """The asking line, the branch menu, and the payload entry."""
        yield Static(id='asking')
        yield OptionList(id='branches')
        with Horizontal(id='entry'):
            yield Static(f'[{ACCENT}]❯[/]', id='caret')
            yield Input(id='reply')

    def on_mount(self) -> None:
        """Stay hidden until a human turn arrives."""
        self.display = False

    async def pick(self, receiver: Role, offered: Sequence[BranchCodec]) -> BranchCodec:
        """The branch the human chose to send to *receiver*.

        A single offer is not a decision: it is taken without asking.
        """
        if len(offered) == 1:
            return offered[0]
        menu = self.query_one('#branches', OptionList)
        menu.clear_options()
        menu.add_options([Option(self._label(branch), id=str(branch.label)) for branch in offered])
        chosen = await self._turn(f'choose what {receiver.name} hears', menu)
        return next(branch for branch in offered if str(branch.label) == chosen)

    async def dictate(self, receiver: Role, branch: BranchCodec) -> str:
        """The payload the human typed for *branch*."""
        entry = self.query_one('#reply', Input)
        entry.value = ''
        entry.placeholder = branch.intent or branch.payload.name
        return await self._turn(f'{branch.label} ❯ {receiver.name}', entry)

    def warn(self, error: str) -> None:
        """Report a payload the codec refused, so the human can answer again."""
        self.query_one('#asking', Static).update(f'[{ALARM}]» {escape(error)}[/]')

    async def _turn(self, asking: str, widget: Input | OptionList) -> str:
        """Show *widget* alone and wait for what the human puts into it."""
        self.query_one('#asking', Static).update(f'[{MUTED}]{escape(asking)}[/]')
        self.query_one('#branches', OptionList).display = isinstance(widget, OptionList)
        self.query_one('#entry', Horizontal).display = isinstance(widget, Input)
        self.display = True
        widget.focus()
        self._waiting = asyncio.get_running_loop().create_future()
        try:
            return await self._waiting
        finally:
            self._waiting = None
            self.display = False

    def _label(self, branch: BranchCodec) -> str:
        return f'{branch.label}  [{MUTED}]{branch.intent or branch.payload.name}[/]'

    def _resolve(self, value: str | None) -> None:
        if value is not None and self._waiting is not None and not self._waiting.done():
            self._waiting.set_result(value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Hand the typed payload to whoever is waiting."""
        event.stop()
        self._resolve(event.value)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Hand the chosen label to whoever is waiting."""
        event.stop()
        self._resolve(event.option_id)


class TuiHumanIo:
    """Human IO that drives the composer.

    ``notify`` and ``recall`` are silent on purpose: the stream already draws
    every delivered envelope from the trace, so answering here would print
    each line the Client receives a second time.
    """

    def __init__(self, app: Studio) -> None:
        """Speak for the human playing on *app*."""
        self._app = app

    async def choose(
        self,
        subject: Role,
        receiver: Role,
        branches: dict[Label, BranchCodec],
    ) -> Chosen[BranchCodec]:
        """Ask the composer for a branch and its payload until one decodes."""
        offered = sorted(branches.values(), key=lambda branch: branch.label)
        composer = self._app.query_one(Composer)
        while True:
            branch = await composer.pick(receiver, offered)
            raw = await composer.dictate(receiver, branch) if branch.payload.carries_value else None
            try:
                return Chosen(branch=branch, payload=branch.payload.decode(raw), raw=raw)
            except PayloadError as error:
                composer.warn(str(error))

    async def notify(self, subject: Role, envelope: Envelope) -> None:
        """Do nothing: the stream already shows what was delivered."""

    async def recall(self, subject: Role, envelope: Envelope) -> None:
        """Do nothing: a replayed message is drawn from the trace too."""

    async def cancel(self, subject: Role, notice: Cancelled) -> None:
        """Close the session line with the reason it was rolled up."""
        self._app.ended(f'cancelled — {notice.reason}')


class Studio(App[None]):
    """One session of the coding-agent protocol, watched as it runs."""

    # Every ground stays transparent: the terminal's own background shows
    # through, and only the lit parts — badges, the prompt block — are painted.
    CSS = f"""
    Screen {{ background: transparent; color: {TEXT}; layout: vertical; }}
    #stream {{ height: 1fr; padding: 1 2; background: transparent;
               scrollbar-size: 1 1; scrollbar-background: transparent;
               scrollbar-color: {RULE}; }}
    #logo {{ width: auto; color: {ACCENT}; border: solid {RULE}; padding: 0 1; }}
    #head {{ margin: 1 0; }}
    .card {{ margin-bottom: 1; }}
    .said {{ margin-bottom: 1; padding: 0 1; background: {PANEL}; }}
    .note {{ margin-bottom: 1; }}
    Pulse {{ height: auto; padding: 0 2; }}
    Composer {{ height: auto; padding: 1 2 0 2; background: transparent; }}
    Composer OptionList {{ height: auto; max-height: 8; border: none;
                           background: transparent; }}
    #entry {{ height: 1; }}
    #caret {{ width: 2; }}
    #reply {{ height: 1; border: none; padding: 0; color: {TEXT};
              background: transparent; }}
    #footer {{ height: 1; padding: 0 2; margin-top: 1; }}
    """
    BINDINGS: ClassVar = [('ctrl+c', 'quit', 'quit')]

    def __init__(self, root: Path, model: ap.LanguageModel) -> None:
        """Run the protocol against the workspace at *root*.

        Args:
            root: The directory the Workspace service really reads and writes.
            model: The model every agent speaks through.
        """
        super().__init__()
        self._root = root
        self._model = model
        self._started = time.monotonic()
        self._tokens = 0
        self._steps = 0

    def compose(self) -> ComposeResult:
        """The banner and header, the stream, then the pulse and the prompt."""
        with VerticalScroll(id='stream'):
            yield Static(BANNER, id='logo')
            yield Static(id='head')
        yield Pulse()
        yield Composer()
        yield Static(id='footer')

    def on_mount(self) -> None:
        """Draw the header, then start the session; the UI watches its trace."""
        self.query_one('#head', Static).update(
            f'[{MUTED}]#[/] [b {ACCENT}]agentsparty coding agent[/] [{MUTED}]v{ap.__version__}[/]\n'
            f'[{MUTED}]# models: {MODEL_NAME} · 3 agents, 1 service, 1 human[/]\n'
            f'[{MUTED}]# workspace: {escape(str(self._root))}[/]',
        )
        self._footer()
        self.run_worker(self._session(), exclusive=True)

    def ended(self, line: str) -> None:
        """Settle the pulse on *line*; the session has nothing left to do."""
        self.query_one(Pulse).settle(line)

    async def _session(self) -> None:
        """Run the cast and fold every recorded event into the view."""
        tracer = ap.QueueTracer()
        cast = build_cast(self._root, TuiHumanIo(self), ap.traced(self._model))
        session = cast.run(allowance=ap.Allowance(unfoldings=40), tracer=tracer)
        async with ap.watching(session, tracer) as watch:
            try:
                async for event in watch.select(SESSION | STEP | MODEL | FAILURE):
                    self._fold(event.signal)
            except Exception as error:  # the session raised; say so and stay open
                self._show(Note(f'{type(error).__name__}: {error}', ALARM))
                self.ended('the session failed')

    def _fold(self, signal: Signal) -> None:
        """Move the view one signal forward."""
        match signal:
            case ap.StepStarted(sender=sender, offered=offered):
                self.query_one(Pulse).waiting(sender, offered)
            case ap.Delivered(envelope=envelope):
                self._steps += 1
                self._show(_entry(envelope))
            case ap.ModelAnswered(answer=answer):
                self._tokens += answer.usage.total_tokens
                self._footer()
            case _:
                self._remark(signal)

    def _remark(self, signal: Signal) -> None:
        """Draw what the session itself did, beside the messages it carried."""
        match signal:
            case ap.Unfolded(name=name, remaining=remaining):
                self._show(Note(f'unfolded {name} · {remaining} left', RULE))
            case ap.Failed(error=error):
                self._show(Note(error, ALARM))
            case ap.SessionFinished(messages=messages):
                elapsed = round(time.monotonic() - self._started)
                self.ended(f'worked for {elapsed}s · {messages} messages')
            case _:
                pass

    def _show(self, widget: Static) -> None:
        """Append *widget* to the stream and follow it."""
        stream = self.query_one('#stream', VerticalScroll)
        stream.mount(widget)
        stream.scroll_end(animate=False)
        self._footer()

    def _footer(self) -> None:
        """Redraw the counters under the prompt."""
        self.query_one('#footer', Static).update(
            f'[{ACCENT}]»[/] [{MUTED}]{self._steps} messages · {self._tokens} tokens[/]'
            f'  [{RULE}]·[/]  [{MUTED}]the protocol decides who speaks · ctrl+c to quit[/]',
        )


def workspace_of(argv: Sequence[str]) -> Path:
    """The directory to work in: the first argument, or the current one.

    Raises:
        SystemExit: if the path is not a directory — the agents write there.
    """
    root = Path(argv[0] if argv else '.').expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f'not a directory: {root}')
    return root


def main() -> None:
    """Watch one session against the workspace named on the command line."""
    root = workspace_of(sys.argv[1:])
    Studio(root, _openai_model()).run()
    print(f'workspace: {root}')


if __name__ == '__main__':
    main()
