from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest
from pydantic import BaseModel

from agentsparty.agent import Agent
from agentsparty.human import Human, ScriptedHumanIo
from agentsparty.kernel.errors import PayloadError, SelectionError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role, roles
from agentsparty.participant import Cancelled, Choice, Envelope
from agentsparty.protocol import (
    Integer,
    Label,
    Nothing,
    Text,
    alt,
    case,
    json_model,
    list_of,
    msg,
    project,
)
from agentsparty.protocol.language.core import Chosen
from agentsparty.protocol.language.endpoint import EndpointType
from agentsparty.runtime import AgentRuntime
from tests._helpers import ReplyingModel


@dataclass
class StubParticipant:
    role: Role
    endpoint_contract: EndpointType
    alts: list[Choice] = field(default_factory=list)
    received: list[Envelope] = field(default_factory=list)
    recalled: list[Envelope] = field(default_factory=list)
    cancelled: list[Cancelled] = field(default_factory=list)

    async def select(self, receiver: Role, branches: Mapping) -> Chosen:
        if not self.alts:
            raise RuntimeError(f'{self.role.name}: no scripted alts left')
        scripted = self.alts.pop(0)
        branch = branches[scripted.label]
        return Chosen(branch=branch, payload=scripted.payload, raw=scripted.payload)

    async def offer(self, envelope: Envelope) -> None:
        self.received.append(envelope)

    async def recall(self, envelope: Envelope) -> None:
        self.recalled.append(envelope)

    async def cancel(self, notice: Cancelled) -> None:
        self.cancelled.append(notice)


def _trade_protocol():
    Buyer, Seller, Bank = roles('Buyer', 'Seller', 'Bank')
    proto = (
        msg[Buyer, Seller]('Order', Text)
        >> msg[Seller, Buyer]('Quote', Integer)
        >> alt[Buyer, Seller](
            case('Accept', Integer)
            >> msg[Seller, Bank]('Charge', Integer)
            >> msg[Bank, Buyer]('Receipt', Text),
            case('Reject') >> msg[Seller, Bank]('Cancel'),
        )
    ).close()
    return Buyer, Seller, Bank, proto


def test_codec_decode_primitives() -> None:
    assert Nothing.decode(None) is None
    assert Text.decode('hi') == 'hi'
    assert Integer.decode('42') == 42
    assert list_of(Text).decode('["one", "two"]') == ['one', 'two']


def test_codec_rejects_bad_int() -> None:
    try:
        Integer.decode('nope')
    except PayloadError:
        return
    raise AssertionError('expected PayloadError')


def test_json_model_codec() -> None:
    class Item(BaseModel):
        sku: str
        qty: int

    codec = json_model(
        'Item',
        Item.model_json_schema(),
        Item.model_validate_json,
    )
    assert codec.decode({'sku': 'x', 'qty': 2}) == Item(sku='x', qty=2)
    assert dict(codec.schema) == Item.model_json_schema()


def test_runtime_missing_role() -> None:
    Buyer, Seller, _Bank, proto = _trade_protocol()
    buyer = StubParticipant(Buyer, project(proto, Buyer))
    seller = StubParticipant(Seller, project(proto, Seller))
    with pytest.raises(ValueError, match='Bank'):
        AgentRuntime(proto, [buyer, seller])


def test_runtime_duplicate_role() -> None:
    Buyer, Seller, Bank, proto = _trade_protocol()
    a = StubParticipant(Buyer, project(proto, Buyer))
    b = StubParticipant(Buyer, project(proto, Buyer))
    c = StubParticipant(Seller, project(proto, Seller))
    d = StubParticipant(Bank, project(proto, Bank))
    with pytest.raises(ValueError, match='duplicate'):
        AgentRuntime(proto, [a, b, c, d])


async def test_session_accept_trace() -> None:
    Buyer, Seller, Bank, proto = _trade_protocol()

    buyer_io = ScriptedHumanIo(
        [
            Choice(Label('Order'), 'widget'),
            Choice(Label('Accept'), 10),
        ],
    )
    buyer = Human(Buyer, proto, buyer_io)
    seller = StubParticipant(
        Seller,
        project(proto, Seller),
        alts=[
            Choice(Label('Quote'), 10),
            Choice(Label('Charge'), 10),
        ],
    )
    bank = StubParticipant(
        Bank,
        project(proto, Bank),
        alts=[Choice(Label('Receipt'), 'ok-10')],
    )

    runtime = AgentRuntime(proto, [buyer, seller, bank])
    trace = await runtime.run()

    labels = [str(e.label) for e in trace]
    assert labels == ['Order', 'Quote', 'Accept', 'Charge', 'Receipt']
    assert trace[0].payload == 'widget'
    assert trace[2].payload == 10
    assert trace[-1].payload == 'ok-10'
    assert len(buyer_io.notifications) == 2


async def test_scripted_human_wrong_label() -> None:
    from agentsparty.protocol.language.endpoint import EndpointBranchCase, EndpointEnd

    Buyer, Seller, _Bank, proto = _trade_protocol()
    buyer_io = ScriptedHumanIo([Choice(Label('Nope'), None)])
    buyer = Human(Buyer, proto, buyer_io)
    branches = NonEmptyMap(
        {Label('Order'): EndpointBranchCase(Label('Order'), Text, EndpointEnd())},
    )
    try:
        await buyer.select(Seller, branches)
    except SelectionError:
        return
    raise AssertionError('expected SelectionError')


def _agent(model: ReplyingModel) -> Agent[object]:
    Buyer, _Seller, _Bank, proto = _trade_protocol()
    return Agent(model=model, role=Buyer, instructions='test', proto=proto)


async def test_agent_run_parses_json_schema_response() -> None:
    model = ReplyingModel('["one", "two"]')
    agent = _agent(model)
    codec = list_of(Text)
    assert await agent.run('say hello', output_type=codec) == ['one', 'two']
    assert model.requests[0].schema_name == 'agent_output'
    assert model.requests[0].schema == {'type': 'array', 'items': {'type': 'string'}}
    # run is not a protocol act, so it leaves no brief memory:
    assert agent.messages == []


async def test_agent_run_uses_json_model() -> None:
    class Item(BaseModel):
        name: str

    codec = json_model(
        'Item',
        Item.model_json_schema(),
        Item.model_validate_json,
    )
    model = ReplyingModel('{"name": "widget"}')
    agent = _agent(model)
    assert await agent.run('name it', output_type=codec) == Item(name='widget')
    assert model.requests[0].schema == Item.model_json_schema()
