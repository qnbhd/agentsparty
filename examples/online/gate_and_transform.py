# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Gate a public post, then turn accepted material into a scored screenplay.

What you will see (sample run):
  === protocol ===
  Feed -> Guard : Post(str)
  Guard -> Feed {
    Accept(str): end
    Reject(str): end
  }
  ---
  Feed -> Writer : Material(str)
  ...
  Scorer -> Feed : Score(int)
  end
  === conversation ===
  Feed:Post -> Guard 'BUY CHEAP PILLS NOW!!!'
  Guard:Reject -> Feed 'spam product pitch'
  Feed:Post -> Guard 'A quiet walk under the old bridge.'
  Guard:Accept -> Feed 'A quiet walk under the old bridge.'
  Feed:Material -> Writer 'A quiet walk under the old bridge.'
  ...
  Scorer:Score -> Feed 7

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/gate_and_transform.py
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
)

Feed, Guard, Writer, Formatter, Scorer = ap.roles(
    'Feed',
    'Guard',
    'Writer',
    'Formatter',
    'Scorer',
)

SCREENPLAY = ap.Text.where(
    'no stage directions in parentheses',
    lambda s: '(' not in s and ')' not in s,
)
SCORE = ap.Integer.between(1, 10)


Post = ap.Text('Post', 'A public post to consider.')
Accept = ap.Text('Accept', 'The post, cleaned of quoting noise.')
Reject = ap.Text('Reject', 'Why this post is spam or abusive.')
Material = ap.Text('Material', 'The accepted post.')
Dialogue = ap.Text('Dialogue', 'The post as a dialogue.')
Screenplay = SCREENPLAY('Screenplay', 'The formatted screenplay.')
Score = SCORE('Score', 'How good the screenplay is, one to ten.')

GATE = (msg[Feed, Guard](Post) >> alt[Guard, Feed](Accept, Reject)).close()

PIPELINE = (
    msg[Feed, Writer](Material)
    >> msg[Writer, Formatter](Dialogue)
    >> msg[Formatter, Scorer](Screenplay)
    >> msg[Scorer, Feed](Score)
).close()


def _feed(protocol: SessionType, text: str) -> ap.Machine:
    def decide(view: ap.View) -> ap.Choice:
        names = {label.name for label in view.offered}
        if Post.label.name in names:
            return ap.says(Post, text)
        if Material.label.name in names:
            return ap.says(Material, text)
        return ap.Choice(min(view.offered))

    return ap.Machine(Feed, protocol, decide)


def build_gate(post: str) -> list[ap.Participant]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    guard = ap.Agent(
        model,
        Guard,
        (
            'Accept clean, thoughtful posts (reply Accept with the cleaned text). '
            'Reject spam, scams, or abusive pitches (reply Reject with a short reason).'
        ),
        GATE,
    )
    return [_feed(GATE, post), guard]


def build_pipeline(material: str) -> list[ap.Participant]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = ap.OpenAIModel('gpt-5.6-luna', client)
    strict = ap.Repair(attempts=2)
    writer = ap.Agent(
        model,
        Writer,
        'Turn the post into a short two-speaker Dialogue (plain text).',
        PIPELINE,
    )
    formatter = ap.Agent(
        model,
        Formatter,
        (
            'Format the dialogue as a Screenplay in plain text. '
            'Do not use parentheses anywhere (no stage directions).'
        ),
        PIPELINE,
        repair=strict,
    )
    scorer = ap.Agent(
        model,
        Scorer,
        'Score the screenplay as an integer from 1 to 10 inclusive.',
        PIPELINE,
        repair=strict,
    )
    return [_feed(PIPELINE, material), writer, formatter, scorer]


def main() -> None:
    report = debug.Report()
    project_all(GATE)
    project_all(PIPELINE)
    report.protocol(GATE)
    report.protocol(PIPELINE, title='pipeline')

    spam = ap.AgentRuntime(GATE, build_gate('BUY CHEAP PILLS NOW!!!')).run_sync()
    report.conversation(spam, title='spam — Reject stops before PIPELINE')

    material = 'A quiet walk under the old bridge.'
    clean_gate = ap.AgentRuntime(GATE, build_gate(material)).run_sync()
    report.conversation(clean_gate, title='clean — Accept, then PIPELINE')
    clean_pipe = ap.AgentRuntime(PIPELINE, build_pipeline(material)).run_sync()
    report.conversation(clean_pipe, title='pipeline run')


if __name__ == '__main__':
    main()
