"""Shared protocol fixtures for the algebraic tests."""

from __future__ import annotations

from agentsparty.protocol import Integer, Nothing, alt, case, msg, owning, rec, var


def strategy_component(d, ad, s, f1):
    """Return the strategy-department component from research example 3.5."""
    return owning(d, ad).defining(
        msg[d, ad]('prod', Integer)
        >> msg[d, s]('prod', Integer)
        >> msg[d, f1]('prod', Integer)
        >> rec(
            'X',
            alt[f1, d](
                case('ok', Nothing) >> msg[d, ad]('go', Nothing),
                case('wait', Nothing) >> msg[d, ad]('wait', Nothing) >> var('X'),
            ),
        ),
    )
