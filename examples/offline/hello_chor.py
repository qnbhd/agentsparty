# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Choreography twin of examples/online/hello.py (facade B).

``equal_session`` against the combinator ``protocol`` is checked here and in
``tests/choreography/test_equivalence.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'online'))

from hello import (  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]
    Ack,
    Note,
    Reviewer,
    Writer,
    protocol,
)

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import ensure_session, equal_session


@pa.choreography
def hello(c: pa.Chor) -> None:
    c.say(Writer, Reviewer, Note)
    c.say(Reviewer, Writer, Ack)


def main() -> None:
    assert equal_session(ensure_session(protocol), hello())
    assert equal_session(hello(), hello())
    report = debug.Report()
    report.protocol(hello(), title='choreography')


if __name__ == '__main__':
    main()
