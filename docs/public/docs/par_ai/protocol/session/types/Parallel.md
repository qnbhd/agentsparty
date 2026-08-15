# Parallel (/docs/agentsparty/protocol/session/types/Parallel)

Independent composition ``H₁ | … | Hₙ``.

Branches own pairwise-disjoint role sets and never exchange a message, so
they have no common future: parallel composition has **no join**, and a
parallel node has no continuation. Branches are closed, flattened, and
ordered canonically, so ``par(a, b)`` and ``par(b, a)`` are one value.

## Attributes

<PyAttribute name={"branches"} type={"_ParallelBranches"} value={null} />

## Functions

<PyFunction name={"__init__"} type={"(self, branches) -> None"}>

<div >

<PyParameter name={"branches"} type={"_ParallelBranches"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
