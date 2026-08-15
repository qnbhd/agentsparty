# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty[openai]"]
# ///
"""Support-triage protocol: classify, search, draft, then ship or escalate."""

from __future__ import annotations

import agentsparty as ap
from agentsparty.human import HumanIo
from agentsparty.protocol import Case, RawValue, project_all

Intake, Classifier, KB, Responder, Approver = ap.roles(
    'Intake',
    'Classifier',
    'KB',
    'Responder',
    'Approver',
)

Ticket = ap.record('Ticket', text=str, customer_tier=str)(
    'Ticket',
    'Customer message and support tier.',
)
Search = ap.Text('Search', 'A short query for the knowledge base.')
Hits = ap.Text.many()('Hits', 'Matching knowledge-base articles.')

Severity = ap.Integer.where('severity_1_to_5', lambda n: 1 <= n <= 5)
Billing = Severity('Billing', 'Billing issue, severity 1 (low) to 5 (critical).')
Technical = Severity('Technical', 'Technical issue, severity 1 to 5.')
Refund = Severity('Refund', 'Refund request, severity 1 to 5.')
Spam = ap.Nothing('Spam', 'Not a real support request.')

OnBilling = ap.Nothing('OnBilling', 'This ticket is a billing case.')
OnTechnical = ap.Nothing('OnTechnical', 'This ticket is a technical case.')
OnRefund = ap.Nothing('OnRefund', 'This ticket is a refund case.')

Draft = ap.record('Draft', subject=str, body=str)(
    'Draft',
    'A reply the customer can receive.',
)
Ship = ap.Nothing('Ship', 'Send the draft to the customer.')
Escalate = ap.Text('Escalate', 'Why a human should take this ticket.')
Shipped = ap.Nothing('Shipped', 'The draft was sent.')
Escalated = ap.Nothing('Escalated', 'A human will take this ticket.')
Close = ap.Nothing('Close', 'Close the ticket as spam.')

ARTICLES: dict[str, tuple[str, ...]] = {
    'billing': (
        'Invoices go out on the first of each month in the billing portal.',
        'A failed charge is retried three times, then the workspace pauses.',
        'Enterprise accounts can request a custom invoice from billing@.',
    ),
    'technical': (
        'SSO is SAML 2.0; send the metadata URL to support to enable it.',
        'API 429s include Retry-After; the published ceiling is 120 req/min.',
        'Webhook signatures use HMAC-SHA256 over the raw request body.',
    ),
    'refund': (
        'Monthly plans refund unused full days within 14 days of the charge.',
        'Annual plans convert unused months to credit, not cash, after day 14.',
        'Refunds post to the original payment method within five business days.',
    ),
}


def _handled(c: ap.Chor, notice: Case) -> None:
    c.say(Responder, Intake, notice)
    c.say(Responder, Approver, notice)
    c.say(Responder, Approver, Draft)
    with c.decide(Approver, Responder) as verdict:
        with verdict.case(Ship):
            c.say(Responder, Intake, Shipped)
        with verdict.case(Escalate):
            c.say(Responder, Intake, Escalated)


@ap.choreography
def triage(c: ap.Chor) -> None:
    c.say(Intake, Classifier, Ticket)
    c.say(Intake, Responder, Ticket)
    c.say(Classifier, KB, Search)
    c.say(KB, Classifier, Hits)
    with c.decide(Classifier, Responder) as verdict:
        with verdict.case(Billing):
            _handled(c, OnBilling)
        with verdict.case(Technical):
            _handled(c, OnTechnical)
        with verdict.case(Refund):
            _handled(c, OnRefund)
        with verdict.case(Spam):
            c.say(Responder, Intake, Close)
            c.say(Responder, Approver, Close)


protocol = triage()

project_all(protocol)

CATEGORIES = frozenset({'Billing', 'Technical', 'Refund', 'Spam'})
OUTCOMES = frozenset({'Shipped', 'Escalated', 'Close'})


def _words(query: str) -> list[str]:
    return [word for word in query.lower().split() if len(word) > 2]


def _matches(query: str) -> list[str]:
    needles = _words(query)
    found = [
        article
        for articles in ARTICLES.values()
        for article in articles
        if any(word in article.lower() for word in needles)
    ]
    return found[:4] or ['No article matched; ask the customer for one clarifying detail.']


async def search(query: str) -> ap.Choice:
    hits: list[RawValue] = list(_matches(query))
    return ap.reply(Hits, hits)


def build_participants(
    model: ap.LanguageModel,
    ticket: dict[str, RawValue],
    approver_io: HumanIo,
) -> list[ap.Participant]:
    """Bind one ticket to the five protocol roles."""
    strict = ap.Repair(attempts=2)
    intake = ap.Human(
        Intake,
        protocol,
        ap.ScriptedHumanIo([ap.says(Ticket, ticket), ap.says(Ticket, ticket)]),
    )
    classifier = ap.Agent(
        model,
        Classifier,
        (
            'Search the knowledge base with a short query, then classify. '
            'Pick Billing, Technical, Refund, or Spam. '
            'Severity is an integer from 1 to 5 (5 is critical). '
            'Spam carries no severity.'
        ),
        protocol,
        repair=strict,
    )
    responder = ap.Agent(
        model,
        Responder,
        (
            'You already have the ticket. After a category arrives: '
            'notify Intake and Approver, then write Draft as '
            "{'subject': str, 'body': str} — short, specific, kind. "
            'On Ship, acknowledge Shipped. On Escalate, acknowledge Escalated. '
            'On Spam, send Close to Intake and Approver. Do not invent policy.'
        ),
        protocol,
        repair=strict,
    )
    return [
        intake,
        classifier,
        responder,
        ap.Human(Approver, protocol, approver_io),
        ap.Toolbox(KB, protocol, [ap.tool_for(Search, search)]),
    ]
