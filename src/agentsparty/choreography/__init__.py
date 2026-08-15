"""Choreography facade: build the same ``SessionType`` AST with Python control flow.

This module has **no** own projection, composition, or AST node types. Every
operator calls the existing combinators in :mod:`agentsparty.protocol`. Pair a
choreography with a combinator twin via
:func:`~agentsparty.protocol.session.equal_session`.

**Not in v1** (stay on facade A): external component interfaces
(``owning`` / ``Boundary``), ``compose`` / ``localise``, and consumption
operators on :class:`Located` values.
"""

from agentsparty.choreography.chor import Chor, Located, choreography

__all__ = ['Chor', 'Located', 'choreography']
