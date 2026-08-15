<p align="center">
  <img src="https://raw.githubusercontent.com/qnbhd/agentsparty/master/assets/par.light.png" width="280" alt="agentsparty">
</p>

<p align="center">
  <strong>Protocol-first orchestration for AI agents.</strong><br>
  <em>Declarative multiparty session types for AI agents</em>
</p>

## What it is

You describe one typed global choreography between named roles. `agentsparty`
projects it onto every role, rejects alts a role cannot observe, and runs
the session. A language model fills a typed payload or picks a declared
branch — it does **not** route the workflow, invent roles, or call arbitrary
code. The protocol owns control; the model owns content.

## What it catches

A role that must behave differently on two branches of a alt it never saw
fails **before** any model call:

```python
>>> from agentsparty.kernel.errors import ProjectionError
>>> from agentsparty import Nothing, Text
>>> from agentsparty.protocol import alt, msg, project
>>> from agentsparty.kernel.role import roles
>>> A, B, C = roles("A", "B", "C")
>>> broken = alt[A, B] (
...     Nothing("Yes") >> msg[A, C] ("Y", Text),
...     Nothing("No") >> msg[C, A] ("N", Text),
... ).close()
>>> try:
...     project(broken, C)
... except ProjectionError as err:
...     print("role" in str(err).lower() and "Yes" in str(err))
True

```

## Install

```bash
pip install agentsparty
pip install "agentsparty[openai]"   # optional OpenAI Responses backend
```

## Quickstart

Minimal agent session with the OpenAI `gpt-5.6-luna` model:

```python compile
import asyncio

from openai import AsyncOpenAI

from agentsparty.agent import Agent
from agentsparty.human import Human, ScriptedHumanIo
from agentsparty import OpenAIModel
from agentsparty import Text
from agentsparty.protocol import msg, render
from agentsparty.kernel.role import roles
from agentsparty.runtime import AgentRuntime

A, B = roles('Writer', 'Reader')
proto = msg[A, B]('Note', Text).close()
print(render(proto))
model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
writer = Agent(model, A, 'send a short note', proto)
reader = Human(B, proto, ScriptedHumanIo([]))


async def main() -> None:
    trace = await AgentRuntime(proto, [writer, reader]).run()
    print(trace[0].payload)


asyncio.run(main())

```

## Examples — live in 10 seconds

```bash
export OPENAI_API_KEY=...
pip install 'agentsparty[openai]'
uv run python examples/online/hello.py
```

Sample output:

```
=== protocol ===
Writer -> Reviewer : Note(str)
Reviewer -> Writer : Ack(str)
end
=== conversation ===
Writer:Note -> Reviewer 'Ship the typed choreography first.'
Reviewer:Ack -> Writer 'Received.'
```

Catch a projection error without a key: `uv run python examples/offline/projection_error.py`.
Full ladder: [examples/README.md](examples/README.md).

## When to use — and when not to

**Use when**

- the allowed interaction shape is known up front
- every role must only act on messages it actually receives
- you need projection to fail closed before the first model call
- tools are roles with a protocol surface, not free function-calling
- sessions must resume from recorded decisions without re-asking

**Do not use when**

- one agent with a free tool set is enough (use a simpler agent SDK)
- the route must be discovered at runtime by the model
- you need a large catalogue of vendor integrations out of the box
- you require a stable API before 1.0 (this project is research / 0.x)
- you need multi-process or multi-machine transport (runtime is in-process)

## Links

- [Documentation](https://qnbhd.github.io/agentsparty/)
- [Examples](examples/README.md)
- [Protocol-first and projection](docs/content/docs/concepts/protocol-first.mdx)
- [Security](docs/content/docs/start/security.mdx)
- [Contributing](CONTRIBUTING.md)

## Status

Research framework at `0.1.x`. What agentsparty proves, checks at run time, and
deliberately leaves to the application — including the non-guarantees (no
deadlock-freedom, no liveness, no exactly-once) — is the
[guarantee table](docs/content/docs/start/what-you-can-rely-on.mdx). Public
surface is the union of tier-1/2 `__all__` exports; see
[`tests/public_api.txt`](tests/public_api.txt).
Exception *types* are stable; message text and journal formats are not.

## Security

Untrusted payloads and web content are data, not instructions. User-written
tools run with the host process privileges — sandbox them and validate paths
or commands before any effect. Give `AsyncOpenAI` a finite transport timeout
(the model wrapper does not add one). `Deadline`, `Allowance`, and `Metered`
bound branch windows, protocol steps, and token spend. Journals and tracers
persist payloads and model output in plaintext.

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
