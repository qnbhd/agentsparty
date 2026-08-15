"""Structural metrics for the product docs corpus (plan 0017 §5)."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / 'docs' / 'content' / 'docs'
DATASETS = REPO / 'docs' / 'components' / 'diagrams' / 'datasets' / 'index.ts'
META = CONTENT / 'meta.json'
FENCE = re.compile(r'^```python(?:\s+(\w+))?', re.MULTILINE)


def _authored() -> list[Path]:
    return sorted(p for p in CONTENT.rglob('*.mdx') if '(api)' not in p.parts)


def _registry_ids(name: str) -> list[str]:
    text = DATASETS.read_text(encoding='utf-8')
    m = re.search(rf'export const {name}[^=]*=\s*\[(.*?)\];', text, re.DOTALL)
    assert m, f'missing {name}'
    export_names = [x.strip() for x in m.group(1).split(',') if x.strip()]
    ids: list[str] = []
    for export in export_names:
        bm = re.search(
            rf"export const {re.escape(export)}\s*=\s*board\(\s*'([^']+)'",
            text,
        )
        if bm:
            ids.append(bm.group(1))
            continue
        start = text.find(f'export const {export}')
        assert start >= 0, export
        chunk = text[start : start + 400]
        om = re.search(
            r"id:\s*'([^']+)',\s*\n\s*kind:\s*'(?:sequence|projection|timeline|board|animation|knowledge|boundary)'",
            chunk,
        )
        if om:
            ids.append(om.group(1))
            continue
        am = re.search(r"id:\s*'(anim-[^']+)'", chunk)
        assert am, f'missing id for {export}'
        ids.append(am.group(1))
    return ids


def test_authored_page_count_at_least_23() -> None:
    pages = _authored()
    assert len(pages) >= 23, f'authored pages={len(pages)}'


def test_top_level_sections_present() -> None:
    meta = META.read_text(encoding='utf-8')
    for section in (
        'start',
        'concepts',
        'tutorials',
        'reference',
    ):
        assert f'"{section}"' in meta
    assert '"learn"' not in meta
    assert 'elements-demo' not in meta


def test_verifiable_python_fences() -> None:
    modes: dict[str, int] = {}
    bare = 0
    for path in _authored():
        text = path.read_text(encoding='utf-8')
        for m in FENCE.finditer(text):
            mode = (m.group(1) or 'bare').lower()
            if mode == 'python':
                mode = 'bare'
            modes[mode] = modes.get(mode, 0) + 1
            if mode == 'bare':
                snippet = text[m.end() : text.find('```', m.end())]
                if '>>>' not in snippet:
                    bare += 1
    verifiable = modes.get('exec', 0) + modes.get('compile', 0)
    assert bare == 0, f'bare python fences remain: {bare}'
    assert verifiable >= 60, f'verifiable snippets={verifiable} modes={modes}'


def test_static_diagrams_at_least_35_top_level_only() -> None:
    ids = _registry_ids('STATIC_DIAGRAMS')
    assert len(ids) >= 35, f'static diagrams={len(ids)} ids={ids}'
    assert len(set(ids)) == len(ids)
    # nested node/message/event ids (single-letter prefixes) must not inflate count
    bad = [i for i in ids if re.match(r'^(n-|msg-|ev-|m\d+$|e\d+$|c\d+$)', i)]
    assert bad == [], f'nested-looking ids in static registry: {bad}'


def test_static_diagrams_are_drawable_kinds() -> None:
    text = DATASETS.read_text(encoding='utf-8')
    for sid in _registry_ids('STATIC_DIAGRAMS'):
        is_board = re.search(rf"board\(\s*'{re.escape(sid)}'", text)
        is_obj = re.search(
            rf"id:\s*'{re.escape(sid)}',\s*\n\s*kind:\s*'(sequence|projection|timeline|board|knowledge|boundary)'",
            text,
        )
        assert is_board or is_obj, f'{sid} missing drawable kind'


def test_controlled_animations_at_least_9() -> None:
    ids = _registry_ids('ANIMATION_DIAGRAMS')
    assert len(ids) >= 9, f'animations={len(ids)}'
    assert all(i.startswith('anim-') for i in ids)


def _doc_and_example_files() -> list[Path]:
    roots = (
        REPO / 'examples',
        REPO / 'docs' / 'content' / 'docs',
        REPO / 'docs' / 'examples',
        REPO / 'README.md',
    )
    files = [roots[-1]]
    for root in roots[:-1]:
        files.extend(root.rglob('*'))
    return [
        path
        for path in files
        if path.is_file() and path.suffix in {'.py', '.md', '.mdx'} and '(api)' not in path.parts
    ]


def _call_args(source: str, callee: str) -> list[str]:
    found: list[str] = []
    start = 0
    needle = callee + '('
    while True:
        at = source.find(needle, start)
        if at < 0:
            return found
        depth = 0
        end = at + len(needle) - 1
        while end < len(source) and depth >= 0:
            depth += {'(': 1, ')': -1}.get(source[end], 0)
            if depth == 0:
                found.append(source[at + len(needle) : end])
                break
            end += 1
        start = end + 1


def test_async_openai_constructions_set_a_timeout() -> None:
    """Examples and authored docs pass a finite client timeout."""
    missing = [
        f'{path.relative_to(REPO)}'
        for path in _doc_and_example_files()
        for args in _call_args(path.read_text(encoding='utf-8'), 'AsyncOpenAI')
        if 'timeout=' not in args and '...' not in args
    ]
    assert missing == [], 'missing timeout:\n' + '\n'.join(missing)


def test_security_page_covers_required_topics() -> None:
    text = (CONTENT / 'start' / 'security.mdx').read_text(encoding='utf-8')
    for needle in (
        'prompt injection',
        'sandbox',
        'timeout',
        'Deadline',
        'Allowance',
        'Metered',
        'plaintext',
    ):
        assert needle.lower() in text.lower(), needle


def test_start_and_core_concepts_routes_exist() -> None:
    for rel in (
        'start/install.mdx',
        'start/quickstart.mdx',
        'start/what-you-can-rely-on.mdx',
        'start/security.mdx',
        'concepts/protocol-first.mdx',
        'concepts/combinators.mdx',
        'concepts/projection.mdx',
        'concepts/knowledge-of-alt.mdx',
        'concepts/control-and-content.mdx',
        'concepts/participants-and-roles.mdx',
        'concepts/choreography.mdx',
        'concepts/composition-and-termination.mdx',
        'concepts/journal-and-trace.mdx',
        'concepts/models.mdx',
        'tutorials/coding-harness/start.mdx',
        'tutorials/coding-harness/declare-the-conversation.mdx',
        'tutorials/coding-harness/add-tools.mdx',
        'tutorials/coding-harness/bind-and-run.mdx',
        'reference/glossary.mdx',
    ):
        assert (CONTENT / rel).is_file(), rel


def test_authored_mdx_has_no_learn_routes() -> None:
    hits = [
        str(path.relative_to(CONTENT))
        for path in _authored()
        if '/docs/learn' in path.read_text(encoding='utf-8')
    ]
    assert hits == [], 'leftover Learn routes:\n' + '\n'.join(hits)


def test_core_concepts_pages_have_examples() -> None:
    for path in sorted((CONTENT / 'concepts').glob('*.mdx')):
        text = path.read_text(encoding='utf-8')
        assert '```python exec' in text or '```python compile' in text, path.name


def test_llms_artifacts_include_structured_sections() -> None:
    llms = (REPO / 'docs' / 'public' / 'llms.txt').read_text(encoding='utf-8')
    assert '## Start' in llms or '## Documentation map' in llms
    assert (REPO / 'docs' / 'public' / 'llms-full.txt').is_file()


def test_no_unclosed_code_fences() -> None:
    problems: list[str] = []
    for path in _authored():
        fenced = False
        open_line = 0
        for i, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if line.startswith(('```', '~~~')):
                if not fenced:
                    fenced = True
                    open_line = i
                else:
                    fenced = False
        if fenced:
            problems.append(f'{path.relative_to(CONTENT)}:{open_line}')
    assert problems == [], 'unclosed fences:\n' + '\n'.join(problems)


def test_no_dead_end_manual_pages() -> None:
    """§5: zero manual product pages without an outgoing semantic link."""
    dead: list[str] = []
    for path in _authored():
        if path.name == 'index.mdx':
            continue
        text = path.read_text(encoding='utf-8')
        if not ('/docs/' in text or '[[agentsparty.' in text or 'examples/' in text):
            dead.append(str(path.relative_to(CONTENT)))
    assert dead == [], 'dead-end pages:\n' + '\n'.join(dead)
