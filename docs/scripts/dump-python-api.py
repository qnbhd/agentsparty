"""Dump `agentsparty` in the schema that fumadocs-python's `convert` consumes.

Replaces `fumapy-generate`, which drops every alias. `agentsparty` exposes its
surface through facade modules: `agentsparty.protocol.msg` is defined in
`agentsparty.protocol.session._syntax`, and dropping the alias documents it
nowhere, because the private module it comes from is not published either.

Each name a module re-exports from a private module is therefore parsed at
its definition and filed under the facade that exports it. Names re-exported
from a *public* module are left alone: that module already documents them,
and hoisting would publish a second page for the same object.
"""

from __future__ import annotations

import json
from pathlib import Path

import griffe
from fumapy.mksource import CustomEncoder, parse_class, parse_function, parse_module
from griffe_typingdoc import TypingDocExtension

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parents[1] / 'agentsparty.json'

PARSERS = {griffe.Kind.CLASS: parse_class, griffe.Kind.FUNCTION: parse_function}
SECTIONS = {griffe.Kind.CLASS: 'classes', griffe.Kind.FUNCTION: 'functions'}


def _is_private(path: str) -> bool:
    return any(part.startswith('_') for part in path.split('.'))


def _resolved_target(alias: griffe.Alias) -> griffe.Object | None:
    """The object an export finally names, or None when it is unresolvable."""
    try:
        return alias.final_target
    except (griffe.AliasResolutionError, griffe.CyclicAliasError):
        return None


def _hoisted_exports(module: griffe.Module) -> dict[str, tuple[str, dict]]:
    """Parsed entries for the names this module re-exports from private code."""
    hoisted = {}
    for name in module.exports or ():
        member = module.members.get(str(name))
        if member is None or not member.is_alias:
            continue
        target = _resolved_target(member)
        if target is None or target.kind not in PARSERS:
            continue
        # The defining module is published in its own right; linking there
        # beats duplicating the page.
        if not _is_private(target.parent.path):
            continue
        entry = PARSERS[target.kind](target)
        # Address the object where it is exported, not where it is written:
        # `convert` derives both the page URL and the file path from `path`.
        entry['path'] = f'{module.path}.{name}'
        hoisted[str(name)] = (SECTIONS[target.kind], entry)
    return hoisted


def _with_exports(module: griffe.Module, parsed: dict) -> dict:
    """Add every hoisted export, then recurse into the parsed submodules."""
    for name, (section, entry) in _hoisted_exports(module).items():
        parsed[section].setdefault(name, entry)
    for name, child in parsed['modules'].items():
        _with_exports(module.modules[name], child)
    return parsed


def main() -> None:
    package = griffe.load(
        'agentsparty',
        search_paths=[ROOT / 'src'],
        docstring_parser='auto',
        store_source=True,
        allow_inspection=False,
        extensions=griffe.load_extensions(TypingDocExtension),
    )
    payload = _with_exports(package, parse_module(package))
    OUTPUT.write_text(
        json.dumps(payload, cls=CustomEncoder, indent=2) + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
