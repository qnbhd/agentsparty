#!/usr/bin/env python3
"""
mutmut_redundancy.py — find redundant or weaker pytest tests from a mutmut
kill matrix (mutmut >= 3.x).

Idea
----
mutmut 3 copies the project into ./mutants/, where each function has mutant
variants and MUTANT_UNDER_TEST selects the active one. A single pytest run
then fills one matrix row: which tests failed (killed the mutant) and which
did not.

From kills[test] = {mutants} the script reports:
  * tests that kill no mutant              -> deletion candidates;
  * tests with no unique contribution (kills is a subset of the rest);
  * dominated tests: kills(A) subset kills(B) — A is strictly weaker than B;
  * duplicate groups: kills(A) == kills(B);
  * a minimal greedy suite that keeps the same mutation score.

Usage
-----
  pip install "mutmut>=3" pytest
  mutmut run                       # required first run
  mutmut results --all > mutmut_results.txt
  python mutmut_redundancy.py --results-file mutmut_results.txt --jobs 8 --tests tests/unit

Output: redundancy_report.md + kill_matrix.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Mutant names look like: mypkg.mymodule.x_my_func__mutmut_3
MUTANT_TOKEN_RE = re.compile(r'[A-Za-z_][\w.]*__mutmut_\d+')
MUTANT_DEF_RE = re.compile(r'^\s*(?:async\s+)?def\s+([^\s(]+__mutmut_\d+)\s*\(', re.MULTILINE)

# Tiny pytest plugin: write each test outcome to JSONL.
PLUGIN_SRC = """
import json, os

_OUT = os.environ["KILL_MATRIX_OUT"]

def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when in ("setup", "teardown")
                                 and report.outcome == "failed"):
        with open(_OUT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"nodeid": report.nodeid,
                                 "outcome": report.outcome}) + "\\n")
"""


# --------------------------------------------------------------------------- #
# Collect mutant names
# --------------------------------------------------------------------------- #
def mutants_from_results_file(path: Path) -> list[str]:
    """Tolerant parser for `mutmut results` output — extract names only."""
    text = path.read_text(encoding='utf-8', errors='replace')
    return sorted(set(MUTANT_TOKEN_RE.findall(text)))


def mutants_from_scan(mutants_dir: Path) -> list[str]:
    """Fallback: scan generated code and collect mutant names.

    WARNING: the full name format (module.func__mutmut_N) depends on the
    mutmut version. If the script finds no killed mutants, compare with
    `mutmut results` and pass --results-file.
    """
    found: list[str] = []
    for py in mutants_dir.rglob('*.py'):
        rel = py.relative_to(mutants_dir)
        if rel.parts and rel.parts[0] in {'tests', 'test', '.venv', '__pycache__'}:
            continue
        module_parts = rel.with_suffix('').parts
        if module_parts and module_parts[0] == 'src':
            module_parts = module_parts[1:]
        module = '.'.join(module_parts)
        src = py.read_text(encoding='utf-8', errors='replace')
        for name in MUTANT_DEF_RE.findall(src):
            found.append(f'{module}.{name}')
    return sorted(set(found))


def mutants_for_tests(mutants_dir: Path, mutants: list[str], test_paths: list[str]) -> list[str]:
    """Keep mutants whose functions are associated with the selected tests."""
    stats_path = mutants_dir / 'mutmut-stats.json'
    if not stats_path.is_file():
        sys.exit('No mutants/mutmut-stats.json. Run `uv run mutmut run` first.')

    stats = json.loads(stats_path.read_text(encoding='utf-8'))
    associations = stats.get('tests_by_mangled_function_name', {})
    selected = {Path(path.split('::', 1)[0]).as_posix() for path in test_paths}
    selected_functions = {
        function
        for function, associated_tests in associations.items()
        if any(test_matches(path, selected) for path in associated_tests)
    }
    filtered = [
        mutant for mutant in mutants if mutant.partition('__mutmut_')[0] in selected_functions
    ]
    if not filtered:
        sys.exit('Selected tests are not linked to any mutant in mutmut-stats.json.')
    return filtered


def test_matches(nodeid: str, selected_paths: set[str]) -> bool:
    """Return whether a mutmut node id belongs to one of the selected paths."""
    path = Path(nodeid.split('::', 1)[0]).as_posix()
    return any(path == selected or path.startswith(f'{selected}/') for selected in selected_paths)


def stale_snapshot_files(mutants_dir: Path) -> list[str]:
    """Return project files whose copies in ``mutants/`` are stale or absent."""
    project_files = [PROJECT_ROOT / 'pyproject.toml']
    project_files.extend(PROJECT_ROOT.joinpath('tests').rglob('*.py'))
    project_files.extend(PROJECT_ROOT.joinpath('examples').rglob('*.py'))
    stale = []
    for source in project_files:
        relative = source.relative_to(PROJECT_ROOT)
        snapshot = mutants_dir / relative
        if not snapshot.is_file() or snapshot.read_bytes() != source.read_bytes():
            stale.append(relative.as_posix())
    return stale


# --------------------------------------------------------------------------- #
# Run pytest
# --------------------------------------------------------------------------- #
def base_pytest_cmd(args) -> list[str]:
    cmd = [
        sys.executable,
        '-m',
        'pytest',
        '-p',
        'no:cacheprovider',
        '-p',
        'no:randomly',
        '-p',
        'kill_matrix_plugin',
        '--tb=no',
        '-q',
    ]
    if args.assert_plain:
        cmd.append('--assert=plain')
    if args.pytest_timeout:
        cmd += ['--timeout', str(args.pytest_timeout)]
    cmd += [*args.test_paths, *args.pytest_args]
    return cmd


def collect_tests(args, env: dict) -> list[str]:
    out = subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            '--collect-only',
            '-q',
            '-p',
            'no:cacheprovider',
            *args.test_paths,
            *args.pytest_args,
        ],
        cwd=args.mutants_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    tests = [ln.strip() for ln in out.stdout.splitlines() if '::' in ln and not ln.startswith(' ')]
    if not tests:
        sys.exit('Could not collect tests:\n' + out.stdout + out.stderr)
    return tests


def run_suite(args, env_extra: dict, plugin_dir: Path) -> tuple[dict[str, str], bool]:
    """Run the whole suite once. Return (nodeid -> outcome, timed_out)."""
    with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False) as tmp:
        out_path = Path(tmp.name)

    env = os.environ.copy()
    mutant_root = args.mutants_dir.resolve()
    pythonpath = [str(plugin_dir), str(mutant_root / 'src'), str(mutant_root)]
    if env.get('PYTHONPATH'):
        pythonpath.append(env['PYTHONPATH'])
    env['PYTHONPATH'] = os.pathsep.join(pythonpath)
    env['KILL_MATRIX_OUT'] = str(out_path)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env.update(env_extra)

    timed_out = False
    try:
        subprocess.run(
            base_pytest_cmd(args),
            cwd=args.mutants_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        timed_out = True

    outcomes: dict[str, str] = {}
    if out_path.exists():
        for line in out_path.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            prev = outcomes.get(rec['nodeid'])
            if prev != 'failed':
                outcomes[rec['nodeid']] = rec['outcome']
        out_path.unlink(missing_ok=True)
    return outcomes, timed_out


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def analyse(kills: dict[str, set[str]]) -> dict:
    all_killed = set().union(*kills.values()) if kills else set()

    zero = sorted(t for t, m in kills.items() if not m)
    non_empty = {t: m for t, m in kills.items() if m}

    no_unique, unique_map = [], {}
    for t, m in non_empty.items():
        others = (
            set().union(*(x for k, x in non_empty.items() if k != t))
            if len(non_empty) > 1
            else set()
        )
        uniq = m - others
        unique_map[t] = sorted(uniq)
        if not uniq:
            no_unique.append(t)

    dominated, duplicates = {}, defaultdict(list)
    items = list(non_empty.items())
    for t, m in items:
        duplicates[frozenset(m)].append(t)
        doms = [t2 for t2, m2 in items if t2 != t and m < m2]
        if doms:
            dominated[t] = sorted(doms)

    # Greedy cover of every killed mutant
    remaining, chosen = set(all_killed), []
    pool = dict(non_empty)
    while remaining:
        best = max(pool, key=lambda t: (len(pool[t] & remaining), t), default=None)
        if best is None or not (pool[best] & remaining):
            break
        chosen.append(best)
        remaining -= pool[best]
        pool.pop(best)

    return {
        'total_tests': len(kills),
        'total_killed_mutants': len(all_killed),
        'zero_kill_tests': zero,
        'tests_without_unique_kills': sorted(no_unique),
        'unique_kills': {t: v for t, v in unique_map.items() if v},
        'dominated_tests': dominated,
        'duplicate_groups': [sorted(g) for g in duplicates.values() if len(g) > 1],
        'minimal_greedy_suite': chosen,
        'removable_candidates': sorted(set(zero) | set(kills) - set(chosen)),
    }


def render_md(res: dict, kills: dict[str, set[str]]) -> str:
    L: list[str] = ['# Report: redundant tests by mutation analysis', '']
    L += [
        f'- Tests analysed: **{res["total_tests"]}**',
        f'- Killed mutants (counted in the analysis): **{res["total_killed_mutants"]}**',
        f'- Minimal greedy suite: **{len(res["minimal_greedy_suite"])}** tests '
        f'keep the same mutation score',
        '',
    ]

    def block(title: str, items, fmt=lambda x: f'- `{x}`'):
        L.append(f'## {title} ({len(items)})')
        L.extend(fmt(i) for i in items) if items else L.append('_none_')
        L.append('')

    block('Tests that killed no mutant', res['zero_kill_tests'])
    block(
        'Tests with no unique contribution (fully covered by others)',
        res['tests_without_unique_kills'],
    )
    L.append(f'## Strictly dominated tests ({len(res["dominated_tests"])})')
    if res['dominated_tests']:
        for t, doms in sorted(res['dominated_tests'].items()):
            L.append(
                f'- `{t}` ({len(kills[t])} mutants) is weaker than: '
                + ', '.join(f'`{d}`' for d in doms[:5])
                + (' …' if len(doms) > 5 else '')
            )
    else:
        L.append('_none_')
    L.append('')
    L.append(f'## Test groups with an identical kill set ({len(res["duplicate_groups"])})')
    for g in res['duplicate_groups']:
        L.append('- ' + ', '.join(f'`{t}`' for t in g))
    if not res['duplicate_groups']:
        L.append('_none_')
    L += ['', '## Minimal greedy suite', '']
    L += [f'- `{t}` (+{len(kills[t])})' for t in res['minimal_greedy_suite']]
    L += [
        '',
        '---',
        '',
        '> The report measures redundancy **only by mutant kills**. '
        'A test can still be valuable as documentation, a bug regression, '
        'a contract check, a performance check, or an integration test. '
        'Equivalent mutants are also possible. Delete tests by hand.',
    ]
    return '\n'.join(L)


# --------------------------------------------------------------------------- #
def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        '--mutants-dir',
        type=Path,
        default=Path('mutants'),
        help='directory created by mutmut (default ./mutants)',
    )
    p.add_argument(
        '--results-file', type=Path, help='file with `mutmut results --all` output (recommended)'
    )
    p.add_argument(
        '--limit', type=int, default=0, help='use only the first N mutants (for a trial run)'
    )
    p.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
    p.add_argument(
        '--timeout', type=float, default=300, help='timeout for one full-suite run, seconds'
    )
    p.add_argument(
        '--pytest-timeout',
        type=float,
        default=None,
        help='pass --timeout to pytest (requires pytest-timeout)',
    )
    p.add_argument(
        '--assert-plain',
        action='store_true',
        help='add --assert=plain (faster, as mutmut does)',
    )
    p.add_argument('--out-prefix', default='.')
    p.add_argument(
        '--tests',
        dest='test_paths',
        nargs='+',
        default=[],
        metavar='PATH',
        help='test directory or file; may be given more than once',
    )
    p.add_argument(
        'pytest_args',
        nargs='*',
        help='extra pytest arguments; a test path may go here instead of --tests',
    )
    args = p.parse_args()

    if not args.mutants_dir.is_dir():
        sys.exit(f'No directory {args.mutants_dir}. Run `mutmut run` first.')
    stale = stale_snapshot_files(args.mutants_dir)
    if stale:
        sys.exit(
            'The mutants directory is stale or incomplete. '
            'After project changes, run `uv run mutmut run` first.\n'
            'First mismatch: ' + stale[0]
        )

    plugin_dir = Path(tempfile.mkdtemp(prefix='killmatrix_'))
    (plugin_dir / 'kill_matrix_plugin.py').write_text(PLUGIN_SRC, encoding='utf-8')

    mutants = (
        mutants_from_results_file(args.results_file)
        if args.results_file
        else mutants_from_scan(args.mutants_dir)
    )
    if not mutants:
        sys.exit('No mutants found.')
    if args.test_paths:
        mutants = mutants_for_tests(args.mutants_dir, mutants, args.test_paths)
    if args.limit:
        mutants = mutants[: args.limit]
    print(f'Mutants to check: {len(mutants)}')

    # 1. Baseline run: without a mutant everything must be green.
    base, base_timeout = run_suite(args, {'MUTANT_UNDER_TEST': ''}, plugin_dir)
    if base_timeout:
        sys.exit('Baseline run exceeded --timeout.')
    broken = sorted(t for t, o in base.items() if o == 'failed')
    if broken:
        sys.exit('Tests fail before mutations — fix those first:\n  ' + '\n  '.join(broken[:20]))
    tests = sorted(base)
    if not tests:
        sys.exit('Pytest collected no tests in the mutants directory.')
    print(f'Tests in the baseline run: {len(tests)}')

    # 2. One suite run per mutant -> one matrix row.
    kills: dict[str, set[str]] = {t: set() for t in tests}
    survived, timeouts, done = [], [], 0

    def work(mut: str):
        outcomes, to = run_suite(args, {'MUTANT_UNDER_TEST': mut}, plugin_dir)
        return mut, outcomes, to

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for mut, outcomes, to in pool.map(work, mutants):
            done += 1
            killers = [t for t, o in outcomes.items() if o == 'failed']
            if to:
                timeouts.append(mut)  # hang = killed, but without attribution
            elif not killers:
                survived.append(mut)
            for t in killers:
                kills.setdefault(t, set()).add(mut)
            print(
                f'[{done}/{len(mutants)}] {mut}: '
                f'{"timeout" if to else (f"killed by {len(killers)} tests" if killers else "SURVIVED")}',
                flush=True,
            )

    if not any(kills.values()):
        sys.exit(
            'No mutant was killed — mutant names or the directory are probably wrong. '
            'Compare with `mutmut results` and pass --results-file.'
        )

    res = analyse(kills)
    res['survived_mutants'] = sorted(survived)
    res['timeout_mutants'] = sorted(timeouts)

    out = Path(args.out_prefix)
    (out / 'kill_matrix.json').write_text(
        json.dumps(
            {'kills': {t: sorted(m) for t, m in kills.items()}, 'analysis': res},
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )
    (out / 'redundancy_report.md').write_text(render_md(res, kills), encoding='utf-8')
    print('\nDone: redundancy_report.md, kill_matrix.json')


if __name__ == '__main__':
    main()
