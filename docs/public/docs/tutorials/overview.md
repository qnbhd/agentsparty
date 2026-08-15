# A coding-agent harness (/docs/tutorials/overview)

# A coding-agent harness

This tutorial builds a small coding agent in `agentsparty`. The protocol is the
control: a client commissions a task; a planner may only list and read
inside a given directory; a coder writes; a reviewer takes one step; then
a result comes out. Write tools are unrepresentable during planning — not
because the prompt says so, but because the planner's local type does not
offer them.

The finished program is `examples/coding_agent.py`. The next two pages
construct that same session from scratch:
[declare the conversation](/docs/tutorials/declare-the-conversation), then
[bind the roles and run](/docs/tutorials/bind-and-run).

When the harness runs, `Client` uses `CliHumanIo`: enter the `Task` branch
and its text in the terminal. The task is not a Python constant and is not
sent as a second shell command after the process exits.

## The phases

1. **Plan.** The planner talks to a workspace role. The offered labels are
   `List`, `Read`, and `Ready`. There is no `Write`.
2. **Implement.** The coder receives the plan and may `Write`, then `Done`.
3. **Review once.** The reviewer sends `Ship`, or one `Fix`. After either
   label the reviewer is finished — there is no loop back into review.
4. **Result.** The coder delivers to the client.

Silent roles hear a distinct label on the loop versus the exit of each
`rec`. That is [knowledge of alt](/docs/concepts/knowledge-of-alt): a role
whose future changes has to observe the branch.

## The shipped protocol

`render` prints the conversation before anyone is bound. `duties` lists
what each role may author. The planner's duties include `List` and `Read`
and do not include `Write`.

```python exec
import runpy

from agentsparty.protocol import project, render
from agentsparty.protocol.analysis import duties

shipped = runpy.run_path('examples/coding_agent.py')
protocol = shipped['protocol']
print(render(protocol).splitlines()[0])
planner = project(protocol, shipped['Planner'])
print(sorted({duty.label.name for duty in duties(planner)}))
```

```text
Client -> Planner : Task(str) :: 'The coding task in one sentence.'
['List', 'Looking', 'Outline', 'Plan', 'Read', 'Ready']
```

The reviewer authors only `Ship` and `Fix`. After either choice the
endpoint is `end`.

```python exec
import runpy

from agentsparty.protocol import project
from agentsparty.protocol.analysis import duties
from agentsparty.protocol.language.endpoint import EndpointEnd, EndpointSelect

shipped = runpy.run_path('examples/coding_agent.py')
reviewer = project(shipped['protocol'], shipped['Reviewer'])
print(sorted({duty.label.name for duty in duties(reviewer)}))
```

[Combinators](/docs/concepts/combinators) and
[participants and roles](/docs/concepts/participants-and-roles) are the
background. Next: write the session type.
