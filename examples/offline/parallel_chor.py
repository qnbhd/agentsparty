# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Choreography twin: parallel independent pairs (facade B)."""

from __future__ import annotations

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import equal_session, msg, par

A, B, C, D = ap.roles('A', 'B', 'C', 'D')


@ap.choreography
def split(c: ap.Chor) -> None:
    with c.parallel() as p:
        with p.branch():
            c.say(A, B, 'L')
        with p.branch():
            c.say(C, D, 'R')


def main() -> None:
    assert equal_session(split(), par(msg[A, B]('L'), msg[C, D]('R')).close())
    report = debug.Report()
    report.protocol(split(), title='choreography')


if __name__ == '__main__':
    main()
