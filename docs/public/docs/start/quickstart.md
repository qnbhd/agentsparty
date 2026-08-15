# Quickstart (/docs/start/quickstart)

# Quickstart

## Install from PyPI

Install agentsparty with its OpenAI dependency, then provide an API key:

```bash
pip install 'agentsparty[openai]'
export OPENAI_API_KEY=...
```

## Define the protocol

The protocol permits one typed message from `Writer` to `Reader`:

```python compile
import agentsparty as pa

Writer, Reader = pa.roles('Writer', 'Reader')
Note = pa.Text('Note')
protocol = pa.protocol.msg[Writer, Reader](Note)

print(pa.protocol.render(protocol))
```

The output describes the complete session before any participant runs:

```text
Writer -> Reader : Note(str)
end
```

## Bind participants and run

Create an OpenAI client, assign an agent to each role, and pass both
participants to `AgentRuntime`:

```python compile
import asyncio

from openai import AsyncOpenAI
import agentsparty as pa

Writer, Reader = pa.roles('Writer', 'Reader')
Note = pa.Text('Note')
protocol = pa.protocol.msg[Writer, Reader](Note)

model = pa.OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0, timeout=30.0))
writer = pa.Agent(model, Writer, 'Send a concise note.', protocol)
reader = pa.Agent(model, Reader, 'Receive the note.', protocol)


async def main() -> None:
    trace = await pa.AgentRuntime(protocol, [writer, reader]).run()
    envelope = trace[0]
    print(
        f'{envelope.sender.name} -> {envelope.receiver.name}: '
        f'{envelope.label}({envelope.payload!r})'
    )


asyncio.run(main())
```

`AgentRuntime` projects the protocol for each role and checks that every role
has exactly one participant. The writer generates the `Note` payload; the
reader receives the resulting typed envelope.

## Continue

- [Core Concepts](/docs/concepts/protocol-first) covers session types,
  combinators, projection, and the rest of the conversation.
- [Tutorials](/docs/tutorials/coding-harness/start) build a coding-agent harness from scratch.

