"""Drive shipped example helpers for untrusted data and write confinement."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_untrusted_search_hits_cap_count_and_each_body() -> None:
    module = _load(
        ROOT / 'examples' / 'content-pipeline' / 'protocol.py',
        'agentsparty_examples_content_pipeline_protocol',
    )
    long_body = 'x' * (module.MAX_BODY_CHARS + 80)
    hits = [{'title': 't', 'href': 'https://example.test', 'body': long_body}] * 12
    out = module.untrusted_search_hits(hits)
    assert len(out) == module.MAX_RESULTS
    assert all(len(hit['body']) == module.MAX_BODY_CHARS for hit in out)
    assert 'untrusted web data' in module.RESEARCHER_BRIEF
    assert 'not instructions' in module.RESEARCHER_BRIEF
    assert 'commands' in module.RESEARCHER_BRIEF


def test_landing_page_writes_only_closed_names_under_root(tmp_path: Path) -> None:
    module = _load(
        ROOT / 'examples' / 'online' / 'landing_page.py',
        'agentsparty_examples_landing_page',
    )
    hero = module.component_path(tmp_path, 'Hero')
    assert hero == (tmp_path / 'Hero.txt').resolve()
    assert hero.is_relative_to(tmp_path.resolve())
    with pytest.raises(ValueError, match='closed component name'):
        module.component_path(tmp_path, 'Other')
    with pytest.raises(ValueError, match='closed component name'):
        module.component_path(tmp_path, '../secret')


def test_meeting_ledger_stays_under_workspace(tmp_path: Path) -> None:
    module = _load(
        ROOT / 'examples' / 'online' / 'meeting_actions.py',
        'agentsparty_examples_meeting_actions',
    )
    path = module.ledger_path(tmp_path)
    assert path == (tmp_path / 'actions.csv').resolve()
    assert path.is_relative_to(tmp_path.resolve())


def test_triage_demo_states_no_authentication() -> None:
    text = (ROOT / 'examples' / 'triage' / 'app.py').read_text(encoding='utf-8')
    assert 'no authentication' in text.lower()
    assert 'do not expose' in text.lower()
