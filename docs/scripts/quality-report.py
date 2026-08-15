"""Emit docs quality metrics as JSON (baseline or live)."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'content' / 'docs'
DATASETS = ROOT / 'components' / 'diagrams' / 'datasets' / 'index.ts'
GENERATED = '(api)'
FENCE = re.compile(r'^```([a-zA-Z0-9_+-]*)([^\n`]*)\s*$')
XREF = re.compile(r'\[\[([A-Za-z_][\w.]*)\]\]')
WORD = re.compile(r'\b[A-Za-z]{2,}\b')


def authored_pages() -> list[Path]:
    return sorted(
        p
        for p in CONTENT.rglob('*.mdx')
        if GENERATED not in p.parts
    )


def fence_modes(text: str) -> list[str]:
    modes: list[str] = []
    for line in text.splitlines():
        m = FENCE.match(line)
        if not m:
            continue
        lang = (m.group(1) or '').lower()
        rest = (m.group(2) or '').strip().lower()
        if lang != 'python':
            continue
        if rest in {'exec', 'compile', 'pseudocode'}:
            modes.append(rest)
        elif rest == '' or rest == 'python':
            modes.append('bare')
        else:
            token = rest.split()[0] if rest else 'bare'
            modes.append(token if token in {'exec', 'compile', 'pseudocode'} else 'bare')
    return modes


def registry_ids(name: str) -> list[str]:
    """Top-level dataset ids from STATIC_DIAGRAMS / ANIMATION_DIAGRAMS only.

    Nested node/step/message ids inside a dataset body are never counted.
    """
    text = DATASETS.read_text(encoding='utf-8')
    m = re.search(rf'export const {name}[^=]*=\s*\[(.*?)\];', text, re.S)
    if not m:
        return []
    export_names = [x.strip() for x in m.group(1).split(',') if x.strip()]
    ids: list[str] = []
    for export in export_names:
        # board('semantic-id', ...) constructor
        bm = re.search(
            rf"export const {re.escape(export)}\s*=\s*board\(\s*'([^']+)'",
            text,
        )
        if bm:
            ids.append(bm.group(1))
            continue
        start = text.find(f'export const {export}')
        if start < 0:
            continue
        chunk = text[start : start + 400]
        # object literal: id then kind (top-level only)
        om = re.search(
            r"id:\s*'([^']+)',\s*\n\s*kind:\s*'(?:sequence|projection|timeline|board|animation|knowledge|boundary)'",
            chunk,
        )
        if om:
            ids.append(om.group(1))
            continue
        am = re.search(r"id:\s*'(anim-[^']+)'", chunk)
        if am:
            ids.append(am.group(1))
    return ids


def metrics() -> dict:
    pages = authored_pages()
    mode_counts: Counter[str] = Counter()
    xrefs = 0
    words = 0
    dead_ends: list[str] = []
    unclosed_fences: list[str] = []
    for path in pages:
        text = path.read_text(encoding='utf-8')
        mode_counts.update(fence_modes(text))
        xrefs += len(XREF.findall(text))
        body = re.sub(r'```.*?```', ' ', text, flags=re.S)
        words += len(WORD.findall(body))
        # unclosed fence scan
        fenced = False
        open_line = 0
        for i, line in enumerate(text.splitlines(), 1):
            if line.startswith('```') or line.startswith('~~~'):
                if not fenced:
                    fenced = True
                    open_line = i
                else:
                    fenced = False
        if fenced:
            unclosed_fences.append(f'{path.relative_to(CONTENT)}:{open_line}')
        # dead-end: no outgoing semantic link (index is a map, allowed)
        rel = str(path.relative_to(CONTENT))
        if path.name != 'index.mdx' and not (
            '/docs/' in text or '[[agentsparty.' in text or 'examples/' in text
        ):
            dead_ends.append(rel)
    static_ids = registry_ids('STATIC_DIAGRAMS')
    anim_ids = registry_ids('ANIMATION_DIAGRAMS')
    verifiable = mode_counts['exec'] + mode_counts['compile']
    generated = list((CONTENT / GENERATED).rglob('*.mdx')) if (CONTENT / GENERATED).is_dir() else []
    examples = [
        p for p in (ROOT.parent / 'examples').rglob('*.py') if '__pycache__' not in p.parts
    ]
    return {
        'authored_pages': len(pages),
        'generated_pages': len(generated),
        'words': words,
        'python_fences': dict(mode_counts),
        'verifiable_snippets': verifiable,
        'bare_python_fences': mode_counts['bare'],
        'xrefs': xrefs,
        'static_diagrams': len(static_ids),
        'static_diagram_ids': static_ids,
        'animations': len(anim_ids),
        'animation_ids': anim_ids,
        'dead_end_pages': dead_ends,
        'dead_end_count': len(dead_ends),
        'unclosed_fences': unclosed_fences,
        'example_files': len(examples),
        'pages': [str(p.relative_to(CONTENT)) for p in pages],
    }


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'quality-baseline.json'
    data = metrics()
    out.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(
        f'wrote {out} authored={data["authored_pages"]} '
        f'verifiable={data["verifiable_snippets"]} '
        f'static_diagrams={data["static_diagrams"]} animations={data["animations"]} '
        f'dead_ends={data["dead_end_count"]} unclosed={len(data["unclosed_fences"])}'
    )
    if data['dead_end_count'] or data['unclosed_fences']:
        if data['dead_end_pages']:
            print('dead-end pages:', ', '.join(data['dead_end_pages']))
        if data['unclosed_fences']:
            print('unclosed fences:', ', '.join(data['unclosed_fences']))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
