"""Guard: every internal link and anchor in the docs resolves.

External links are only checked when ``AGENTSPARTY_CHECK_EXTERNAL=1`` so the
default test run stays fast and offline; CI can opt in.
"""

from __future__ import annotations

import os
import re
import unicodedata
from contextlib import closing
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from urllib.parse import urlsplit

DOCS = Path(__file__).resolve().parents[2] / 'docs' / 'content' / 'docs'
README = Path(__file__).resolve().parents[2] / 'README.md'
# Site-absolute links name a route. `(api)` is a route group, so it is a
# directory on disk but not a path segment in the URL.
ROUTE_ROOT = '/docs/'
CONTENT_ROOTS = (DOCS, DOCS / '(api)')

_LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
_INLINE_CODE = re.compile(r'`+[^`\n]*`+')


def _files() -> list[Path]:
    return sorted([*DOCS.rglob('*.mdx'), README])


def _links() -> list[tuple[Path, str]]:
    return [
        (path, target)
        for path in _files()
        for target in _markdown_links(path.read_text(encoding='utf-8'))
    ]


def _markdown_links(text: str) -> list[str]:
    """Extract links from prose, excluding fenced and indented code."""
    links: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith('```'):
            fenced = not fenced
            continue
        if fenced or line.startswith('    '):
            continue
        links.extend(_LINK.findall(_INLINE_CODE.sub('', line)))
    return links


def _slugify(text: str) -> str:
    value = unicodedata.normalize('NFKD', text)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)


def _headings(path: Path) -> set[str]:
    slugs: set[str] = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('#'):
            slugs.add(_slugify(line.lstrip('#').strip()))
    return slugs


def _bases(source: Path, target: str) -> tuple[Path, ...]:
    """The directories *target* may be written against."""
    if target.startswith(ROUTE_ROOT):
        return CONTENT_ROOTS
    return (source.parent,)


def _page_at(candidate: Path) -> Path | None:
    if candidate.is_file():
        return candidate
    if candidate.suffix in {'.md', '.mdx'}:
        return None
    guesses = (candidate.with_suffix('.mdx'), candidate.with_suffix('.md'), candidate / 'index.mdx')
    return next((guess for guess in guesses if guess.is_file()), None)


def _resolve(source: Path, target: str) -> Path | None:
    """Resolve *target* to the page it names, or ``None``."""
    route = target.removeprefix(ROUTE_ROOT)
    resolved = (_page_at((base / route).resolve()) for base in _bases(source, target))
    return next((page for page in resolved if page is not None), None)


def test_internal_links_resolve() -> None:
    problems = [
        problem
        for source, target in _links()
        if (problem := _internal_link_problem(source, target)) is not None
    ]
    assert problems == [], 'broken docs links:\n' + '\n'.join(problems)


def _internal_link_problem(source: Path, target: str) -> str | None:
    if target.startswith(('http://', 'https://', 'mailto:')):
        return None
    path, _, anchor = target.partition('#')
    resolved = _resolve(source, path)
    rel = source.relative_to(DOCS.parents[2])
    if resolved is None:
        return f'{rel}: broken link {path!r}'
    if not anchor or ':::' in resolved.read_text(encoding='utf-8'):
        return None
    if _slugify(anchor) in _headings(resolved):
        return None
    return f'{rel}: anchor #{anchor} not found in {resolved.name}'


def test_external_links_resolve() -> None:
    if os.environ.get('AGENTSPARTY_CHECK_EXTERNAL') != '1':
        return
    failures = [
        failure
        for _source, target in _links()
        if (failure := _external_link_problem(target)) is not None
    ]
    assert failures == [], 'unreachable external links:\n' + '\n'.join(failures)


def _external_link_problem(target: str) -> str | None:
    if not target.startswith(('http://', 'https://')):
        return None
    try:
        status = _http_status(target)
    except OSError as exc:
        return f'{target} -> {exc}'
    else:
        return f'{target} -> HTTP {status}' if status >= 400 else None


def _http_status(target: str) -> int:
    parsed = urlsplit(target)
    connection_type = HTTPSConnection if parsed.scheme == 'https' else HTTPConnection
    path = parsed.path or '/'
    if parsed.query:
        path += f'?{parsed.query}'
    with closing(connection_type(parsed.netloc, timeout=15)) as connection:
        connection.request('GET', path, headers={'User-Agent': 'agentsparty docs link check'})
        return connection.getresponse().status
