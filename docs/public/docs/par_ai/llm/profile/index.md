# profile (/docs/agentsparty/llm/profile/index)

What a provider actually serves, and how a request is retracted onto it.

<PyAttribute name={"EVERY_EFFORT"} type={"Final"} value={"Profile.of(*(EFFORTS[1:]))"}>

A profile that serves the whole chain; the identity of retraction.

</PyAttribute>

<PyAttribute name={"NO_REASONING"} type={"Final"} value={"Profile.of()"}>

A profile for a model that does not reason: every request retracts to the
least effort, so a model asked for ``"high"`` is never sent a parameter it
would reject.

</PyAttribute>

<Tabs items={["Class"]}>

<Tab value={"Class"}>

<Cards >

<Card title={"Profile"} href={"/docs/agentsparty/llm/profile/Profile"} />
<Card title={"Profiled"} href={"/docs/agentsparty/llm/profile/Profiled"} />

</Cards>

</Tab>

</Tabs>
