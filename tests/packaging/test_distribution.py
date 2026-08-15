"""Build-backend packaging gates for the agentsparty distribution.

Propositions:

1. ``uv build`` (hatchling) produces both an sdist and a wheel for ``agentsparty``.
2. Every non-cache source file under ``src/agentsparty`` is present in the wheel,
   including ``py.typed``.
3. The wheel does not ship non-package repo material (tests, docs, caches, …).
4. The sdist ships exactly the build inputs — sources plus the files the
   metadata points at — and no docs site, tool cache or agent configuration.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_PACKAGE = ROOT / 'src' / 'agentsparty'

# Paths that must never appear inside the installable wheel.
WHEEL_JUNK_MARKERS = (
    '__pycache__',
    '.pyc',
    'tests/',
    'docs/',
    'htmlcov/',
    'unrs/',
    'examples/',
    'noxfile',
    'justfile',
    '.hypothesis',
)

# Everything the sdist is allowed to carry, as top-level names under the
# ``agentsparty-<version>/`` root. Hatchling force-includes PKG-INFO and the VCS
# ignore file so the tarball can rebuild identically; the rest is the
# allow-list from [tool.hatch.build.targets.sdist].
SDIST_ALLOWED_ROOTS = frozenset({
    'src',
    'README.md',
    'CHANGELOG.md',
    'LICENSE',
    'pyproject.toml',
    'PKG-INFO',
    '.gitignore',
})


@dataclass(frozen=True, slots=True)
class _BuildResult:
    returncode: int
    stdout: str
    stderr: str


def _package_source_files() -> set[str]:
    """Relative package paths that the wheel must ship (posix, under agentsparty/)."""
    files: set[str] = set()
    for path in SRC_PACKAGE.rglob('*'):
        if not path.is_file():
            continue
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        rel = path.relative_to(SRC_PACKAGE.parent).as_posix()
        files.add(rel)
    return files


async def _build_artifacts(out_dir: Path) -> tuple[Path, Path]:
    """Run the project build toolchain into *out_dir*; return (sdist, wheel)."""
    uv = shutil.which('uv')
    assert uv is not None, 'uv is required to build the package'
    result = await _build_with_uv(uv, out_dir)
    assert result.returncode == 0, (
        f'uv build failed ({result.returncode})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    )
    sdists = sorted(out_dir.glob('*.tar.gz'))  # noqa: ASYNC240
    wheels = sorted(out_dir.glob('*.whl'))  # noqa: ASYNC240
    assert sdists, f'no sdist under {out_dir}; stdout:\n{result.stdout}'
    assert wheels, f'no wheel under {out_dir}; stdout:\n{result.stdout}'
    return sdists[0], wheels[0]


async def _build_with_uv(uv: str, out_dir: Path) -> _BuildResult:
    process = await asyncio.create_subprocess_exec(
        uv,
        'build',
        '--out-dir',
        str(out_dir),
        cwd=ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return _BuildResult(process.returncode or 0, stdout.decode(), stderr.decode())


@pytest.fixture(scope='module')
async def built_dist(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Build once per module; packaging is slow relative to unit tests."""
    out = tmp_path_factory.mktemp('agentsparty-dist')
    return await _build_artifacts(out)


def test_build_produces_agentsparty_sdist_and_wheel(built_dist: tuple[Path, Path]) -> None:
    sdist, wheel = built_dist
    assert sdist.name.startswith('agentsparty-') or sdist.name.startswith('agentsparty-')
    assert wheel.name.startswith('agentsparty-') or wheel.name.startswith('agentsparty-')
    assert 'agentsparty' in wheel.name or 'agentsparty' in wheel.name


def test_wheel_contains_full_package_tree(built_dist: tuple[Path, Path]) -> None:
    _, wheel = built_dist
    expected = _package_source_files()
    assert expected, 'src/agentsparty source tree is empty'
    assert 'agentsparty/py.typed' in expected

    with zipfile.ZipFile(wheel) as zf:
        members = set(zf.namelist())

    missing = expected - members
    assert not missing, f'wheel missing package files: {sorted(missing)}'


def test_wheel_excludes_non_package_junk(built_dist: tuple[Path, Path]) -> None:
    _, wheel = built_dist
    with zipfile.ZipFile(wheel) as zf:
        members = zf.namelist()

    for marker in WHEEL_JUNK_MARKERS:
        hits = [m for m in members if marker in m]
        assert not hits, f'wheel contains junk matching {marker!r}: {hits}'

    # Only the package tree and dist-info metadata.
    for member in members:
        assert member.startswith('agentsparty/') or '.dist-info/' in member, member


def test_sdist_includes_package_sources(built_dist: tuple[Path, Path]) -> None:
    """Sdist may ship extra project files; the library sources must still be present."""
    sdist, _ = built_dist
    expected = {f'src/{path}' for path in _package_source_files()}
    with tarfile.open(sdist, 'r:gz') as tf:
        # Members are rooted under agentsparty-<version>/
        members = set()
        for name in tf.getnames():
            parts = Path(name).parts
            if len(parts) >= 2 and parts[1] == 'src':
                members.add('/'.join(parts[1:]))
    missing = expected - members
    assert not missing, f'sdist missing package sources: {sorted(missing)}'


def test_sdist_ships_only_build_inputs(built_dist: tuple[Path, Path]) -> None:
    """A source distribution, not a mirror of the repository."""
    sdist, _ = built_dist
    with tarfile.open(sdist, 'r:gz') as tf:
        # Members are rooted under agentsparty-<version>/; take the name below it.
        roots = {Path(name).parts[1] for name in tf.getnames() if len(Path(name).parts) >= 2}
        sources = {name for name in tf.getnames() if '/src/' in name}

    unexpected = roots - SDIST_ALLOWED_ROOTS
    assert not unexpected, f'sdist ships repo material it does not need: {sorted(unexpected)}'
    assert not any('__pycache__' in name or name.endswith('.pyc') for name in sources)


def test_installed_package_exposes_py_typed_and_public_modules() -> None:
    """Structural check on the importable tree used by the running test env."""
    import importlib

    import agentsparty

    root = Path(agentsparty.__file__).resolve().parent
    assert (root / 'py.typed').is_file()

    public = [
        'agentsparty',
        'agentsparty.protocol',
        'agentsparty.participant',
        'agentsparty.agent',
        'agentsparty.human',
        'agentsparty.journal',
        'agentsparty.runtime',
        'agentsparty.llm',
        'agentsparty.kernel',
        'agentsparty.kernel.budget',
        'agentsparty.kernel.console',
        'agentsparty.kernel.errors',
        'agentsparty.kernel.nonempty',
        'agentsparty.kernel.role',
        'agentsparty.protocol.language',
        'agentsparty.protocol.language.core',
        'agentsparty.protocol.language.endpoint',
        'agentsparty.protocol.language.raw',
    ]
    for name in public:
        mod = importlib.import_module(name)
        assert mod is not None

    for pkg_name in ('agentsparty.protocol', 'agentsparty.llm'):
        pkg = importlib.import_module(pkg_name)
        for attr in pkg.__all__:
            assert hasattr(pkg, attr), f'{pkg_name}.{attr} not exported'


def test_wheel_metadata_has_license_and_no_placeholder_description(
    built_dist: tuple[Path, Path],
) -> None:
    """Release packaging: MIT license metadata and a real description."""
    _, wheel = built_dist
    with zipfile.ZipFile(wheel) as zf:
        metadata_name = next(n for n in zf.namelist() if n.endswith('.dist-info/METADATA'))
        metadata = zf.read(metadata_name).decode('utf-8')
        license_files = [
            n for n in zf.namelist() if 'licenses/' in n.lower() or n.endswith('LICENSE')
        ]
    assert 'License: MIT' in metadata or 'License-Expression: MIT' in metadata
    assert 'Add your description here' not in metadata
    assert 'Declarative multiparty session protocols for AI agents' in metadata
    assert 'Classifier: Programming Language :: Python :: 3.10' in metadata
    assert 'Classifier: Programming Language :: Python :: 3.13' in metadata
    assert 'Home-page:' in metadata or 'Project-URL: Homepage' in metadata
    assert license_files or 'License-File:' in metadata
    assert 'Requires-Python: >=3.10' in metadata
    assert 'github.com/qnbhd/agentsparty' in metadata
    assert 'qnbhd.github.io/agentsparty' in metadata
    assert 'gitlab' not in metadata.lower()
    assert 'unte' not in metadata
    assert 'Provides-Extra: openai' in metadata


def test_install_smoke_uses_current_text_codec() -> None:
    """The wheel-smoke session must import Text, not the removed TEXT binding."""
    source = (ROOT / 'noxfile.py').read_text(encoding='utf-8')
    assert 'from agentsparty.protocol import Text, msg' in source
    assert 'import TEXT' not in source
    assert ', TEXT' not in source


async def test_core_does_not_require_openai() -> None:
    """Core package imports without pulling the OpenAI SDK (L4).

    The dev environment installs ``openai`` for the optional extra, so an
    in-process import would succeed even if the SDK were a hard dependency.
    A child interpreter reports what the import actually loaded instead.
    """
    probe = (
        'import agentsparty, agentsparty.protocol, agentsparty.agent, agentsparty.llm, sys;'
        'from agentsparty.llm import ScriptedLanguageModel;'
        'assert ScriptedLanguageModel is not None;'
        "print('openai' in sys.modules)"
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        '-c',
        probe,
        cwd=ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    assert process.returncode == 0, f'core import failed:\n{stderr.decode()}'
    assert stdout.decode().strip() == 'False', 'importing agentsparty loaded the OpenAI SDK'


async def test_offline_primary_path_scripted_humans() -> None:
    """Primary offline behavior via the real Human / AgentRuntime entry points.

    The README doctest exercises the same choreography for documentation;
    this test pins the concrete trace so a packaging/import regression fails
    the suite even when doctests are skipped.
    """

    from agentsparty.human import Human, ScriptedHumanIo
    from agentsparty.kernel.role import roles
    from agentsparty.participant import Choice
    from agentsparty.protocol import Label, Text, msg, render
    from agentsparty.runtime import AgentRuntime

    Client, Server = roles('Client', 'Server')
    proto = (msg[Client, Server]('Request', Text) >> msg[Server, Client]('Reply', Text)).close()
    assert 'Request(str)' in render(proto)
    client = Human(Client, proto, ScriptedHumanIo([Choice(Label('Request'), 'ping')]))
    server = Human(Server, proto, ScriptedHumanIo([Choice(Label('Reply'), 'pong')]))
    trace = await AgentRuntime(proto, [client, server]).run()
    result = [(e.sender.name, e.receiver.name, str(e.label), e.payload) for e in trace]
    assert result == [
        ('Client', 'Server', 'Request', 'ping'),
        ('Server', 'Client', 'Reply', 'pong'),
    ]
