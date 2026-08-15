# routine (/docs/agentsparty/protocol/routine/index)

Role-parameterised choreographies: ``Routine`` and the ``do`` call.

<Tabs items={["Class","Functions"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"Routine"} href={"/docs/agentsparty/protocol/routine/Routine"} />

</Cards>

</Tab>
<Tab value={"Functions"}>

<PyFunction name={"do"} type={"(routine, *actuals) -> SessionFragment"}>

Call *routine* with *actuals* bound to its parameters, in order.

The result splices into any position: the routine's own roles are renamed,
the caller's continuation is not. ``do`` adds no node to the protocol —
what comes out is an ordinary choreography, so projection, the journal and
replay need to know nothing about routines.

<PySourceCode >

```python
def do(routine: Routine, *actuals: Role) -> SessionFragment:
    """Call *routine* with *actuals* bound to its parameters, in order.

    The result splices into any position: the routine's own roles are renamed,
    the caller's continuation is not. ``do`` adds no node to the protocol —
    what comes out is an ordinary choreography, so projection, the journal and
    replay need to know nothing about routines.

    Args:
        routine: The choreography to call.
        *actuals: One role per parameter, in declaration order.

    Returns:
        A fragment equal to the routine's body under the binding.

    Raises:
        ValueError: if the number of roles does not match, or two parameters
            would be bound to the same role. Aliasing is rejected because it
            would build an interaction from a role to itself, which
            ``assert_wellformed`` does not catch.
    """
    if len(actuals) != len(routine.params):
        raise ValueError(
            f'routine {routine.name!r} takes {len(routine.params)} roles, got {len(actuals)}',
        )
    if len(set(actuals)) != len(actuals):
        names = _NAMES_SEPARATOR.join(role.name for role in actuals)
        raise ValueError(
            f'routine {routine.name!r} was called with the same role twice '
            f'({names}); distinct parameters need distinct roles',
        )
    binding = dict(zip(routine.params, actuals, strict=True))
    # Rename the body while its tail is still a marker, then graft the real
    # continuation in: `Fragment._fill` is a closure, so the body cannot be
    # rewritten in place, and rewriting `body.fill(tail)` would rename the
    # caller's roles too.
    skeleton = _rename(routine.body.fill(SessionVar(_HOLE)), binding)
    return Fragment(lambda tail: _substitute(skeleton, _HOLE, tail), SessionEnd())
```

</PySourceCode>

<div >

<PyParameter name={"routine"} type={"Routine"} value={undefined}>

The choreography to call.

</PyParameter>
<PyParameter name={"actuals"} type={"Role"} value={"()"} />

</div>

<PyFunctionReturn type={"agentsparty.protocol.session.types.SessionFragment"}>

A fragment equal to the routine's body under the binding.

</PyFunctionReturn>

</PyFunction>

</Tab>

</Tabs>
