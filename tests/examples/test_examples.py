"""Acceptance runners for examples (plan 0012 F5).

Offline suite: subprocess run, section headers, deterministic skeletons.
Online suite (cheap CI): import module + project_all without a model call.
Live online runs are a separate nox session (examples_online), not this file.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / 'examples'
OFFLINE = EXAMPLES / 'offline'
ONLINE = EXAMPLES / 'online'

# Offline files with deterministic skeleton lines (catalog-style).
SKELETONS: dict[str, str] = {
    'revise_until_ok.py': (
        'Editor:Topic  Bard:Measure  Meter:Length  Bard:Post  Critic:Revise  '
        'Bard:Again  Meter:Closed  Bard:Retrying  Bard:Measure  Meter:Length  '
        'Bard:Post  Critic:Revise  Bard:Again  Meter:Closed  Bard:Retrying  '
        'Bard:Measure  Meter:Length  Bard:Post  Critic:Give up  Bard:Done  '
        'Meter:Closed  Bard:Abandoned'
    ),
    'triage_inbox.py': (
        'Owner:Check  Triage:Fetch  Mailbox:Thread  Triage:Handle  '
        'Responder:Discard  Mailbox:Noted  Responder:Ignored  Triage:Nothing  '
        'Owner:Check  Triage:Fetch  Mailbox:Thread  Triage:Handle  '
        'Responder:Save  Mailbox:Stored  Responder:Drafted  Triage:Draft  '
        'Owner:Check  Triage:Fetch  Mailbox:Empty  Triage:Rest  '
        'Responder:Idle  Mailbox:Noted  Responder:Quiet  Triage:Idle'
    ),
}

# Offline files: exit 0 only (mechanisms + projection_error + choreography twins).
SMOKE_ONLY = {
    'resume.py',
    'cancellation.py',
    'toolbox.py',
    'projection_error.py',
    'hello_chor.py',
    'revise_until_ok_chor.py',
    'chain_chor.py',
    'parallel_chor.py',
    'times_chor.py',
}

HEADERS_CATALOG = (
    '=== protocol ===',
    '=== duties ===',
    '=== session ===',
    '=== skeleton ===',
)

# projection_error has its own sections.
HEADERS_PROJECTION = ('=== protocol ===', '=== project ===')


@dataclass(frozen=True, slots=True)
class _ProcessResult:
    returncode: int
    stdout: str
    stderr: str


def _offline_py_files() -> set[str]:
    return {p.name for p in OFFLINE.glob('*.py')}


def _online_py_files() -> set[str]:
    return {p.name for p in ONLINE.glob('*.py')}


def test_offline_manifest_is_complete() -> None:
    found = _offline_py_files()
    registered = set(SKELETONS) | SMOKE_ONLY
    assert found == registered, (
        f'offline manifest mismatch: only in files {found - registered!r}; '
        f'only in manifest {registered - found!r}'
    )


ROOT_ONLINE = {'coding_agent.py', 'coding_agent_pro.py'}


def test_online_tree_nonempty() -> None:
    assert 'hello.py' in _online_py_files()
    assert 'main.py' in _online_py_files()
    # The coding-agent harness lives at the examples root; nothing else does.
    root_py = {p.name for p in EXAMPLES.glob('*.py')}
    assert root_py == ROOT_ONLINE, f'unexpected root examples: {root_py}'


async def _run(path: Path) -> _ProcessResult:
    return await _run_command(sys.executable, str(path), cwd=ROOT, timeout=180)


async def _run_command(
    *args: str,
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
) -> _ProcessResult:
    return await _run_command_async(*args, cwd=cwd, timeout=timeout, env=env)


async def _run_command_async(
    *args: str,
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
) -> _ProcessResult:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise
    return _ProcessResult(process.returncode or 0, stdout.decode(), stderr.decode())


def _skeleton_line(stdout: str) -> str:
    lines = stdout.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == '=== skeleton ===':
            for following in lines[index + 1 :]:
                if following.strip():
                    return following.strip()
            return ''
    return ''


@pytest.mark.parametrize('name', sorted(SMOKE_ONLY))
async def test_offline_smoke_exit_zero(name: str) -> None:
    result = await _run(OFFLINE / name)
    assert result.returncode == 0, result.stderr or result.stdout
    if name == 'projection_error.py':
        for header in HEADERS_PROJECTION:
            assert header in result.stdout, f'missing {header!r}'
        assert 'ProjectionError' in result.stdout
        assert 'no model was called' in result.stdout


@pytest.mark.parametrize('name', sorted(SKELETONS))
async def test_offline_catalog_example(name: str) -> None:
    result = await _run(OFFLINE / name)
    assert result.returncode == 0, result.stderr or result.stdout
    for header in HEADERS_CATALOG:
        assert header in result.stdout, f'missing {header!r} in {name}'
    assert _skeleton_line(result.stdout) == SKELETONS[name], (
        f'skeleton mismatch for {name}:\n'
        f'  got:      {_skeleton_line(result.stdout)!r}\n'
        f'  expected: {SKELETONS[name]!r}'
    )


def _load_module(path: Path):
    # Unique name avoids collisions across example files (all are scripts).
    mod_name = f'agentsparty_examples_online_{path.stem}'
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses/pydantic need the module registered before exec.
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    return module


def _protocols_of(module) -> list:
    found = [
        getattr(module, name)
        for name in ('protocol', 'PROTO', 'proto', 'GATE', 'PIPELINE', 'BROKEN')
        if hasattr(module, name)
    ]
    if hasattr(module, 'build_protocol'):
        result = module.build_protocol()
        # main.py returns roles + proto
        if isinstance(result, tuple):
            found.append(result[-1])
        else:
            found.append(result)
    return found


@pytest.mark.parametrize(
    'path',
    [
        *(ONLINE / name for name in sorted(_online_py_files())),
        *(EXAMPLES / name for name in sorted(ROOT_ONLINE)),
    ],
)
def test_online_import_and_project(path: Path) -> None:
    """Cheap CI invariant: import + project_all without a live model call."""
    name = path.name
    if name in {'surprise_trip.py', 'main.py'}:
        pytest.importorskip('pydantic')
    if name == 'stock_analysis.py':
        pytest.importorskip('msgspec')
    if name == 'coding_agent_pro.py':
        pytest.importorskip('textual')

    # Avoid constructing models at import: modules should only construct
    # models inside build()/main(). If import requires a key,
    # that is a bug in the example layout.
    module = _load_module(path)
    protos = _protocols_of(module)
    assert protos, f'{name}: no PROTO/proto/GATE/PIPELINE for project_all'
    from agentsparty.protocol import project_all

    for proto in protos:
        project_all(proto)


async def test_missing_openai_key_fails_fast() -> None:
    env = {k: v for k, v in __import__('os').environ.items() if k != 'OPENAI_API_KEY'}
    result = await _run_command(
        sys.executable,
        str(ONLINE / 'hello.py'),
        cwd=ROOT,
        timeout=60,
        env=env,
    )
    assert result.returncode == 1
    assert "KeyError: 'OPENAI_API_KEY'" in result.stderr
