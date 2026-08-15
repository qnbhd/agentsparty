# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Projection refuses a silent third role — before any model call.

What you will see (exact):
  === protocol ===
  (broken alt rendered)
  === project ===
  ProjectionError: role 'C' cannot tell 'Yes' from 'No' ...
  === result ===
  no model was called

No language model is constructed. The failure is pure protocol projection.

Run::

    uv run python examples/offline/projection_error.py
"""

from __future__ import annotations

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import alt, msg, project

A, B, C = ap.roles('A', 'B', 'C')


# C never sees the alt, yet the branches treat C differently — illegal.


Yes = ap.Nothing('Yes')
Y = ap.Text('Y')
No = ap.Nothing('No')
N = ap.Text('N')

BROKEN = alt[A, B](
    Yes >> msg[A, C](Y),
    No >> msg[C, A](N),
).close()


def main() -> None:
    report = debug.Report()
    report.protocol(BROKEN)
    with report.refusing(ap.ProjectionError, title='project'):
        project(BROKEN, C)
    report.note('no model was called', title='result')


if __name__ == '__main__':
    main()
