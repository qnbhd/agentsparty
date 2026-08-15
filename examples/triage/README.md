# Support Triage API

One support ticket is one durable multiparty session:

`Intake → Classifier → KB → Responder → Approver`

`POST /tickets` returns a ticket id immediately. Classification, knowledge-base
calls, typed drafts and the human decision are committed to `SqliteJournal`.
After a process restart, `GET /tickets/{id}` reads the saved trace directly and
`POST /tickets/{id}/resume` replays it before continuing, so completed model and
tool decisions are not called again.

The protocol uses closed `record()` codecs for `Ticket` and `Draft`, plus a
bounded integer codec for severity. FastAPI exposes the decoded values through
Pydantic response models. The worker uses `gpt-5.6-luna`, a 40,000-token
`Metered` limit and `Allowance(steps=32, unfoldings=4)`. Tokens are deliberately
metered by the model wrapper rather than `Allowance`: their count is known only
after the provider responds.

## Run

```bash
export OPENAI_API_KEY=...
uv run --with fastapi --with uvicorn --with pydantic python examples/triage/app.py
```

Open [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs).

Set `TRIAGE_DB=/path/to/tickets.db` to keep the journal elsewhere and `PORT` to
change the listening port.

## API

```bash
curl -s -X POST http://127.0.0.1:8765/tickets \
  -H 'content-type: application/json' \
  -d '{"text":"Our card was charged twice","customer_tier":"enterprise"}'

curl -s http://127.0.0.1:8765/tickets/$TICKET_ID

curl -s -X POST http://127.0.0.1:8765/tickets/$TICKET_ID/decision \
  -H 'content-type: application/json' \
  -d '{"label":"Ship"}'

curl -s -X POST http://127.0.0.1:8765/tickets/$TICKET_ID/resume
```
