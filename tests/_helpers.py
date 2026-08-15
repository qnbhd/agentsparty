"""Shared test inputs and protocol fixtures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from hypothesis import strategies as st

from agentsparty.kernel.role import Role, roles
from agentsparty.llm import Answer, ModelId, StructuredRequest, Usage
from agentsparty.participant import Cancelled, Envelope
from agentsparty.protocol import Label, alt, case, rec, var
from agentsparty.protocol.language.core import Chosen, RawValue
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.protocol.session import SessionType

RAW_BY_CODEC: dict[str, RawValue] = {
    'undefined': None,
    'null': None,
    'str': 'x',
    'int': 1,
    'float': 1.5,
    'bool': True,
}


def first_alt_json(schema: dict[str, object]) -> str:
    """Return a valid selection answer for the first offered arm."""
    root = cast(dict[str, Any], schema)
    alt_schema = cast(dict[str, Any], root['properties']['alt'])
    arm = cast(dict[str, Any], alt_schema['anyOf'][0]) if 'anyOf' in alt_schema else alt_schema
    label = arm['properties']['label']['enum'][0]
    payload_type = arm['properties']['payload'].get('type')
    payload = {
        'null': None,
        'string': 'x',
        'integer': 1,
        'number': 1.5,
        'boolean': True,
    }.get(payload_type)
    return json.dumps({'alt': {'label': label, 'payload': payload}})


def loop_protocol() -> SessionType:
    """Return the two-role protocol used by recursion tests."""
    A, B = roles('A', 'B')
    return rec(
        't',
        alt[A, B](
            case('loop') >> var('t'),
            case('done'),
        ),
    ).close()


def cancellable_envelopes():
    """Generate arbitrary envelopes for cancellation tests."""
    return st.lists(
        st.builds(
            Envelope,
            sender=st.just(roles('A')[0]),
            receiver=st.just(roles('B')[0]),
            label=st.builds(Label, st.sampled_from(['Hi', 'Bye', 'Done'])),
            payload=st.text(),
        ),
    )


@dataclass
class DeterministicPeer:
    """Participant that chooses the smallest label with a codec payload."""

    role: Role
    endpoint_contract: EndpointType
    selects: int = 0
    received: list[Envelope] = field(default_factory=list)
    recalled: list[Envelope] = field(default_factory=list)
    cancelled: list[Cancelled] = field(default_factory=list)

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        self.selects += 1
        branch = min(branches.values(), key=lambda candidate: candidate.label)
        raw = RAW_BY_CODEC[branch.payload.name]
        return Chosen(branch=branch, payload=branch.payload.decode(raw), raw=raw)

    async def offer(self, envelope: Envelope) -> None:
        self.received.append(envelope)

    async def recall(self, envelope: Envelope) -> None:
        self.recalled.append(envelope)

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled.append(notice)


@dataclass
class ScriptedModel:
    """Model that returns a valid alt for the first offered arm."""

    requests: list[StructuredRequest] = field(default_factory=list)

    async def complete(self, request: StructuredRequest) -> Answer:
        self.requests.append(request)
        return Answer(first_alt_json(request.schema), ModelId('stub', 'v1'))


@dataclass
class ReplyingModel:
    """Model that returns the same raw reply for every request."""

    reply: str
    requests: list[StructuredRequest] = field(default_factory=list)

    async def complete(self, request: StructuredRequest) -> Answer:
        self.requests.append(request)
        return Answer(self.reply, ModelId('stub', 'v1'))


@st.composite
def usage_values(draw: st.DrawFn) -> Usage:
    """Generate usage values with valid cached-token bounds."""
    input_tokens = draw(st.integers(0, 100))
    output_tokens = draw(st.integers(0, 100))
    return Usage(
        input_tokens,
        output_tokens,
        draw(st.integers(0, input_tokens)),
        draw(st.integers(0, output_tokens)),
    )
