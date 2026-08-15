# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Choreography twin: finite unrolling via ``c.times`` (facade B)."""

from __future__ import annotations

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import equal_session, msg, repeat

A, B = pa.roles('A', 'B')


@pa.choreography
def ticks(c: pa.Chor) -> None:
    for _ in c.times(3):
        c.say(A, B, 'Tick')


def main() -> None:
    assert equal_session(ticks(), repeat(3, msg[A, B]('Tick')).close())
    report = debug.Report()
    report.protocol(ticks(), title='choreography')


if __name__ == '__main__':
    main()
