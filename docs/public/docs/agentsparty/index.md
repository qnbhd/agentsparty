# agentsparty (/docs/agentsparty/index)

Declarative multiparty session protocols for AI agents.

The public surface lives in submodules, with the codec vocabulary and other
commonly used names re-exported here. The protocol DSL remains an explicit
submodule import, except for the codec vocabulary described by ADR 0059:

- ``agentsparty.protocol`` — the protocol DSL, codecs, projection and rendering;
- ``agentsparty.participant`` — the participant contract (``select`` / ``offer``);
- ``agentsparty.agent``, ``agentsparty.human``, ``agentsparty.machine``, ``agentsparty.toolbox``
  — the four kinds of participant;
- ``agentsparty.runtime`` — binds roles to participants and executes a protocol;
- ``agentsparty.kernel.role``, ``agentsparty.brief``, ``agentsparty.kernel.budget``,
  ``agentsparty.kernel.console``,
  ``agentsparty.kernel.errors`` — the vocabulary they share;
- ``agentsparty.llm`` — the language-model contract;
- ``agentsparty.journal`` — durable decisions;
- ``agentsparty.tracing`` — observability.
- ``agentsparty.debug`` — human-readable reports of protocols and runs.

<Tabs items={["Modules"]}>

<Tab value={"Modules"}>

<Cards >

<Card href={"/docs/agentsparty/agent"} title={"agent"} />
<Card href={"/docs/agentsparty/choreography"} title={"choreography"} />
<Card href={"/docs/agentsparty/human"} title={"human"} />
<Card href={"/docs/agentsparty/participant"} title={"participant"} />
<Card href={"/docs/agentsparty/runtime"} title={"runtime"} />
<Card href={"/docs/agentsparty/brief"} title={"brief"} />
<Card href={"/docs/agentsparty/toolbox"} title={"toolbox"} />
<Card href={"/docs/agentsparty/debug"} title={"debug"} />
<Card href={"/docs/agentsparty/machine"} title={"machine"} />
<Card href={"/docs/agentsparty/llm"} title={"llm"} />
<Card href={"/docs/agentsparty/journal"} title={"journal"} />
<Card href={"/docs/agentsparty/kernel"} title={"kernel"} />
<Card href={"/docs/agentsparty/protocol"} title={"protocol"} />
<Card href={"/docs/agentsparty/tracing"} title={"tracing"} />

</Cards>

</Tab>

</Tabs>
