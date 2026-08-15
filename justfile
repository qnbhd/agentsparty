default:
    @just --list

install:
    uv sync --frozen --all-groups
    pre-commit install --install-hooks

sync:
    uv sync --all-groups

format:
    uv run ruff format src tests examples
    uv run ruff format --line-length 80 docs/content/docs
    uv run ruff check --fix

lint:
    uv run ruff format --check src tests examples
    uv run ruff format --line-length 80 --check docs/content/docs
    uv run ruff check
    uv run flake8 src --select WPS

typecheck:
    uv run pyright
    uv run ty check examples src/agentsparty tests

test:
    uv run pytest -n auto

test-wheel:
    uv run nox -s test

testcov:
    uv run nox -s testcov

docs:
    npm --prefix docs ci
    npm --prefix docs run build

docs-check:
    npm --prefix docs ci
    npm --prefix docs run check

docs-serve:
    npm --prefix docs run dev

# Serve the exported site in docs/out, exactly as a static host would.
docs-preview:
    npm --prefix docs run preview

run-example:
    uv run python examples/online/main.py

links:
    uv run pytest tests/docs/test_links.py --no-cov

docs-cov:
    uv run pytest tests/docs/test_coverage.py --no-cov

spell:
    uv run codespell --toml pyproject.toml src tests examples docs/content/docs docs/examples README.md CHANGELOG.md dsl-2.md architecture/decisions justfile pyproject.toml
    uv run typos

all: format lint typecheck testcov docs spell links docs-cov

ci:
    uv run nox -t ci
