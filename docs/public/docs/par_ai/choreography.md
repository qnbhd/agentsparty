# choreography (/docs/agentsparty/choreography/index)

Choreography facade: build the same ``SessionType`` AST with Python control flow.

This module has **no** own projection, composition, or AST node types. Every
operator calls the existing combinators in [`protocol`](/docs/agentsparty/protocol). Pair a
choreography with a combinator twin via
[`equal_session`](/docs/agentsparty/protocol/session).

**Not in v1** (stay on facade A): external component interfaces
(``owning`` / ``Boundary``), ``compose`` / ``localise``, and consumption
operators on `Located` values.

<Tabs items={["Modules"]}>

<Tab value={"Modules"}>

<Cards >

<Card href={"/docs/agentsparty/choreography/chor"} title={"chor"} />

</Cards>

</Tab>

</Tabs>
