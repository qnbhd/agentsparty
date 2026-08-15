# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]", "msgspec>=0.19"]
# ///
"""Analyse a ticker from typed filings and arithmetic, then buy/hold/avoid.

What you will see (sample run):
  === protocol ===
  Investor -> Analyst : Ticker(str)
  Analyst -> Filings : Annual(str)
  Filings -> Analyst : Filing(Filing)
  ...
  Advisor -> Investor {
    Buy(str): end
    Hold(str): end
    Avoid(str): end
  }
  === conversation ===
  Investor:Ticker -> Analyst 'AMZN'
  Analyst:Annual -> Filings 'AMZN'
  Filings:Filing -> Analyst Filing(form='10-K', ...)
  ...
  Analyst:Analysis -> Advisor '...'
  Advisor:Hold -> Investor '...'

Run::

    export OPENAI_API_KEY=...
    uv run python examples/online/stock_analysis.py
"""

from __future__ import annotations

import os
from typing import Any

import msgspec
from openai import AsyncOpenAI

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import (
    SessionType,
    alt,
    msg,
    project_all,
    seq,
)

Investor, Analyst, Advisor, Filings, Arithmetic = pa.roles(
    'Investor',
    'Analyst',
    'Advisor',
    'Filings',
    'Arithmetic',
)


class Filing(msgspec.Struct, frozen=True):
    form: str
    period: str
    revenue: float
    net_income: float


# msgspec.json.schema emits $ref/$defs; providers disagree on $ref, so flatten.
_raw_schema = msgspec.json.schema(Filing)
if '$ref' in _raw_schema or '$defs' in _raw_schema:
    _refs, _components = msgspec.json.schema_components([Filing])
    FILING_SCHEMA = dict(_components['Filing'])
else:
    FILING_SCHEMA = dict(_raw_schema)

FILING = pa.json_model(
    'Filing',
    FILING_SCHEMA,
    lambda text: msgspec.json.decode(text.encode(), type=Filing),
)


FilingCase = FILING('Filing', 'The quarterly filing on file.')
Annual = pa.Text('Annual', 'Ticker whose 10-K is wanted.')
Quarterly = pa.Text('Quarterly', 'Ticker whose 10-Q is wanted.')
Total = pa.Number('Total', 'The sum of the figures.')
Sum = pa.Number.many()('Sum', 'Figures to add up.')
Analysis = pa.Text('Analysis', 'What the filings say.')
Buy = pa.Text('Buy', 'Why the position is worth taking.')
Hold = pa.Text('Hold', 'Why nothing should change.')
Avoid = pa.Text('Avoid', 'Why the position is not worth taking.')
Ticker = pa.Text('Ticker', 'The company to analyse.')

protocol = seq(
    msg[Investor, Analyst](Ticker),
    msg[Analyst, Filings](Annual),
    msg[Filings, Analyst](FilingCase),
    msg[Analyst, Filings](Quarterly),
    msg[Filings, Analyst](FilingCase),
    msg[Analyst, Arithmetic](Sum),
    msg[Arithmetic, Analyst](Total),
    msg[Analyst, Advisor](Analysis),
    alt[Advisor, Investor](
        Buy,
        Hold,
        Avoid,
    ),
).close()

ANNUAL = {
    'form': '10-K',
    'period': '2024',
    'revenue': 100.0,
    'net_income': 12.0,
}
QUARTERLY = {
    'form': '10-Q',
    'period': '2025-Q1',
    'revenue': 28.0,
    'net_income': 3.5,
}


def _filings_tools() -> list[Any]:
    async def annual(_ticker: str) -> pa.Choice:
        return pa.reply(FilingCase, dict(ANNUAL))

    async def quarterly(_ticker: str) -> pa.Choice:
        return pa.reply(FilingCase, dict(QUARTERLY))

    return [
        pa.tool_for(Annual, annual),
        pa.tool_for(Quarterly, quarterly),
    ]


def _arithmetic_tools() -> list[Any]:
    async def total(figures: list[float]) -> pa.Choice:
        return pa.reply(Total, sum(figures))

    return [pa.tool_for(Sum, total)]


def build() -> tuple[SessionType, list[pa.Participant]]:
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        max_retries=0,
        timeout=30.0,
    )
    model = pa.OpenAIModel('gpt-5.6-luna', client)
    analyst = pa.Agent(
        model,
        Analyst,
        (
            'For the ticker: request Annual then Quarterly filings, '
            'Sum a short list of numeric figures from those filings, '
            'then write a one-sentence Analysis.'
        ),
        protocol,
    )
    advisor = pa.Agent(
        model,
        Advisor,
        'Recommend Buy, Hold, or Avoid with one short reason string.',
        protocol,
    )
    investor = pa.Human(
        Investor,
        protocol,
        pa.ScriptedHumanIo([pa.says(Ticker, 'AMZN')]),
    )
    participants: list[pa.Participant] = [
        investor,
        analyst,
        advisor,
        pa.Toolbox(Filings, protocol, _filings_tools()),
        pa.Toolbox(Arithmetic, protocol, _arithmetic_tools()),
    ]
    return protocol, participants


def main() -> None:
    project_all(protocol)
    report = debug.Report()
    report.protocol(protocol)
    _, participants = build()
    report.conversation(pa.AgentRuntime(protocol, participants).run_sync())


if __name__ == '__main__':
    main()
