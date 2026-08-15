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

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
)

Feed, Guard, Writer, Formatter, Scorer = pa.roles(
    'Feed',
    'Guard',
    'Writer',
    'Formatter',
    'Scorer',
)

SCREENPLAY = pa.Text.where(
    'no stage directions in parentheses',
    lambda s: '(' not in s and ')' not in s,
)
SCORE = pa.Integer.between(1, 10)


Post = pa.Text('Post', 'A public post to consider.')
Accept = pa.Text('Accept', 'The post, cleaned of quoting noise.')
Reject = pa.Text('Reject', 'Why this post is spam or abusive.')
Material = pa.Text('Material', 'The accepted post.')
Dialogue = pa.Text('Dialogue', 'The post as a dialogue.')
Screenplay = SCREENPLAY('Screenplay', 'The formatted screenplay.')
Score = SCORE('Score', 'How good the screenplay is, one to ten.')

GATE = (msg[Feed, Guard](Post) >> alt[Guard, Feed](Accept, Reject)).close()

PIPELINE = (
    msg[Feed, Writer](Material)
    >> msg[Writer, Formatter](Dialogue)
    >> msg[Formatter, Scorer](Screenplay)
    >> msg[Scorer, Feed](Score)
).close()


def _feed(protocol: SessionType, text: str) -> pa.Machine:
    def decide(view: pa.View) -> pa.Choice:
        names = {label.name for label in view.offered}
        if Post.label.name in names:
            return pa.says(Post, text)
        if Material.label.name in names:
            return pa.says(Material, text)
        return pa.Choice(min(view.offered))

    return pa.Machine(Feed, protocol, decide)


def build_gate(post: str) -> list[pa.Participant]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    guard = pa.Agent(
        model,
        Guard,
        (
            'Accept clean, thoughtful posts (reply Accept with the cleaned text). '
            'Reject spam, scams, or abusive pitches (reply Reject with a short reason).'
        ),
        GATE,
    )
    return [_feed(GATE, post), guard]


def build_pipeline(material: str) -> list[pa.Participant]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    strict = pa.Repair(attempts=2)
    writer = pa.Agent(
        model,
        Writer,
        'Turn the post into a short two-speaker Dialogue (plain text).',
        PIPELINE,
    )
    formatter = pa.Agent(
        model,
        Formatter,
        (
            'Format the dialogue as a Screenplay in plain text. '
            'Do not use parentheses anywhere (no stage directions).'
        ),
        PIPELINE,
        repair=strict,
    )
    scorer = pa.Agent(
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

    spam = pa.AgentRuntime(GATE, build_gate('BUY CHEAP PILLS NOW!!!')).run_sync()
    report.conversation(spam, title='spam — Reject stops before PIPELINE')

    material = 'A quiet walk under the old bridge.'
    clean_gate = pa.AgentRuntime(GATE, build_gate(material)).run_sync()
    report.conversation(clean_gate, title='clean — Accept, then PIPELINE')
    clean_pipe = pa.AgentRuntime(PIPELINE, build_pipeline(material)).run_sync()
    report.conversation(clean_pipe, title='pipeline run')


if __name__ == '__main__':
    main()
