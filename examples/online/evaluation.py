# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Solve a tiny problem under a judge; run facts come from MemoryTracer.

Sample run (conversation sketch, 3-6 lines)::

    Bench:Problem -> Solver 'return the sum of two integers'
    Solver:Solution -> Judge '…'
    Judge:Fail -> Solver '…'     # or Pass with score 1-5
    Solver:Retrying -> Bench '…'
    Solver:Solution -> Judge '…'
    Judge:Pass -> Solver 5
    Solver:Accepted -> Bench 5

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/evaluation.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    Label,
    SessionType,
    alt,
    msg,
    project_all,
    rec,
    var,
)

Bench, Solver, Judge = ap.roles('Bench', 'Solver', 'Judge')

VERDICT = ap.Integer.between(1, 5)


Problem = ap.Text('Problem', 'The task to solve.')
Solution = ap.Text('Solution', 'The current solution.')
Pass = VERDICT('Pass', 'A score from one to five.')
Accepted = VERDICT('Accepted', 'The score that was awarded.')
Fail = ap.Text('Fail', 'What is wrong with the solution.')
Retrying = ap.Text('Retrying', 'Progress note.')

protocol = (
    msg[Bench, Solver](Problem)
    >> rec(
        'attempt',
        msg[Solver, Judge](Solution)
        >> alt[Judge, Solver](
            Pass >> msg[Solver, Bench](Accepted),
            Fail >> msg[Solver, Bench](Retrying) >> var('attempt'),
        ),
    )
).close()


def _bench_decide(view: ap.View) -> ap.Choice:
    offered = {label.name for label in view.offered}
    if 'Problem' in offered:
        return ap.says(Problem, 'return the sum of two integers')
    return ap.Choice(view.offered[0])


def _judge_decide(view: ap.View) -> ap.Choice:
    solutions = [e.payload for e in view.seen if e.label == Label('Solution')]
    latest = str(solutions[-1]) if solutions else ''
    if 'a + b' in latest:
        return ap.says(Pass, 5)
    return ap.says(Fail, 'must use addition, not subtraction')


def build() -> tuple[SessionType, list[ap.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    solver = ap.Agent(
        ap.traced(model),
        Solver,
        'Solve the Problem as plain-text Solution (a short code or formula). '
        'After Fail, send Retrying with a brief progress note, then a new '
        'Solution. After Pass, send Accepted with the same integer score you '
        'received (an integer from 1 to 5). Prefer solutions that use '
        "addition of two integers, e.g. involving 'a + b'.",
        protocol,
        repair=ap.Repair(attempts=2),
    )
    return protocol, [
        ap.Machine(Bench, protocol, _bench_decide),
        solver,
        ap.Machine(Judge, protocol, _judge_decide),
    ]


def main() -> None:
    report = debug.Report()
    project_all(protocol)
    report.protocol(protocol)
    _, participants = build()
    tracer = ap.MemoryTracer()
    trace = ap.AgentRuntime(protocol, participants, tracer=tracer).run_sync()
    report.conversation(trace)
    report.facts(tracer.events)
    report.note(
        f'Delivered == len(trace): {tracer.names().count("step.delivered") == len(trace)}',
        title='check',
    )


if __name__ == '__main__':
    main()
