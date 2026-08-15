"""Compare the current public package with its previous Git revision."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ADR 0048 records this pre-1.0 public removal. Keep the allow-list narrow so
# an unrelated API break still fails the documentation gate.
EXPECTED_REMOVALS = (
    'title=participants::Public object was removed',
    'file=src/agentsparty/protocol/__init__.py,line=0,title=tx::Public object was removed',
    'file=src/agentsparty/protocol/session/__init__.py,line=0,title=tx::Public object was removed',
)


def main() -> None:
    try:
        subprocess.run(
            ['git', 'rev-parse', '--verify', 'HEAD~1'],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        print('skipped API breakage check: no previous Git revision')
        return

    result = subprocess.run(
        [
            'uv',
            'run',
            'griffe',
            'check',
            'agentsparty',
            '--search',
            'src',
            '--no-inspection',
            '--verbose',
            '--format',
            'github',
            '--against',
            'HEAD~1',
            '--base-ref',
            'HEAD',
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(result.stdout, end='')
        return

    diagnostics = '\n'.join(filter(None, (result.stdout, result.stderr)))
    unexpected = [
        line
        for line in diagnostics.splitlines()
        if line and not any(marker in line for marker in EXPECTED_REMOVALS)
    ]
    if unexpected or not diagnostics.strip():
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    print('accepted approved API removals from ADR 0048:')
    print(diagnostics, end='\n' if not diagnostics.endswith('\n') else '')


if __name__ == '__main__':
    main()
