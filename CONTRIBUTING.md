# Contributing

Thank you for considering a contribution. The public surface is recorded in
[`tests/public_api.txt`](tests/public_api.txt).

## Prerequisites

- Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 (only for the documentation site)
- git

## Setup

```bash
git clone https://github.com/qnbhd/agentsparty.git
cd agentsparty
uv sync --all-groups
```

Docs site dependencies:

```bash
npm --prefix docs ci
```

## Tests

Fast, from a development checkout:

```bash
uv run pytest -n auto
```

README doctest and the offline projection example:

```bash
uv run pytest README.md examples/offline/projection_error.py -q
```

Full CI, including the wheel install smoke and docs checks:

```bash
uv run nox -t ci
```

`just all` runs the same local gate as maintainers.

Do not monkey-patch in tests. Inject doubles.

## Documentation

```bash
npm --prefix docs run check
npm --prefix docs run build
npm --prefix docs run dev
```

`check` regenerates `docs/content/docs/(api)` and `docs/public`. Do not edit
those trees by hand.

## Pull requests

- Smallest possible patch for the stated task.
- English for code, docs, issues, and pull requests.
- No drive-by features, abstractions, or unrelated formatting.
- Fill in `.github/PULL_REQUEST_TEMPLATE.md`.

## Changelog and public API

- Update `CHANGELOG.md` under `Unreleased` for user-visible changes.
- Public surface changes must update `tests/public_api.txt` knowingly.

Agent-oriented coding conventions: [`AGENTS.md`](AGENTS.md).
Security reports go to [SECURITY.md](SECURITY.md), not public issues.
Conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
