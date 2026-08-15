# Knowledge of alt (/docs/learn/knowledge-of-alt)

# 3 — Knowledge of alt

The Reviewer approves or rejects. The Reader has to publish in one case and
do nothing in the other. Nobody told the Reader which one happened — and in
most frameworks that is a runtime bug you find in production, three model
calls and forty cents later.

Here it is a `ProjectionError` before the first call.

## The blind protocol

```python exec
from agentsparty.kernel.errors import ProjectionError
from agentsparty.protocol import Nothing, Text, case, alt, msg, project
from agentsparty.kernel.role import roles

A, B, C = roles('A', 'B', 'C')
# C is not told which branch A selected, but each branch gives C a different duty.
broken = alt[A, B](
    Nothing('Yes') >> msg[A, C]('Y', Text),
    Nothing('No') >> msg[C, A]('N', Text),
).close()

try:
    # Projection catches the missing knowledge before a session can run.
    project(broken, C)
except ProjectionError as error:
    print(type(error).__name__)
```

<BrokenChoiceTreeDiagram />

Role C would need to receive on one branch and send on the other — without
any signal telling it which future it is in. `project` refuses:

```text
ProjectionError: role 'C' cannot tell the branches of the alt A -> B apart:
  on 'No' it must send N to A (as C), on 'Yes' it must receive Y from A (as C).
```

<ProjectionDiagnosisDiagram />

The instinct is to give C an endpoint that covers both — receive-or-send,
whichever comes. That is not a type, that is a coin flip: C would have to
guess which branch it is in before acting, and the guess is exactly the thing
the protocol was supposed to remove.

## Make the branch observable

The fix is to send a branch-specific message to every role whose continuation
differs. In the approval workflow, both outcomes come from the same Writer:
`Final` after approval, `Rejected` after rejection.

```python exec
from agentsparty.protocol import Nothing, Text, case, alt, msg, project_all, render
from agentsparty.kernel.role import roles

Writer, Reviewer, Reader = roles('Writer', 'Reviewer', 'Reader')
# Model the draft payload and the two possible review decisions.
Draft = Text('Draft')
ApproveLabel = Nothing('Approve')
RejectLabel = Nothing('Reject')
Approve = ApproveLabel >> msg[Writer, Reader](Text('Final'))
Reject = RejectLabel >> msg[Writer, Reader](Text('Rejected'))
# Reviewer selects a branch; Writer sends its branch-specific result to Reader.
protocol = msg[Writer, Reviewer](Draft) >> alt[Reviewer, Writer](
    Approve, Reject
)
print(render(protocol))
```

`Final` is inside the `Approve` branch and `Rejected` inside `Reject` — the
protocol is honest: a rejected draft does not claim to be final. Reader now
has one mergeable endpoint: it receives a message from Writer on either
branch.

```python exec
from agentsparty.protocol import Nothing, Text, case, alt, msg, project_all
from agentsparty.kernel.role import roles

Writer, Reviewer, Reader = roles('Writer', 'Reviewer', 'Reader')
Draft = Text('Draft')
ApproveLabel = Nothing('Approve')
RejectLabel = Nothing('Reject')
Approve = ApproveLabel >> msg[Writer, Reader](Text('Final'))
Reject = RejectLabel >> msg[Writer, Reader](Text('Rejected'))
protocol = msg[Writer, Reviewer](Draft) >> alt[Reviewer, Writer](
    Approve, Reject
)
# Projection derives a local contract for all three roles.
for role, endpoint in project_all(protocol):
    print(role.name)
    print(render(endpoint))
```

## Run the full workflow

```python compile
from openai import AsyncOpenAI

from agentsparty.agent import agent
from agentsparty.human import human, script
from agentsparty import OpenAIModel
from agentsparty.participant import says
from agentsparty.protocol import Nothing, Text, case, alt, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import Cast

Writer, Reviewer, Reader = roles('Writer', 'Reviewer', 'Reader')
Draft = Text('Draft')
ApproveLabel = Nothing('Approve')
RejectLabel = Nothing('Reject')
Approve = ApproveLabel >> msg[Writer, Reader](Text('Final'))
Reject = RejectLabel >> msg[Writer, Reader](Text('Rejected'))
protocol = msg[Writer, Reviewer](Draft) >> alt[Reviewer, Writer](
    Approve, Reject
)
model = OpenAIModel('gpt-5.6-luna', AsyncOpenAI(max_retries=0))
trace = (
    Cast(protocol)
    .play(Writer, agent(model, 'Draft then send the branch result.'))
    .play(Reviewer, human(script(says(ApproveLabel))))
    .play(Reader, human(script()))
    .run_sync()
)
assert [event.label.name for event in trace] == ['Draft', 'Approve', 'Final']
print([event.label.name for event in trace])
```

The model authors the two Writer selections; the Reviewer picks `Approve`;
the Reader receives the declared result. The whole file is
`docs/examples/tutorial/01_approval_workflow.py`.

Try the failure mode yourself: remove the `Rejected` message so only one
branch talks to the Reader. Projection raises — and that failure is useful,
because it points to a missing knowledge-of-alt edge before a live run can
spend tokens.

Next: [typed payloads](/docs/learn/typed-payloads).
