# Facet (/docs/agentsparty/tracing/facet/Facet)

A side of a session one can watch: a subset of `SIGNAL_NAMES`.

Facets combine like sets: ``|`` is union, ``&`` is intersection, ``~`` is
complement and ``\<=`` is inclusion. That is the whole of what the industry
spells as six methods: ``stream.llm``, ``stream.tools``, … and
``interleave([...])``, which is just ``|``.

A facet carries no data about a signal beyond membership, which is why
projecting a trace onto one loses nothing but the events it excludes.

## Attributes

<PyAttribute name={"names"} type={"frozenset[str]"} value={null} />

## Functions

<PyFunction name={"__init__"} type={"(self, names) -> None"}>

<div >

<PyParameter name={"names"} type={"frozenset[str]"} value={null} />

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
