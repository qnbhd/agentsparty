"""Allowance exhaustion names idle roles and points at starvation."""

from __future__ import annotations

import pytest

from agentsparty.kernel.budget import Allowance
from agentsparty.kernel.errors import RecursionLimitError
from agentsparty.kernel.role import roles
from agentsparty.participant import Choice
from agentsparty.protocol import Label, Nothing, Text, alt, case, msg, project, rec, var
from agentsparty.runtime import AgentRuntime
from tests.conftest import Stub


def _starving_protocol():
    """A loops with B; C participates only on the unused ``finish`` arm."""
    A, B, C = roles('A', 'B', 'C')
    proto = rec(
        't',
        alt[A, B](
            case('retry', Text) >> var('t'),
            case('finish', Nothing) >> msg[A, C]('Notify', Text),
        ),
    ).close()
    return proto, A, B, C


async def test_allowance_exhausted_names_idle_role_and_starvation() -> None:
    """When C never participates, the error names C and mentions starvation."""
    from agentsparty.protocol.language.endpoint import EndpointEnd

    proto, A, B, C = _starving_protocol()
    a = Stub(
        A,
        project(proto, A),
        alts=[Choice(Label('retry'), 'again')] * 40,
    )
    b = Stub(B, project(proto, B))
    # C only appears on the unselected arm; projection is undefined for C,
    # but C is still a bound protocol participant and stays idle in the trace.
    c = Stub(C, EndpointEnd())
    runtime = AgentRuntime(proto, [a, b, c], allowance=Allowance(unfoldings=2))
    with pytest.raises(RecursionLimitError) as caught:
        await runtime.run()
    message = str(caught.value)
    assert 'C' in message
    assert 'never sent or received' in message
    assert 'starved' in message.lower() or 'starvation' in message.lower()
    # Does not only say "raise the allowance" — starvation is the diagnosis.
    assert 'narrowed its alt' in message


async def test_allowance_without_idle_roles_keeps_budget_advice() -> None:
    """When every role has participated, only the budget message is raised."""
    A, B = roles('A', 'B')
    proto = rec(
        't',
        alt[A, B](case('loop') >> var('t'), case('done')),
    ).close()
    a = Stub(
        A,
        project(proto, A),
        alts=[Choice(Label('loop'), None)] * 40,
    )
    b = Stub(B, project(proto, B))
    runtime = AgentRuntime(proto, [a, b], allowance=Allowance(unfoldings=2))
    with pytest.raises(RecursionLimitError) as caught:
        await runtime.run()
    message = str(caught.value)
    assert 'never sent or received' not in message
    assert 'Allowance(unfoldings=None)' in message
