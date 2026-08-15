from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / 'src' / 'par_ai'


def _py_files() -> list[Path]:
    return sorted(SRC.rglob('*.py'))


def test_isinstance_only_in_raw() -> None:
    offenders: list[str] = []
    for path in _py_files():
        text = path.read_text(encoding='utf-8')
        if path.relative_to(SRC) == Path('protocol/language/raw.py'):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if 'isinstance' in line and not line.lstrip().startswith('#'):
                offenders.append(f'{path.relative_to(SRC)}:{i}:{line.strip()}')
    assert offenders == [], 'isinstance outside raw.py:\n' + '\n'.join(offenders)
