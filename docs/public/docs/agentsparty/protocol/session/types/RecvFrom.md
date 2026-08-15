# RecvFrom (/docs/agentsparty/protocol/session/types/RecvFrom)

External input ``p?q``.

Internal `receiver` reacts to a label external `sender` picks.

## Attributes

<PyAttribute name={"sender"} type={"Role"} value={null} />

<PyAttribute name={"receiver"} type={"Role"} value={null} />

<PyAttribute name={"branches"} type={"NonEmptyMap[Label, SessionBranchCase]"} value={null} />

## Functions

<PyFunction name={"__init__"} type={"(self, sender, receiver, branches) -> None"}>

<div >

<PyParameter name={"sender"} type={"Role"} value={null} />
<PyParameter name={"receiver"} type={"Role"} value={null} />
<PyParameter name={"branches"} type={"NonEmptyMap[Label, SessionBranchCase]"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
