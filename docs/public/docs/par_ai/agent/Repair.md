# Repair (/docs/agentsparty/agent/Repair)

How many corrections a model is offered when its answer will not decode.

A person at a console is already re-prompted on a bad payload
(``CliHumanIo.choose`` loops until the input parses); this gives a model
the same courtesy, and nothing more. Repair is invisible to the protocol
and to the journal: nothing is recorded until an answer decodes, so a
resumed session never repeats a correction, and a protocol reader cannot
tell a repaired step from a clean one.

A failure the protocol *declares* is a reply branch, not a repair.

## Attributes

<PyAttribute name={"attempts"} type={"int"} value={"1"} />

## Functions

<PyFunction name={"__init__"} type={"(self, attempts=1) -> None"}>

<div >

<PyParameter name={"attempts"} type={"int"} value={"1"} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
