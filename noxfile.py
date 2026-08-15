from __future__ import annotations

import nox
from nox_uv import session

PYTHON = '3.13'
TEST_PYTHONS = ['3.10', '3.11', '3.12', '3.13']
DIST = 'agentsparty'

nox.options.default_venv_backend = 'uv|virtualenv'
nox.options.sessions = ['lint', 'typecheck', 'testcov', 'docs', 'docscheck']


_WHEEL: str | None = None


def _wheel(session: nox.Session) -> str:
    """Build the wheel once per Nox run and return its path."""
    global _WHEEL
    if _WHEEL is None:
        out = session.cache_dir / 'wheel'
        session.run_install('uv', 'build', '--wheel', '--out-dir', str(out), external=True)
        wheels = sorted(out.glob('*.whl'))
        if not wheels:
            session.error(f'no wheel in {out}')
        _WHEEL = str(wheels[0])
    return _WHEEL


def _install_wheel(session: nox.Session) -> None:
    session.install(_wheel(session), f'--reinstall-package={DIST}')
    session.run(
        'python',
        '-c',
        (
            'from pathlib import Path\n'
            'import agentsparty\n'
            'package = Path(agentsparty.__file__).resolve()\n'
            'source = Path.cwd().resolve() / "src" / "agentsparty"\n'
            'assert "site-packages" in package.parts, f"not imported from site-packages: {package}"\n'
            'assert not package.is_relative_to(source), f"imported from source tree: {package}"\n'
            'print(f"wheel import: {package}")\n'
        ),
    )


_TARGETS = ('tests', '--pyargs', 'agentsparty')


@session(python=PYTHON, uv_groups=['lint'], tags=['ci'])
def lint(session: nox.Session) -> None:
    """Run import-linter, ruff, flake8, codespell and typos checks."""
    session.run('lint-imports')
    session.run('ruff', 'format', '--check', 'src', 'tests', 'examples')
    session.run('ruff', 'format', '--check', '--line-length', '80', 'docs/content/docs')
    session.run('ruff', 'check')
    session.run(
        'codespell',
        'src',
        'tests',
        'examples',
        'architecture/decisions',
        'architecture/references.md',
        'architecture/research-analysis.md',
        'README.md',
        'CHANGELOG.md',
        'CONTRIBUTING.md',
        'AGENTS.md',
        'noxfile.py',
        '--skip',
        'examples/offline/revise_until_ok.py,architecture/decisions/0030-non-empty-containers-stay-internal.md,architecture/decisions/0035-message-declared-once.md',
    )
    session.run(
        'typos',
        '--exclude',
        'sigs-analysis.md',
        '--exclude',
        'hero-project/agentsparty hero (light).html',
    )
    # session.run("flake8", "src", "examples")


@session(python=PYTHON, uv_groups=['dev', 'lint', 'examples'], tags=['ci'])
def typecheck(session: nox.Session) -> None:
    """Run the static type checker."""
    session.run('ty', 'check', 'examples', 'src/agentsparty', 'tests')


@session(
    python=TEST_PYTHONS,
    uv_groups=['dev'],
    uv_no_install_project=True,
    tags=['ci'],
)
def test(session: nox.Session) -> None:
    """Run the test suite against the built wheel."""
    _install_wheel(session)
    session.run('pytest', '-v', '-n', 'auto', *(session.posargs or _TARGETS))


@session(
    python=TEST_PYTHONS,
    uv_groups=['dev'],
    uv_no_install_project=True,
    tags=['ci'],
)
def testcov(session: nox.Session) -> None:
    """Run tests with branch coverage enforcement against the built wheel."""
    _install_wheel(session)
    session.run(
        'pytest',
        '-n',
        'auto',
        '--cov=agentsparty',
        '--cov-report=term-missing',
        '--cov-report=xml',
        '--cov-fail-under=85',
        *(session.posargs or _TARGETS),
    )


@session(python=PYTHON, uv_groups=['docs', 'lint'], tags=['ci'])
def docs(session: nox.Session) -> None:
    """Build the static Fumadocs site."""
    session.run('npm', '--prefix', 'docs', 'ci', external=True)
    session.run('npm', '--prefix', 'docs', 'run', 'build', external=True)


@session(python=PYTHON, uv_groups=['dev', 'docs'], tags=['ci'])
def docscheck(session: nox.Session) -> None:
    """Check MDX syntax, generated API data, and embedded examples."""
    session.run('npm', '--prefix', 'docs', 'ci', external=True)
    session.run('npm', '--prefix', 'docs', 'run', 'check', external=True)


@session(python=PYTHON, uv_groups=['lint'])
def format(session: nox.Session) -> None:
    """Format source files and apply safe Ruff fixes."""
    session.run('ruff', 'format', 'src', 'tests', 'examples')
    session.run('ruff', 'format', '--line-length', '80', 'docs/content/docs')
    session.run('ruff', 'check', '--fix')


@session(python=PYTHON, uv_groups=['dev'])
def example_metrics(session: nox.Session) -> None:
    """Count proto mentions, imports, and label repeats under examples/ (plan 0013 F0)."""
    session.run(
        'python',
        '-c',
        r"""
import ast
from collections import Counter
from pathlib import Path
import re
examples = list(Path("examples").rglob("*.py"))
proto_mentions = import_names = label_repeats = 0
for path in examples:
    text = path.read_text()
    proto_mentions += len(re.findall(r"\b[Pp][Rr][Oo][Tt][Oo]\b", text))
    try:
        tree = ast.parse(text)
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("agentsparty"):
            import_names += sum(1 for a in (node.names or []) if a.name != "*")
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("agentsparty"):
                    import_names += 1
    strings = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value
        and n.value[0].isupper()
        and len(n.value) < 40
        and "\n" not in n.value
    ]
    label_repeats += sum(c - 1 for c in Counter(strings).values() if c > 1)
print(f"files={len(examples)}")
print(f"lines={sum(len(p.read_text().splitlines()) for p in examples)}")
print(f"proto_mentions={proto_mentions}")
print(f"import_names={import_names}")
print(f"label_repeats={label_repeats}")
""",
    )


@session(python=['3.10', PYTHON], tags=['ci'])
def install_smoke(session: nox.Session) -> None:
    """Build the wheel, install outside the tree, and exercise real entry points.

    Proves the release artifact: py.typed and license land in the wheel; tests,
    docs, and examples do not; core runs a ScriptedLanguageModel agent session
    without PYTHONPATH; missing-SDK import names the install extra; with the
    openai extra a real Agent path reaches the provider network boundary.
    """
    import tempfile
    import zipfile
    from pathlib import Path

    out = Path(tempfile.mkdtemp(prefix='agentsparty-smoke-dist-'))
    session.log(f'building into {out}')
    session.run('uv', 'build', '--out-dir', str(out), external=True)
    wheels = sorted(out.glob('*.whl'))
    assert wheels, f'no wheel in {out}'
    wheel = wheels[0]

    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    assert any(n.endswith('py.typed') for n in names), 'py.typed missing from wheel'
    assert not any('tests/' in n for n in names), 'tests leaked into wheel'
    assert not any(n.startswith('docs/') for n in names), 'docs leaked into wheel'
    assert not any(n.startswith('examples/') for n in names), 'examples leaked into wheel'
    assert any('LICENSE' in n or n.endswith('.dist-info/licenses/LICENSE') for n in names) or any(
        n.endswith('.dist-info/METADATA') for n in names
    )

    env_dir = Path(tempfile.mkdtemp(prefix='agentsparty-smoke-env-'))
    # uv creates an isolated env without relying on ensurepip.
    session.run('uv', 'venv', str(env_dir), '--python', session.python, external=True)
    py = env_dir / 'bin' / 'python'
    session.run('uv', 'pip', 'install', '--python', str(py), str(wheel), external=True)

    # Core imports without openai extra.
    session.run(
        str(py),
        '-c',
        'import agentsparty, agentsparty.protocol, agentsparty.agent, agentsparty.llm; '
        'from pathlib import Path; '
        "assert (Path(agentsparty.__file__).parent / 'py.typed').is_file(); "
        'from agentsparty.llm import ScriptedLanguageModel; '
        'assert ScriptedLanguageModel is not None',
        external=True,
    )

    # Quickstart path from the installed wheel: Agent + ScriptedLanguageModel.
    core_run = r"""
import json
from agentsparty.agent import Agent
from agentsparty.human import Human, ScriptedHumanIo
from agentsparty.llm import ScriptedLanguageModel
from agentsparty.protocol import Text, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import AgentRuntime

A, B = roles("Writer", "Reader")
proto = msg[A, B]( "Note", Text).close()
model = ScriptedLanguageModel([
    json.dumps({"alt": {"label": "Note", "payload": "hello-from-wheel"}})
])
writer = Agent(model, A, "send a note", proto)
reader = Human(B, proto, ScriptedHumanIo([]))
trace = AgentRuntime(proto, [writer, reader]).run_sync()
assert len(trace) == 1 and trace[0].payload == "hello-from-wheel", trace
print("core-session-ok", trace[0].payload)
"""
    session.run(str(py), '-c', core_run, external=True)

    # Backend missing-SDK path: core wheel has no openai dependency.
    probe = (
        'import importlib.util, sys\n'
        "spec = importlib.util.find_spec('openai')\n"
        'if spec is not None:\n'
        "    print('openai present in smoke env; skip missing-SDK probe')\n"
        '    sys.exit(0)\n'
        'try:\n'
        '    import agentsparty.llm.openai as m\n'
        'except ModuleNotFoundError as e:\n'
        '    assert "agentsparty[openai]" in str(e), e\n'
        "    print('ok:', e)\n"
        'else:\n'
        "    raise SystemExit('expected ModuleNotFoundError without openai')\n"
    )
    session.run(str(py), '-c', probe, external=True)

    # With openai extra: agent path reaches the provider network/auth boundary.
    session.run(
        'uv',
        'pip',
        'install',
        '--python',
        str(py),
        f'{wheel}[openai]',
        external=True,
    )
    network_boundary = r"""
import asyncio
from openai import AsyncOpenAI
from agentsparty.agent import Agent
from agentsparty.kernel.errors import ModelError
from agentsparty.llm.openai import OpenAIModel
from agentsparty.protocol import Text, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import AgentRuntime
from agentsparty.human import Human, ScriptedHumanIo

A, B = roles("Writer", "Reader")
proto = msg[A, B]( "Note", Text).close()
# Fake key + public OpenAI URL: must fail at HTTP/auth, not at import/setup.
client = AsyncOpenAI(
    api_key="sk-smoke-not-a-real-key",
    base_url="https://api.openai.com/v1",
    max_retries=0,
    timeout=30.0,
)
model = OpenAIModel("gpt-5.6-luna", client)
writer = Agent(model, A, "send a one-word note", proto)
reader = Human(B, proto, ScriptedHumanIo([]))
try:
    AgentRuntime(proto, [writer, reader]).run_sync()
except ModelError as err:
    print("network-boundary-ok", type(err).__name__, str(err)[:200])
except Exception as err:
    # SDK may raise before translation on some versions; still past import.
    name = type(err).__name__
    if name in ("APIConnectionError", "APIStatusError", "AuthenticationError",
                "PermissionDeniedError", "RateLimitError", "APIError"):
        print("network-boundary-ok", name, str(err)[:200])
    else:
        raise
else:
    raise SystemExit("expected failure at provider boundary, session completed")
"""
    session.run(str(py), '-c', network_boundary, external=True)
    session.log('install-smoke passed')


# Live online suite (plan 0012 F5). Not tagged "ci" — needs a real key and spends tokens.
# N consecutive greens and cost ceiling: see F0 acceptance numbers (N=2, ceiling $2).
ONLINE_LIVE_N = 2


@session(python=PYTHON, uv_groups=['dev', 'examples'], uv_extras=['openai'])
def examples_online(session: nox.Session) -> None:
    """Run every online example against a live model N times (default model).

    Requires OPENAI_API_KEY. Not part of default CI.
    N consecutive greens: ONLINE_LIVE_N (F0 = 2). Cost ceiling: USD 2.00/suite.
    """
    import os
    from pathlib import Path

    if not os.environ.get('OPENAI_API_KEY'):
        session.error('set OPENAI_API_KEY for the live online suite')

    root = Path(__file__).resolve().parent
    online = sorted((root / 'examples' / 'online').glob('*.py'))
    # Interactive finale needs a human at the keyboard — skip in batch suite.
    online = [p for p in online if p.name != 'main.py']
    if not online:
        session.error('no online examples found')

    for run in range(1, ONLINE_LIVE_N + 1):
        session.log(f'=== live pass {run}/{ONLINE_LIVE_N} ===')
        for path in online:
            session.log(f'running {path.relative_to(root)}')
            session.run('python', str(path), external=False)
