# Examples

Live agents are the default. Deterministic doubles live under `offline/` only
when the thesis needs replay, budgets, cancellation, or a projection refusal.

## Run in 10 seconds

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

Catch a type error **without** a model:

```bash
uv run python examples/offline/projection_error.py
```

```
=== protocol ===
A -> B {
  No():
    C -> A : N(str)
    end
  Yes():
    A -> C : Y(str)
    end
}
=== project ===
ProjectionError: role 'C' cannot tell the branches of the alt A -> B apart:
  ...
=== result ===
no model was called
```

## Environment

| Variable | Required | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | for live examples | — |

```bash
export OPENAI_API_KEY=...
pip install 'agentsparty[openai]'
uv sync --all-groups   # pydantic / msgspec for a few catalog files
```

Every example is self-contained: no shared helper module. Each online file
builds its own fixed `gpt-5.6-luna` model with the OpenAI API key above.
`examples/coding_agent.py` uses `gpt-5.6-luna` and reads the task from its
interactive Client prompt. Run it from the workspace whose files the agents
may edit.

## Ladder

| Step | Where | What |
| --- | --- | --- |
| **Start** | `online/hello.py`, `online/quickstart.py` | two agents; three roles + a branch |
| **Online catalog** | `online/*.py` | user tasks with a live model |
| **Offline** | `offline/*.py` | deterministic doubles: replay, cancel, budget, projection |
| **Finale** | `online/main.py` | five-role design review with streaming |

---

## Start

| File | Task | Run |
| --- | --- | --- |
| `online/hello.py` | two agents exchange one note | `uv run python examples/online/hello.py` |
| `online/quickstart.py` | Writer drafts; Reviewer approves or rejects | `uv run python examples/online/quickstart.py` |

## Online catalog

Needs `OPENAI_API_KEY`. Each file prints the protocol
first, then the conversation.

| File | Task | Run |
| --- | --- | --- |
| `coding_agent.py` | interactive task → plan (read-only) → implement → one review → ship | `uv run python examples/coding_agent.py` |
| `coding_agent_pro.py` | the same harness on a real directory, watched live in a Textual UI | `uv run --group examples python examples/coding_agent_pro.py [dir]` |
| `online/starter.py` | one-screen app: task, result, one revision | `uv run python examples/online/starter.py` |
| `online/trip.py` | three-day trip plan with a typed itinerary | `uv run python examples/online/trip.py` |
| `online/campaign.py` | research → strategy → ad copy | `uv run python examples/online/campaign.py` |
| `online/score_leads.py` | score candidates, then reach out or redo | `uv run python examples/online/score_leads.py` |
| `online/recruitment.py` | source, rank, outreach, report | `uv run python examples/online/recruitment.py` |
| `online/meeting_actions.py` | transcript → action cards (or skip) | `uv run python examples/online/meeting_actions.py` |
| `online/write_a_book.py` | outline then two chapters under one routine | `uv run python examples/online/write_a_book.py` |
| `online/build_and_qa.py` | engineer code under review until ship | `uv run python examples/online/build_and_qa.py` |
| `online/evaluation.py` | solver retries until the judge passes | `uv run python examples/online/evaluation.py` |
| `online/job_posting.py` | research company culture, write a posting | `uv run python examples/online/job_posting.py` |
| `online/instagram_post.py` | copy + image shot under one compose | `uv run python examples/online/instagram_post.py` |
| `online/landing_page.py` | expand idea, pick templates, write site | `uv run python examples/online/landing_page.py` |
| `online/lint_and_fix.py` | scan markdown until clean | `uv run python examples/online/lint_and_fix.py` |
| `online/retrieval_qa.py` | grounded answer with an auditor | `uv run python examples/online/retrieval_qa.py` |
| `online/match_profile.py` | rank open positions for a CV | `uv run python examples/online/match_profile.py` |
| `online/stock_analysis.py` | filings + arithmetic → hold/buy/sell | `uv run python examples/online/stock_analysis.py` |
| `online/brief_pack.py` | meeting brief from parallel research | `uv run python examples/online/brief_pack.py` |
| `online/gate_and_transform.py` | gate a post, then turn it into a screenplay | `uv run python examples/online/gate_and_transform.py` |
| `online/surprise_trip.py` | surprise itinerary the traveller only sees late | `uv run python examples/online/surprise_trip.py` |
| `online/providers.py` | provider-prefixed model identifiers | `uv run python examples/online/providers.py` |
| `online/model_composition.py` | fallback, retries, spend meter | `uv run python examples/online/model_composition.py` |
| `online/guide.py` | multi-role section pipeline | `uv run python examples/online/guide.py` |
| `online/scribe.py` | compaction as a choreographed role | `uv run python examples/online/scribe.py` |

## Offline (deterministic doubles)

No API key. Use when the point is **replay**, **cancel timing**, **budget
exhaustion**, or a **projection refusal** before any model call.

| File | Task | Run |
| --- | --- | --- |
| `offline/projection_error.py` | silent role → `ProjectionError`, no model | `uv run python examples/offline/projection_error.py` |
| `offline/resume.py` | fall mid-session; resume from a journal | `uv run python examples/offline/resume.py` |
| `offline/cancellation.py` | step budget dies; every role hears cancel | `uv run python examples/offline/cancellation.py` |
| `offline/revise_until_ok.py` | budget exhausted vs work will not converge | `uv run python examples/offline/revise_until_ok.py` |
| `offline/triage_inbox.py` | poll mailbox; journal triage verdicts | `uv run python examples/offline/triage_inbox.py` |
| `offline/toolbox.py` | tool as a role; replay skips the tool call | `uv run python examples/offline/toolbox.py` |

## Finale

| File | Task | Run |
| --- | --- | --- |
| `online/main.py` | five-role design review with live streaming | `uv run python examples/online/main.py` |

## Four ways to type a payload

| Style | Dependencies | Where shown |
| --- | --- | --- |
| `Text.mapping().having(…)` | none | most examples |
| plain `@dataclass` + `json_model` | none | `online/campaign.py` |
| `@dataclass` + `refine(..., holds)` | none | `online/job_posting.py`, `online/match_profile.py` |
| `pydantic.BaseModel` | `pydantic>=2` | `online/surprise_trip.py` |
| `msgspec.Struct` | `msgspec>=0.19` | `online/stock_analysis.py` |

Transfer glossary, notebook map, and source attributions live on
[Protocol-first design](../docs/content/docs/concepts/choreography.mdx).
