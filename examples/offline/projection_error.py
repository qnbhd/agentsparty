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

import agentsparty as pa
from agentsparty import debug
from agentsparty.protocol import alt, msg, project

A, B, C = pa.roles('A', 'B', 'C')


# C never sees the alt, yet the branches treat C differently — illegal.


Yes = pa.Nothing('Yes')
Y = pa.Text('Y')
No = pa.Nothing('No')
N = pa.Text('N')

BROKEN = alt[A, B](
    Yes >> msg[A, C](Y),
    No >> msg[C, A](N),
).close()


def main() -> None:
    report = debug.Report()
    report.protocol(BROKEN)
    with report.refusing(pa.ProjectionError, title='project'):
        project(BROKEN, C)
    report.note('no model was called', title='result')


if __name__ == '__main__':
    main()
