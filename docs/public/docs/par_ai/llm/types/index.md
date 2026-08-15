# types (/docs/agentsparty/llm/types/index)

Language-model contract types shared with the protocol layer.

<PyAttribute name={"Effort"} type={"TypeAlias"} value={"Literal['none', 'minimal', 'low', 'medium', 'high']"} />

<PyAttribute name={"ChatRole"} type={"TypeAlias"} value={"Literal['user', 'assistant', 'system']"} />

<PyAttribute name={"EFFORTS"} type={"Final[tuple[Effort, ...]]"} value={"('none', 'minimal', 'low', 'medium', 'high')"}>

Every reasoning effort, from least to greatest.

Kept next to `Effort` on purpose: the alias and its enumeration are two
halves of one fact, and a plan that separates them lets them drift.

</PyAttribute>

<PyAttribute name={"LEAST_EFFORT"} type={"Final[Effort]"} value={"EFFORTS[0]"}>

The effort every model is assumed to serve; see [`Profile`](/docs/agentsparty/llm/profile/Profile).

</PyAttribute>

<PyAttribute name={"NO_USAGE"} type={"Final"} value={"Usage()"}>

The empty bill: what a provider that reports no usage is recorded as.

</PyAttribute>

<Tabs items={["Class"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"ModelId"} href={"/docs/agentsparty/llm/types/ModelId"} />
<Card title={"Usage"} href={"/docs/agentsparty/llm/types/Usage"} />
<Card title={"Answer"} href={"/docs/agentsparty/llm/types/Answer"} />
<Card title={"Message"} href={"/docs/agentsparty/llm/types/Message"} />
<Card title={"StructuredRequest"} href={"/docs/agentsparty/llm/types/StructuredRequest"} />
<Card title={"LanguageModel"} href={"/docs/agentsparty/llm/types/LanguageModel"} />

</Cards>

</Tab>

</Tabs>
