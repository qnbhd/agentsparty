# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]", "pydantic"]
# ///
"""Finale: five-role design review with streaming model observation.

ProductOwner (you at the keyboard) briefs an Architect; Senior reviews the
PlantUML design; two Mids implement class diagrams; Architect merges Done.

Stdout is a human narrative. Model tokens are observed live (progress while
the model writes; decoded payloads when a step lands). Raw stream dumps stay
off the console.

What you will see (sample run):
  ── Protocol ──
  ProductOwner -> Architect : Brief
  Architect -> Senior : Design(...)
  ...
  ── Session ──
    ▶ Architect → Senior
      · model (Answer) ····· done  [..→.. tok]
      ✓ chose Design
    ...

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/main.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict

import agentsparty as pa
from agentsparty.protocol import alt, msg, render

_RULE = '─' * 56


class Answer(BaseModel):
    model_config = ConfigDict(extra='forbid')

    text: str


AnswerCodec = pa.json_model(
    'Answer',
    Answer.model_json_schema(),
    Answer.model_validate_json,
)


def build_protocol():
    ProductOwner, Architect, Senior, MidA, MidB = pa.roles(
        'ProductOwner',
        'Architect',
        'Senior',
        'MidA',
        'MidB',
    )

    Brief = pa.Text('Brief')
    Design = AnswerCodec(
        'Design',
        'ONLY a PlantUML component diagram (@startuml … @enduml), '
        '4-7 modules with dependency arrows, ~15-25 lines, no prose.',
    )
    Ok = pa.Nothing('Ok', 'Approve only a specific, production-minded diagram.')
    Reject = pa.Text(
        'Reject',
        'One sharp critique, at most 25 words, naming what is missing.',
    )
    Redesign = pa.Text('Redesign')
    Assign = pa.Text('Assign')
    Impl = pa.Text('Impl')
    Done = pa.Text('Done')

    protocol = (
        msg[ProductOwner, Architect](Brief)
        >> msg[Architect, Senior](Design)
        >> alt[Senior, Architect](
            Ok,
            Reject >> msg[Architect, Senior](Redesign) >> msg[Senior, Architect](Ok),
        )
        >> msg[Architect, MidA](Assign)
        >> msg[MidA, Architect](Impl)
        >> msg[Architect, MidB](Assign)
        >> msg[MidB, Architect](Impl)
        >> msg[Architect, ProductOwner](Done)
    ).close()
    return ProductOwner, Architect, Senior, MidA, MidB, protocol


def _agent(model, role, protocol, instructions: str) -> pa.Agent:
    return pa.Agent(
        pa.traced(model),
        role,
        instructions,
        protocol,
        effort='none',
    )


def _banner(title: str) -> None:
    print(f'\n{_RULE}')
    print(f'  {title}')
    print(_RULE)


def _indent(text: str, prefix: str = '    ') -> None:
    for line in text.splitlines() or [text]:
        print(f'{prefix}{line}')


def _print_body(payload: object) -> None:
    if payload is None:
        return
    text = str(payload)
    if not text.strip() or text == 'None':
        return
    print()
    _indent(text, '    │ ')


class _LiveView:
    """Turn the event tape into a short terminal narrative."""

    def __init__(self) -> None:
        self._writing = False
        self._dots = 0

    def see(self, event: pa.Event) -> None:
        match event.signal:
            case pa.SessionStarted() | pa.Unfolded() | pa.SessionFinished():
                self._see_session(event.signal)
            case pa.StepStarted() | pa.Selected() | pa.Recalled() | pa.Delivered():
                self._see_step(event.signal)
            case pa.ModelCalled() | pa.ModelStreamed() | pa.ModelAnswered():
                self._see_model(event.signal)
            case pa.Failed(error=error):
                self._end_writing()
                print(f'    ✗ {error}')
            case _:
                pass

    def _see_session(self, signal: pa.SessionStarted | pa.Unfolded | pa.SessionFinished) -> None:
        match signal:
            case pa.SessionStarted(participants=people):
                names = ', '.join(role.name for role in people)
                print(f'  session open · {names}')
            case pa.Unfolded(name=name, remaining=remaining):
                rest = '∞' if remaining is None else str(remaining)
                print(f'    ↻ unfold {name!r}  (left {rest})')
            case pa.SessionFinished(messages=count):
                self._end_writing()
                print(f'\n  session closed · {count} message(s)')

    def _see_step(self, signal: pa.StepStarted | pa.Selected | pa.Recalled | pa.Delivered) -> None:
        match signal:
            case pa.StepStarted(sender=sender, receiver=receiver, offered=offered):
                self._end_writing()
                labels = ', '.join(str(label) for label in offered)
                print(f'\n  ▶ {sender.name} → {receiver.name}')
                print(f'    offered: {labels}')
            case pa.Selected(label=label, payload=payload):
                self._end_writing()
                print(f'    ✓ chose {label}')
                _print_body(payload)
            case pa.Recalled(label=label, payload=payload):
                self._end_writing()
                print(f'    ↩ recalled {label}')
                _print_body(payload)
            case pa.Delivered():
                pass  # body already shown on Selected / Recalled

    def _see_model(self, signal: pa.ModelCalled | pa.ModelStreamed | pa.ModelAnswered) -> None:
        match signal:
            case pa.ModelCalled(schema_name=schema):
                self._writing = True
                self._dots = 0
                print(f'    · model ({schema}) ', end='', flush=True)
            case pa.ModelStreamed():
                self._see_streamed()
            case pa.ModelAnswered(answer=answer):
                self._see_answered(answer)

    def _see_streamed(self) -> None:
        if not self._writing:
            return
        self._dots += 1
        if self._dots % 8 == 1:
            print('·', end='', flush=True)

    def _see_answered(self, answer) -> None:
        if not self._writing:
            return
        usage = answer.usage
        bill = f'{usage.input_tokens}→{usage.output_tokens} tok'
        print(f' done  [{bill}]')
        self._writing = False

    def _end_writing(self) -> None:
        if not self._writing:
            return
        print(' interrupted')
        self._writing = False


def _print_envelopes(envelopes) -> None:
    _banner(f'Transcript · {len(envelopes)} message(s)')
    for index, envelope in enumerate(envelopes, start=1):
        print(
            f'\n  [{index}] {envelope.sender.name} → {envelope.receiver.name}  ·  {envelope.label}',
        )
        _print_body(envelope.payload)


async def async_main() -> None:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    llm = pa.OpenAIModel('gpt-5.6-luna', client)
    ProductOwner, Architect, Senior, MidA, MidB, protocol = build_protocol()

    product_owner = pa.Human(ProductOwner, protocol, pa.CliHumanIo())
    architect = _agent(
        llm,
        Architect,
        protocol,
        'You are the Architect. Follow the ProductOwner Brief exactly.',
    )
    senior = _agent(
        llm,
        Senior,
        protocol,
        'You are a strict Senior reviewer. Default to Reject on first Design. '
        'Reject unless the diagram has clear module boundaries, named '
        'dependencies, and covers the Brief without vague boxes. '
        'On Redesign, reply Ok.',
    )
    mid_a = _agent(
        llm,
        MidA,
        protocol,
        'You are MidA. Include 3-6 classes with fields (+name: Type), '
        'methods (+method(): Type), and relations (--> , --|> , o--). '
        'About 20-40 lines. No prose. No component syntax like [Foo].',
    )
    mid_b = _agent(
        llm,
        MidB,
        protocol,
        'You are MidB. Include 3-6 classes with fields (+name: Type), '
        'methods (+method(): Type), and relations (--> , --|> , o--). '
        'About 20-40 lines. No prose. No component syntax like [Foo].',
    )

    queue = pa.QueueTracer()
    runtime = pa.AgentRuntime(
        protocol,
        [product_owner, architect, senior, mid_a, mid_b],
        tracer=queue,
    )

    _banner('Protocol')
    print(render(runtime.proto))

    _banner('Session')
    view = _LiveView()
    async with pa.watching(runtime.run(), queue) as watch:
        async for event in watch:
            view.see(event)
        envelopes = await watch

    _print_envelopes(envelopes)
    print()


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print('\n  interrupted.', file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == '__main__':
    main()
