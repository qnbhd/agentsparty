# What you can rely on (/docs/start/what-you-can-rely-on)

This page is the honest boundary of the project: what agentsparty proves, what it
checks at run time, and what it deliberately leaves to you. Read it before you
build anything on top.

## Fit

| Use agentsparty when | Look elsewhere when |
| --- | --- |
| The allowed interaction shape is known up front | One agent with a free tool set is enough |
| Every role must act only on messages it actually receives | The route must be discovered at runtime by the model |
| Projection has to fail closed before the first model call | You need a large catalogue of vendor integrations out of the box |
| Tools are roles with a protocol surface, not free function-calling | You require a stable API before 1.0 |
| Sessions must resume from recorded decisions without re-asking | You need multi-process or multi-machine transport |

The runtime is **in-process** only. Distributed multi-host orchestration is
not shipped, and roles are never invented mid-run: topology is known at bind
time.

## What is checked, and when

| Property | Result | Stage |
| --- | --- | --- |
| Declared labels only | Guaranteed | construction, projection, runtime decode |
| Knowledge of alt | Guaranteed | projection |
| Well-formed recursion | Guaranteed | `close`, projection, analysis |
| Payload shape | Guaranteed at the boundary | codec decode |
| Endpoint conformance | Guaranteed when checked | `subtype` / bind |
| Replay of authored decisions | Guaranteed for journaled decisions | resume |
| Deadlock freedom | **Not** generally guaranteed | — |
| Liveness | **Not** guaranteed | — |
| Termination | Predicate only (`may_terminate`, `must_terminate`) | — |
| Exactly-once external effects | **Not** guaranteed | — |
| Distributed delivery | **Not** shipped | — |

The negative claims are part of the contract. Projection can reject a protocol
before a model call; it cannot make a model answer, make a human respond, or
make an external API idempotent. A participant can still fail or wait.

## Status of 0.1.x

- Research framework at `0.1.x`. The public surface is tiered.
- Exception *types* are stable; exception message text and journal formats are
  not.
- Removing a public export, changing a public signature, or changing protocol
  meaning is a breaking change and lands in the
  [CHANGELOG](https://github.com/qnbhd/agentsparty/blob/master/CHANGELOG.md).
- Protocol meaning is introduced in [Protocol-first](/docs/concepts/protocol-first).

