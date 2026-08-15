# Start (/docs/tutorials/coding-harness/start)

Build a coding harness that accepts a task in the terminal, inspects a working
directory, edits files, and submits the result for one review. The finished
program follows the same design as
[`examples/coding_agent.py`](https://github.com/qnbhd/agentsparty/blob/master/examples/coding_agent.py).

The harness has five participants:

- `Client` enters the task and receives the result.
- `Planner` lists and reads files, then sends an implementation plan.
- `Coder` writes files and reports the patch.
- `Reviewer` either ships the patch or requests one final correction.
- `Workspace` exposes filesystem operations as protocol messages.

The session protocol determines which messages each participant can send. During
planning, the planner's endpoint contains `List`, `Read`, and `Ready`. The
`Write` branch belongs to the coder's endpoint, and the planner cannot select
it.

## Prepare the script

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) and
create an empty file named `coding_agent.py`. Add inline metadata so `uv` can
select Python and install the OpenAI integration in an isolated environment:

```python compile
# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
```

Append the imports. `AsyncOpenAI` provides the model client; `agentsparty` supplies
roles, codecs, participants, and the runtime. The protocol combinators describe
the conversation as a value.

```python compile
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import alt, msg, project_all, rec, var
```

## Follow the control flow

The program moves through three phases:

1. The planner repeatedly selects `List` or `Read`. Selecting `Ready` closes
   exploration and publishes the plan.
2. The coder may issue any number of `Write` requests. Selecting `Done` sends
   the patch to the reviewer.
3. The reviewer selects `Ship` or `Fix`. A fix permits one final write, after
   which the coder delivers the result.

Both repeating phases are finite at runtime because the allowance bounds
recursive unfoldings. The protocol also makes the single-review policy visible
in the topology: neither review branch returns to the reviewer.

The next page builds this control flow with roles, typed messages, alternatives,
and recursion. Continue with
[declare the conversation](/docs/tutorials/coding-harness/declare-the-conversation).

