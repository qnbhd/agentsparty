# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Choreography twin: three-party linear chain (facade B)."""

from __future__ import annotations

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import equal_session, msg

A, B, C = ap.roles('A', 'B', 'C')


@ap.choreography
def chain(c: ap.Chor) -> None:
    c.say(A, B, 'One')
    c.say(B, C, 'Two')


def main() -> None:
    assert equal_session(chain(), (msg[A, B]('One') >> msg[B, C]('Two')).close())
    report = debug.Report()
    report.protocol(chain(), title='choreography')


if __name__ == '__main__':
    main()
