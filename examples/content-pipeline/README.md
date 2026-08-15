# Content pipeline

A focused Gradio demo for a marketing workflow:

`Brief → Researcher ⇄ Search → Writer → Editor (human) → Publisher`

The Researcher is a model-driven agent, but its Findings are grounded in
the live web: it distils the brief into one `Query`, and `Search` — a
`Toolbox` answered by `ddgs` — replies with real `Results` before the
Researcher writes the notes the Writer works from.

The Editor's **Approve** and **Request revision** buttons stay disabled until
the protocol offers that choice. A revision re-enters the bounded
`rec('revise', ...)` loop; `Allowance(unfoldings=3)` prevents an endless cycle.
The collapsed activity panel is fed by `StreamTracer` and includes the rendered
global protocol.

The example calls `gpt-5.6-luna` through `OPENAI_API_KEY`. `Metered` caps model
usage at 40,000 tokens for the session; `Allowance` separately bounds protocol
steps and unfoldings.

## Run

```bash
export OPENAI_API_KEY=...
uv run --with gradio python examples/content-pipeline/app.py
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860).

The current sidebar and markdown workspace are captured in
[`screenshots/sidebar.png`](screenshots/sidebar.png).

`project_all(protocol)` runs when the protocol module is imported. Remove one
of the `Working` or `Published` notifications in `protocol.py` to see the
projection fail before the UI starts: the uninformed role can no longer know
which branch the Editor selected.
