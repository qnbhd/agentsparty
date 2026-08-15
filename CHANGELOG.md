# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the caveats described by the public API surface in `tests/public_api.txt`.

## [Unreleased]

### Added

- `SECURITY.md`, a README Security section, and the Start page `security`
  document injection, sandboxing, path checks, transport timeouts, budgets,
  and plaintext journals.

### Changed

- Replaced uppercase codec bindings with type-shaped names, added codec branch
  constructors and constraint methods, and re-exported the closed codec
  vocabulary from \`agentsparty\`; this is the breaking surface change described by
  [ADR 0056](architecture/decisions/0056-a-codec-constructs-its-branch.md),
  [ADR 0057](architecture/decisions/0057-a-payload-constraint-is-a-codec-method.md),
  [ADR 0058](architecture/decisions/0058-codecs-are-named-as-types.md), and
  [ADR 0059](architecture/decisions/0059-the-codec-vocabulary-lives-at-the-top-level.md).
  Generated constraint names use digits, so old refined journal identities are
  intentionally not replay-compatible in version 0.1.0.
- Restructured the documentation around reader tasks instead of module
  layout: Start (4 pages), a single Learn tutorial that grows one system
  through seven steps, Concepts (7 explanation pages), How-to (14 task pages),
  one Examples catalogue, Migration, and Reference. The module-based sections
  (Protocols, Participants, Runtime, Models, Tutorials, Contribute) and the
  five overview pages were removed; their content moved to the new sections.
  The `elements-demo` catalogue page was removed from the public site.
- The guarantee table (checked properties, non-guarantees, and the 0.1.x
  status) now lives on the Start page `what-you-can-rely-on`, next to the
  promise, instead of only in the reference.
- Machine-readable docs were reduced to the two standard `llms.txt` and
  `llms-full.txt` files; `llms-api.txt` was dropped and the examples corpus is
  now part of `llms-examples.txt` only as a verified/showcase split.
- Renamed package modules to conventional lowercase names without trailing
  underscores and made public type-home modules explicit. The old protocol
  language, foundation, and root paths were removed in this pre-1.0 migration;
  `agentsparty.protocol.analysis.participants` was removed because participant
  enumeration now belongs to session.
- Added canonical `agentsparty.protocol.language` and `agentsparty.kernel` homes for
  shared protocol leaves and foundation types. Exception, Role, serialization,
  and pickle identity now use those canonical homes directly.
- Split `agentsparty.protocol.session` into a package with leaf modules (types,
  recursion, well-formedness, syntax, termination, equivalence, projection,
  bridge, composition). Imports of `from agentsparty.protocol.session import …`
  remain valid; the runtime `__module__` of session AST types is now
  `agentsparty.protocol.session.types` (canonical type-home).
- Kept endpoint analysis (`Duty`, `duties`) in `agentsparty.protocol.analysis`,
  moved participant enumeration to `agentsparty.protocol.session`, and kept human
  rendering in `agentsparty.protocol.render`. The obsolete `agentsparty.protocol.common`
  path was removed.
- Endpoint subtyping lives in `agentsparty.protocol._conformance`; `associate` lives
  in `agentsparty.protocol._binding`. Public re-exports `subtype` / `associate` on
  `agentsparty.protocol` are unchanged.
- Journal protocol digests use a versioned canonical encoding
  (`agentsparty/protocol-digest/1`) independent of human-facing `render`. Digest
  values change for the same protocol text; JSONL/SQLite journal format
  `agentsparty/2` is unchanged.
- Non-empty containers moved from `agentsparty._utils` to the canonical kernel home
  `agentsparty.kernel.nonempty` (`NonEmptyMap`, `NonEmptyTuple`). Public signatures now
  declare non-emptiness in branch maps and tuple-shaped fields instead of
  re-checking it at runtime.
- Protocol carriers now expose `GlobalType` and `SingleSubject`, with
  `as_global` as the checked runtime boundary; overloaded message and tool
  declarations have explicit `*_for` constructors.
- Branch windows are represented by the validated `Deadline` type, and the
  closed tracing signal catalogue is available as the `SignalName` type alias.
- Project URLs, clone links, and the documentation host now use
  `https://github.com/qnbhd/agentsparty` and `https://qnbhd.github.io/agentsparty/`.

### Added

- `agentsparty.debug.Report` for human-readable protocol, conversation, duty, and
  run-fact sections written to an injected console.

## [0.1.0]

### Added

- Global choreography DSL: messages, alts, recursion, parallel composition,
  routines, and typed payload codecs with projection and rendering.
- Endpoint projection, process-oriented subtyping, association-based
  conformance, and hybrid-type composition (Equation C).
- Four participant kinds: agent (language model), human, machine, and toolbox.
- Session runtime with per-run allowances, branch deadlines, and broadcast
  cancellation.
- Decision journals with replay/resume and optional SQLite durability.
- Observability: tracers, facets, streaming observation, and optional SQLite
  sink.
- Language-model contract with retry, fallback, metering, and an optional
  OpenAI Responses API backend (`agentsparty[openai]`).
- Deterministic `ScriptedLanguageModel` for offline agent tests.
- Synchronous `AgentRuntime.run_sync` wrapper over the async session runner.
