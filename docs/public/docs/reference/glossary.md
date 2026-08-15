# Glossary (/docs/reference/glossary)

## Protocol and projection

| Term | Definition |
| --- | --- |
| global choreography | The whole-session protocol among roles |
| endpoint protocol / view | One role's projected local type |
| projection | Deriving endpoints; refusing blind alt |

## Roles and participants

| Term | Definition |
| --- | --- |
| role | Address in the protocol |
| participant | Behaviour implementing an endpoint |
| `Cast` | Partial section of projection + factories |

## Messages and branches

| Term | Definition |
| --- | --- |
| branch / case | Declared alternative with a label |
| payload codec | Decoder at the message boundary |

## What a run records

| Term | Definition |
| --- | --- |
| journal decision | Recorded authorship alt for replay |
| replay / resume | Re-run using journal decisions |
| trace event | Observation record; not a decision |
| allowance | Runtime bound on spend (steps/unfolds/tokens) |

See also [protocol-first](/docs/concepts/protocol-first),
[projection](/docs/concepts/projection), and
[journal and trace](/docs/concepts/journal-and-trace).

