<p align="center">
  <img src="https://raw.githubusercontent.com/qnbhd/agentsparty/master/assets/par.light.png" width="280" alt="agentsparty">
</p>

<p align="center">
  <strong>Protocol-first orchestration for AI agents.</strong><br>
  <em>Declarative multiparty session protocols for AI agents</em>
</p>

Inspired by Multiparty Session Types (MPST), this project focuses on
declarative session protocols for AI agents; it is a practical protocol-oriented
experiment, not a claim to implement MPST as a type system.

## What it is

You describe one typed global choreography between named roles. `agentsparty`
projects it onto every role, rejects the choreographies a role could not
follow, and runs the session. A language model fills a typed payload or picks a
declared branch — it does **not** route the workflow, invent roles, or call
arbitrary code. The protocol owns control; the model owns content.

## Install

```bash
pip install agentsparty
pip install "agentsparty[openai]"   # optional OpenAI Responses backend
```

## A session, end to end

Three roles, one branch point: a Writer drafts a note, a Reviewer either
approves or rejects it, and a Reader receives the final text either way. The
protocol is stated once; `Cast` binds each role to whoever plays it.

```python
from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import alt, msg

Writer, Reviewer, Reader = ap.roles('Writer', 'Reviewer', 'Reader')

protocol = (
    msg[Writer, Reviewer]('Draft')
    >> alt[Reviewer, Writer](
        ap.Nothing('Approve') >> msg[Writer, Reader]('Final'),
        ap.Nothing('Reject') >> msg[Writer, Reader]('Final'),
    )
).close()

model = ap.OpenAIModel('gpt-5.6-luna', AsyncOpenAI(timeout=30.0))

report = debug.Report()
report.protocol(protocol)
report.conversation(
    ap.Cast(protocol)
    .play(Writer, ap.agent(model, 'Write a one-sentence draft note.'))
    .play(Reviewer, ap.agent(model, 'Approve or Reject the draft.'))
    .play(Reader, ap.human(ap.script()))
    .run_sync(),
)
```

A message carries `str` unless you say otherwise, so `msg[Writer, Reviewer]('Draft')`
is the whole declaration; richer payloads take a codec as the second argument.

A sample run — the protocol section is fixed by the declaration above, the
quoted text is whatever the model wrote:

```
=== protocol ===
Writer -> Reviewer : Draft(str)
Reviewer -> Writer {
  Approve():
    Writer -> Reader : Final(str)
    end
  Reject():
    Writer -> Reader : Final(str)
    end
}
=== conversation ===
Writer:Draft -> Reviewer 'Ship the typed choreography first.'
Reviewer:Approve -> Writer
Writer:Final -> Reader 'Ship the typed choreography first.'
```

Two things are worth noting. The Reviewer never returns free-form prose that
someone has to parse: it selects `Approve` or `Reject`, and nothing else is
representable. And the Reader is a `human`, not an agent — swapping who plays a
role does not touch the protocol.

The same session, as a runnable file, is
[`examples/online/quickstart.py`](examples/online/quickstart.py):

```bash
export OPENAI_API_KEY=...
uv run python examples/online/quickstart.py
```

## What it refuses to run

The same declarative surface rejects a choreography that cannot be carried out
by the roles it names — **before** the first model call. Here `C` is required
to send on one branch and to receive on the other, yet `C` is never told which
branch was taken:

```python
import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import alt, msg, project

A, B, C = ap.roles('A', 'B', 'C')

broken = alt[A, B](
    ap.Nothing('Yes') >> msg[A, C]('Y'),
    ap.Nothing('No') >> msg[C, A]('N'),
).close()

report = debug.Report()
report.protocol(broken)
with report.refusing(ap.ProjectionError, title='project'):
    project(broken, C)
report.note('no model was called', title='result')
```

Projection fails, and the error names the role, both branches, and the fix:

```
=== project ===
ProjectionError: role 'C' cannot tell the branches of the alt A -> B apart:
  on 'No' it must send N to A (as C), on 'Yes' it must receive Y from A (as C).
A role that behaves differently per branch must be told which branch was taken — add a message from A (or B) to C inside each branch.
```

No API key and no network are needed to see this:

```bash
uv run python examples/offline/projection_error.py
```

The full ladder of examples, from a two-message session to a coding harness, is
in [examples/README.md](examples/README.md).

## When to use — and when not to

**Use when**

- the allowed interaction shape is known up front
- every role must only act on messages it actually receives
- you need projection to fail closed before the first model call
- tools are roles with a protocol surface, not free function-calling
- sessions must resume from recorded decisions without re-asking

**Do not use when**

- one agent with a free tool set is enough (use a simpler agent SDK)
- the route must be discovered at run time by the model
- you need a large catalogue of vendor integrations out of the box
- you require a stable API before 1.0 (this project is research / 0.x)
- you need multi-process or multi-machine transport (the runtime is in-process)

## Links

- [Documentation](https://qnbhd.github.io/agentsparty/)
- [Examples](examples/README.md)
- [Protocol-first and projection](docs/content/docs/concepts/protocol-first.mdx)
- [A very gentle introduction to Multiparty Session Types](https://dl.acm.org/doi/10.1007/978-3-030-36987-3_5)
- [Global Types for Agent Interaction Protocols](https://dl.acm.org/doi/10.1145/3586031)
- [Security](docs/content/docs/start/security.mdx)
- [Contributing](CONTRIBUTING.md)

## Status

Research framework at `0.1.x`. What agentsparty proves, checks at run time, and
deliberately leaves to the application — including the non-guarantees (no
deadlock-freedom, no liveness, no exactly-once) — is set out in the
[guarantee table](docs/content/docs/start/what-you-can-rely-on.mdx). The public
surface is the union of the tier-1/2 `__all__` exports; see
[`tests/public_api.txt`](tests/public_api.txt).
Exception *types* are stable; message text and journal formats are not.

## Security

Untrusted payloads and web content are data, not instructions. User-written
tools run with the privileges of the host process — sandbox them, and validate
paths or commands before any effect. Give `AsyncOpenAI` a finite transport
timeout (the model wrapper does not add one). `Deadline`, `Allowance`, and
`Metered` bound branch windows, protocol steps, and token spend. Journals and
tracers persist payloads and model output in plaintext.

Private reports: [SECURITY.md](SECURITY.md). Guidance:
[security](docs/content/docs/start/security.mdx).

## Development

```bash
uv sync --all-groups
just all    # or: uv run nox -t ci
```

Agent conventions for contributors live in `AGENTS.md`.

## License

MIT — see [LICENSE](LICENSE).
