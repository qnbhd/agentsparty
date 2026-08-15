"""Guard that the committed generated API covers the public modules."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from tests.api.test_public import PUBLIC as PUBLIC_MODULES

DOCS = Path(__file__).resolve().parents[2] / 'docs'
API = DOCS / 'content' / 'docs' / '(api)'


def test_each_public_module_has_autodoc_page() -> None:
    for module in PUBLIC_MODULES:
        page = API.joinpath(*module.split('.')) / 'index.mdx'
        assert page.is_file(), f'missing autodoc page for {module}'
    data = json.loads((DOCS / 'public' / 'api-data.json').read_text(encoding='utf-8'))
    assert data['xref_map'], 'generated API must contain an xref_map'


def test_each_module_has_a_docstring() -> None:
    for module in PUBLIC_MODULES:
        mod = importlib.import_module(module)
        assert mod.__doc__, f'{module} lacks a module docstring'


def test_llm_artifacts_exist() -> None:
    assert (DOCS / 'public' / 'llms.txt').is_file()
    assert (DOCS / 'public' / 'llms-full.txt').is_file()
