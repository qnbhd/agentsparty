# View (/docs/agentsparty/machine/View)

Everything a machine is allowed to base a alt on.

Deliberately not the machine itself: ``decide`` takes a view and returns a
alt, so it is a pure function that a test calls in one line, without a
session, a runtime or an event loop.

## Attributes

<PyAttribute name={"seen"} type={"tuple[Envelope, ...]"} value={null} />

<PyAttribute name={"receiver"} type={"Role"} value={null} />

<PyAttribute name={"offered"} type={"_OfferedLabels"} value={null} />

## Functions

<PyFunction name={"__init__"} type={"(self, seen, receiver, offered) -> None"}>

<div >

<PyParameter name={"seen"} type={"tuple[Envelope, ...]"} value={null} />
<PyParameter name={"receiver"} type={"Role"} value={null} />
<PyParameter name={"offered"} type={"_OfferedLabels"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
