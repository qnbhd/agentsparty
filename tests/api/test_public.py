"""Guard: the public surface is exactly what the contract says it is.

Tier 1 (core) and tier 2 (extension) modules declare ``__all__``; their union
is the public API. ``tests/public_api.txt`` is the recorded surface — a diff
there is the review signal that a release-note entry is due.

See ADR 0029 and tests/public_api.txt.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import types
import typing
from pathlib import Path

import agentsparty
import agentsparty.protocol

CORE = [
    'agentsparty',
    'agentsparty.agent',
    'agentsparty.brief',
    'agentsparty.choreography',
    'agentsparty.debug',
    'agentsparty.human',
    'agentsparty.journal',
    'agentsparty.kernel',
    'agentsparty.llm',
    'agentsparty.machine',
    'agentsparty.participant',
    'agentsparty.protocol',
    'agentsparty.runtime',
    'agentsparty.toolbox',
    'agentsparty.tracing',
]

TYPE_HOMES = [
    'agentsparty.journal.jsonl',
    'agentsparty.journal.memory',
    'agentsparty.journal.types',
    'agentsparty.llm.compose',
    'agentsparty.llm.profile',
    'agentsparty.llm.scripted',
    'agentsparty.llm.types',
    'agentsparty.kernel.budget',
    'agentsparty.kernel.console',
    'agentsparty.kernel.errors',
    'agentsparty.kernel.nonempty',
    'agentsparty.kernel.role',
    'agentsparty.choreography.chor',
    'agentsparty.protocol.analysis',
    'agentsparty.protocol.language.core',
    'agentsparty.protocol.graph',
    'agentsparty.protocol.language.core',
    'agentsparty.protocol.language.endpoint',
    'agentsparty.protocol.language.raw',
    'agentsparty.protocol.render',
    'agentsparty.protocol.routine',
    'agentsparty.protocol.session',
    'agentsparty.protocol.session.types',
    'agentsparty.tracing.facet',
    'agentsparty.tracing.memory',
    'agentsparty.tracing.model',
    'agentsparty.tracing.queue',
    'agentsparty.tracing.scope',
    'agentsparty.tracing.signals',
    'agentsparty.tracing.stream',
    'agentsparty.tracing.types',
]

EXTENSION = [
    'agentsparty.journal.sqlite',
    'agentsparty.llm.openai',
    'agentsparty.protocol.language.endpoint',
    'agentsparty.protocol.language.raw',
    'agentsparty.tracing.sqlite',
]

PUBLIC = CORE + TYPE_HOMES + EXTENSION
ALLOWED_IMPORTS = frozenset(PUBLIC)
SNAPSHOT = Path(__file__).resolve().parents[1] / 'public_api.txt'
EXAMPLES = Path(__file__).resolve().parents[2] / 'examples'


def _surface() -> list[str]:
    """Every public name, as ``module:name``, sorted."""
    return sorted(
        f'{module}:{name}' for module in PUBLIC for name in importlib.import_module(module).__all__
    )


def test_every_public_module_declares_all() -> None:
    for module in PUBLIC:
        mod = importlib.import_module(module)
        assert hasattr(mod, '__all__'), f'{module} must declare __all__'


def test_no_exported_name_is_private() -> None:
    for module in PUBLIC:
        mod = importlib.import_module(module)
        private = [n for n in mod.__all__ if n.startswith('_') and n != '__version__']
        assert not private, f'{module} exports private names: {private}'


def test_every_exported_name_exists() -> None:
    for module in PUBLIC:
        mod = importlib.import_module(module)
        missing = [n for n in mod.__all__ if not hasattr(mod, n)]
        assert not missing, f'{module} exports missing names: {missing}'


def test_no_duplicate_exports_within_a_module() -> None:
    for module in PUBLIC:
        names = importlib.import_module(module).__all__
        assert len(names) == len(set(names)), f'{module} lists a name twice'


def _annotation_types(value: object) -> list[type]:
    """Return project-defined classes nested in an annotation."""
    if isinstance(value, type):
        return [value]
    if isinstance(value, types.UnionType) or typing.get_origin(value) is not None:
        return [
            found for argument in typing.get_args(value) for found in _annotation_types(argument)
        ]
    return []


def _public_callables(module: object, name: str) -> list[object]:
    """Return an exported callable and its public class methods."""
    value = getattr(module, name)
    if not inspect.isclass(value):
        return [value] if inspect.isfunction(value) else []
    methods = [
        method
        for method_name, method in inspect.getmembers(value, inspect.isfunction)
        if not method_name.startswith('_') or method_name == '__init__'
    ]
    return [value, *methods]


def test_public_signatures_use_public_types() -> None:
    """Public annotations must not expose types from private modules."""
    leaks = [leak for module_name in PUBLIC for leak in _module_signature_leaks(module_name)]
    assert leaks == [], 'public signatures expose private types:\n' + '\n'.join(leaks)


def _module_signature_leaks(module_name: str) -> list[str]:
    module = importlib.import_module(module_name)
    return [
        leak
        for name in module.__all__
        for callable_value in _public_callables(module, name)
        for leak in _callable_signature_leaks(module_name, name, callable_value)
    ]


def _callable_signature_leaks(module_name: str, name: str, callable_value) -> list[str]:
    try:
        hints = typing.get_type_hints(callable_value)
    except (NameError, TypeError) as exc:
        return [f'{module_name}.{name}: unresolved annotations: {exc}']
    return [
        f'{module_name}.{name}.{hint_name}: {annotation_type.__module__}'
        for hint_name, hint in hints.items()
        for annotation_type in _annotation_types(hint)
        if annotation_type.__module__.startswith('agentsparty')
        and annotation_type.__module__ not in PUBLIC
    ]


def test_public_surface_matches_the_snapshot() -> None:
    """A diff here is intentional or it is a leak. Update the file knowingly."""
    recorded = SNAPSHOT.read_text(encoding='utf-8').split()
    assert _surface() == recorded, (
        'the public surface changed; review the diff and, if it is intended, '
        'regenerate with:\n'
        '  uv run python -c "import tests.api.test_public as t; '
        't.SNAPSHOT.write_text(chr(10).join(t._surface()) + chr(10))"'
    )


def test_root_codec_vocabulary_is_canonical() -> None:
    names = (
        'Text',
        'Integer',
        'Number',
        'Flag',
        'Null',
        'Nothing',
        'Codec',
        'record',
        'json_model',
    )
    assert all(getattr(agentsparty, name) is getattr(agentsparty.protocol, name) for name in names)


def test_examples_import_only_public_modules() -> None:
    """Examples must not import tier-3 module paths (plan 0010 §11)."""
    leaks: list[str] = []
    for path in sorted(EXAMPLES.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not node.module.startswith('agentsparty'):
                continue
            if node.module not in ALLOWED_IMPORTS:
                leaks.append(f'{path.name}:{node.lineno}: from {node.module}')
    assert not leaks, 'examples import tier-3 modules:\n' + '\n'.join(leaks)
