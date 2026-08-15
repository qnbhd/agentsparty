# /// script
# requires-python = ">=3.10"
# dependencies = ["agentsparty"]
# ///
"""Choreography twin of revise_until_ok (facade B): loop + decide as indentation.

Uses ``c.loop("draft")`` so the binder matches the combinator twin's
``rec("draft", …)`` — ``equal_session`` against ``revise_until_ok.protocol`` holds.
"""

from __future__ import annotations

# Same message declarations and roles as the combinator example.
from revise_until_ok import (
    Abandoned,
    Again,
    Bard,
    Closed,
    Critic,
    Done,
    Editor,
    Final,
    GiveUp,
    Length,
    Measure,
    Meter,
    Ok,
    Post,
    Retrying,
    Revise,
    Topic,
)

import agentsparty as ap
from agentsparty import debug
from agentsparty.protocol import equal_session


@ap.choreography
def revise(c: ap.Chor) -> None:
    c.say(Editor, Bard, Topic)
    with c.loop('draft') as draft:
        c.say(Bard, Meter, Measure)
        c.say(Meter, Bard, Length)
        c.say(Bard, Critic, Post)
        with c.decide(Critic, Bard) as verdict:
            with verdict.case(Ok):
                c.say(Bard, Meter, Done)
                c.say(Meter, Bard, Closed)
                c.say(Bard, Editor, Final)
            with verdict.case(Revise):
                c.say(Bard, Meter, Again)
                c.say(Meter, Bard, Closed)
                c.say(Bard, Editor, Retrying)
                draft.again()
            with verdict.case(GiveUp):
                c.say(Bard, Meter, Done)
                c.say(Meter, Bard, Closed)
                c.say(Bard, Editor, Abandoned)


def main() -> None:
    protocol = revise()
    assert equal_session(protocol, protocol)
    assert equal_session(revise(), revise())
    report = debug.Report()
    report.protocol(protocol, title='choreography')


if __name__ == '__main__':
    main()
