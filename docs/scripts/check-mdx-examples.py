"""Check Python fences in authored MDX: exec / compile / pseudocode / doctest.

Modes (language line tokens after ``python``):

- ``exec`` — concatenate page exec blocks and run in a subprocess
- ``compile`` — ``compile(..., mode='exec')`` on 3.10-compatible syntax
- ``pseudocode`` — highlight only; requires nearby ``Illustrative only``
- bare ``python`` — error (must be marked)
- doctest (``>>>`` inside a fence) — run via :mod:`doctest` as before
"""

from __future__ import annotations

import doctest
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'content' / 'docs'
REPO = ROOT.parent
GENERATED = '(api)'
FENCE_OPEN = re.compile(r'^```([^\n`]*)\s*$')
TIMEOUT_S = 15


@dataclass(frozen=True)
class Fence:
    """One fenced code block from an MDX page."""

    path: Path
    index: int
    lang: str
    mode: str
    body: str
    line: int


def authored_mdx() -> list[Path]:
    return sorted(
        p
        for p in CONTENT.rglob('*.mdx')
        if GENERATED not in p.parts
    )


def parse_fences(path: Path) -> list[Fence]:
    lines = path.read_text(encoding='utf-8').splitlines()
    fences: list[Fence] = []
    i = 0
    index = 0
    while i < len(lines):
        open_m = FENCE_OPEN.match(lines[i])
        if not open_m:
            i += 1
            continue
        info = open_m.group(1).strip()
        start = i
        i += 1
        body_lines: list[str] = []
        while i < len(lines) and not lines[i].startswith('```'):
            body_lines.append(lines[i])
            i += 1
        i += 1  # closing fence
        tokens = info.split()
        lang = tokens[0].lower() if tokens else ''
        mode = tokens[1].lower() if len(tokens) > 1 else ''
        if lang == 'python' and mode not in {'exec', 'compile', 'pseudocode'}:
            mode = 'bare' if mode == '' else mode
        fences.append(
            Fence(
                path=path,
                index=index,
                lang=lang,
                mode=mode,
                body='\n'.join(body_lines),
                line=start + 1,
            )
        )
        index += 1
    return fences


def _nearby_illustrative(path: Path, line: int) -> bool:
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    window = '\n'.join(lines[max(0, line - 8) : min(len(lines), line + 12)])
    return 'Illustrative only' in window


def check_bare(fences: list[Fence]) -> list[str]:
    return [
        f'{f.path.relative_to(ROOT)}:{f.line}: unmarked python fence '
        f'(use exec, compile, or pseudocode)'
        for f in fences
        if f.lang == 'python' and f.mode == 'bare' and '>>>' not in f.body
    ]


def check_pseudocode(fences: list[Fence]) -> list[str]:
    return [
        f'{f.path.relative_to(ROOT)}:{f.line}: pseudocode fence needs '
        f'nearby "Illustrative only"'
        for f in fences
        if f.lang == 'python' and f.mode == 'pseudocode' and not _nearby_illustrative(f.path, f.line)
    ]


def check_compile(fences: list[Fence]) -> list[str]:
    problems: list[str] = []
    for f in fences:
        if f.lang != 'python' or f.mode != 'compile':
            continue
        try:
            compile(f.body + '\n', f'{f.path}:{f.line}', 'exec')
        except SyntaxError as exc:
            problems.append(
                f'{f.path.relative_to(ROOT)}:{f.line}: compile block #{f.index}: {exc}'
            )
    return problems


def check_exec(pages: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in pages:
        fences = [f for f in parse_fences(path) if f.lang == 'python' and f.mode == 'exec']
        if not fences:
            continue
        # Skip blocks that look like expected failures (raise ProjectionError etc.)
        source = '\n\n'.join(f.body for f in fences)
        if '>>>' in source:
            continue
        env = {
            **dict(**{k: v for k, v in __import__('os').environ.items()}),
            'PYTHONPATH': str(REPO / 'src'),
            'AGENTSPARTY_DOCS_EXEC': '1',
        }
        # Drop network-ish keys so offline pages cannot silently use keys
        for key in ('OPENAI_API_KEY',):
            env.pop(key, None)
        try:
            completed = subprocess.run(
                [sys.executable, '-c', source],
                cwd=str(REPO),
                env=env,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            problems.append(f'{path.relative_to(ROOT)}: exec timeout after {TIMEOUT_S}s')
            continue
        if completed.returncode != 0:
            err = (completed.stderr or completed.stdout or 'unknown error').strip()
            problems.append(
                f'{path.relative_to(ROOT)}: exec failed ({completed.returncode}):\n{err[:800]}'
            )
    return problems


def check_doctest(pages: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in pages:
        blocks: list[str] = []
        for f in parse_fences(path):
            if f.lang == 'python' and '>>>' in f.body:
                blocks.append(f.body)
        if not blocks:
            continue
        source = '\n'.join(blocks)
        runner = doctest.DocTestRunner(verbose=False)
        parser = doctest.DocTestParser()
        test = parser.get_doctest(source, {}, path.as_posix(), path.as_posix(), 0)
        result = runner.run(test)
        if result.failed:
            problems.append(f'{path.relative_to(ROOT)}: {result.failed} doctest failure(s)')
    return problems


def check_diagram_fixtures() -> list[str]:
    """Diagram text must equal render() output (docs/test-fixtures/diagrams.py)."""
    fixture = ROOT / 'test-fixtures' / 'diagrams.py'
    if not fixture.exists():
        return [f'missing diagram fixture: {fixture.relative_to(ROOT)}']
    env = {**os.environ, 'PYTHONPATH': str(REPO / 'src')}
    try:
        completed = subprocess.run(
            [sys.executable, str(fixture)],
            cwd=str(REPO),
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [f'{fixture.relative_to(ROOT)}: diagram fixture timeout after {TIMEOUT_S}s']
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or 'unknown error').strip()
        return [f'{fixture.relative_to(ROOT)}: diagram fixture failed:\n{err[:800]}']
    return []


def main() -> None:
    pages = authored_mdx()
    all_fences = [f for p in pages for f in parse_fences(p)]
    python = [f for f in all_fences if f.lang == 'python']
    problems = [
        *check_bare(python),
        *check_pseudocode(python),
        *check_compile(python),
        *check_exec(pages),
        *check_doctest(pages),
        *check_diagram_fixtures(),
    ]
    modes = {}
    for f in python:
        modes[f.mode or 'unknown'] = modes.get(f.mode or 'unknown', 0) + 1
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        raise SystemExit(1)
    print(
        f'checked {len(pages)} MDX page(s); '
        f'{len(python)} python fence(s); modes={modes}'
    )


if __name__ == '__main__':
    main()
