## agentsparty

This project is an idea that I have been developing for a long time.
It explores how modern AI agent systems can interact according to a clearly defined protocol. The theoretical foundation is **Multiparty Session Types**.

This is a research project aimed at bringing this theoretical concept closer to real-world applications and modern practices in agent-based systems.
I have studied existing projects, and I believe I may be able to contribute something new to the tooling ecosystem for AI development.

Overall, this project is a major experiment intended to answer the following questions:

> Can this be designed differently?
> Would such an approach actually be convenient to use?

## Instructions for Agents

Most of the code in this project will be implemented by a human.

When a human asks you to make a change, you must propose the smallest possible patch that solves the requested task.
You are strictly prohibited from adding anything beyond what the user explicitly requested.

For example, when the user asks you to add the ability to create something, implement only that capability. Do not introduce additional features, abstractions, utilities, or other “cool” functionality.

Unrequested additions only make the project harder for the author to understand and interfere with the author’s ability to reason deeply and independently about its design.

### CUPID Properties

When writing or reviewing code, use the CUPID properties (https://cupid.dev/) as a lens rather than a checklist of rules. These are not principles to comply with — they are qualities code can move closer to or further from. Prefer changes that move code toward these properties, but always weigh them against the "smallest possible patch" instruction above: do not use CUPID as a justification for scope creep.

- **Composable** — plays well with others. Favor a small, opinionated surface area; intention-revealing names that make it obvious what a piece of code does and whether it's the right fit; and minimal dependencies, so the code is easy to pick up and combine with other code.
- **Unix philosophy** — does one thing well. A function, module, or agent should have a single, clear purpose, be usable on its own, and compose cleanly with other things that also do one thing well.
- **Predictable** — does what you expect. Behavior should be deterministic where possible, free of surprising side effects, and observable/testable, so that reading the code (or its types/contracts) is enough to know what it will do.
- **Idiomatic** — feels natural. Code should follow the conventions of the language, ecosystem, and codebase it lives in, so it feels familiar even to someone seeing it for the first time.
- **Domain-based** — the code models the problem domain in language and structure. Names, types, and structure should reflect the vocabulary and shape of the problem (here: agents, sessions, protocols, roles), minimizing the distance between the domain and the code.

### Design Guidelines

Unlike CUPID, the rules below are firm defaults. They still sit under the
"smallest possible patch" instruction: apply them to the code you are
writing, not as a mandate to rewrite code around it. The goal is to write
compact, correct code the first time — a planned "refactor it later" is not
a substitute.

#### Contracts

Before writing a function, work out what must hold *before* it runs
(precondition), what it guarantees *after* (postcondition), and what
property it must preserve (invariant). State each in one sentence, then
encode it with `pre`, `post`, and `safe_assert` from
`agentsparty._utils.assertions`. Aim for at least one or two assertions per
function.

These assertions describe programmer errors — a broken contract is a bug in
the caller, not an expected outcome. Expected failures caused by external
input are handled at the boundary (see below), not by an assertion.

#### Parse, don't validate

Move every check of an unknown value to the one place where the value first
becomes known: a type's constructor or a deserialization boundary.
Everything downstream then receives a value that is correct by construction
and needs no re-checking.

- Replace raw primitives (`str`, `int`, bare tuples) with small domain types
  that cannot hold an incorrect value.
- Make illegal states unrepresentable: prefer one enum over several
  independent booleans/optionals whose combinations admit a fourth, illegal
  state. A comment saying `start must be <= end` is not a mechanism.
- Model absence explicitly — an object satisfying the interface, or a type
  that forces the caller to handle the empty case — rather than letting
  `None` travel through the code.
- Forbid wrong call sequences at the type level (`start` returns a token
  that `stop` requires) instead of relying on tests to catch them.
- Best of all, change the mental model so the check never has to arise
  ("next page" instead of "the last one, or 1").

#### Shape of a function

- 40 lines maximum; nesting at most one level deep.
- Prefer guard clauses and early returns over `else` and `elif` chains.
  Branching on a type code belongs in polymorphism or a dispatch table
  (dict of handlers) — new behavior should be a new entry, not an edit to
  an existing chain.
- A loop nested inside a condition is a stop signal: reach for a `dict`/`set`
  or reshape the data.
- A boolean flag that switches behavior means there are two functions.
- Return named results (`NamedTuple`, dataclass, or a dict with meaningful
  keys) when more than one value leaves a function.
- Keep logically linked lines together in one function: a predicate and its
  negation, matching constants, a shared threshold. Write a predicate once
  and obtain its complement by negation or partitioning. Fix a volatile
  quantity (current time, a threshold) once and pass it as a parameter, so
  the result is consistent and testable.

#### No raw loops

Recognize the family a loop belongs to — fold, unfold, map, filter, find,
partition — and name the intent instead of spelling it out. Use `all`/`any`/
`sum`, `functools.reduce`, comprehensions, and `itertools`; iterate over
elements rather than indices unless the index is meaningful; merge passes
that can be done in one. An unfold (generating a sequence from an initial
state) belongs in a named generator. Recurring acquire/release pairs belong
in a context manager, never in a hand-written `try/finally`.

Prefer a pipeline to nested calls: stages in the order the value actually
flows, one meaningful transformation per line, named after domain concepts
(`eligible_orders`, not `step2`). Keep lazy stages distinct from the
terminal operation so cost and side effects stay visible, and do not
materialize intermediate lists without a reason. A pipeline that grows
conditionals and I/O in the middle should be split instead.

#### No runtime reflection or magic

Avoid `isinstance`, `hasattr`, `getattr`/`setattr` on dynamic names, `exec`,
`eval`, dynamic imports, and metaclass tricks. If the code seems to require
them, the design is most likely wrong: the missing piece is usually a type,
a protocol, or an explicit registry.

#### Purity and shared state

Reading global state and mutating an argument are acceptable; mutating
global state from an otherwise pure function is not. Keep module-level
state genuinely immutable (a `Final` reference to a mutable collection
protects nothing). Copy defensively when a mutable object crosses a
boundary in either direction. Make data-flow dependencies explicit by
passing the object rather than hiding it in a global.

#### Comments

Comments should carry what the code cannot: contracts, prohibitions, the
reason behind a decision, global context, TODOs, and anti-information —
what a function deliberately does *not* do and where that happens instead.
Do not transcribe the code, and do not encode documentation into six-word
function names. Keep comments next to the code they describe, and update
them during refactoring exactly like names and tests; a stale comment is
worse than none.

Inside a function, label each logical step with a comment naming its
meaning (`# resolve target role:`) even while the code stays in one place.
The labels let the function be read as a list of steps and mark the seams
for a later extraction. Keep temporaries scoped to the step that needs them.

### Testing Guidelines

When writing tests, minimize redundancy: avoid multiple tests that exercise
the same behavior in slightly different guises.

Before writing a test, check whether the function under test has an
algebraic property (inverse, invariant, idempotence, commutativity/
associativity, a commuting diagram, or an equivalence to a simpler
reference model). If so, prefer a single property-based test expressing
that property over several example-based tests.

Use example-based tests only for cases a property test cannot express:
boundary conditions, specific regression cases, or scenarios without a
clean algebraic characterization.

Avoid monkey patching of every kind: pytest's `monkeypatch` fixture,
`unittest.mock.patch`, and reassigning attributes on modules, classes, or
instances. A test that needs to patch something is reporting a design
problem — the dependency is hidden instead of being passed in. Make it a
parameter (a function, a protocol implementation, a clock) and supply the
test double directly.

Two related signals worth reading as design feedback rather than test
problems:

- Many similar mock-heavy tests around one class mean the class depends on
  too much, or its behavior is driven by conditional branches.
- Passing `None`/zero values for parameters the body never touches in that
  scenario means the function does more than one thing and should be split.

For a type with an invariant, test more than the constructor: every public
operation must be closed over valid values — any successful operation on a
correct value has to yield a correct value.

## Running the Project

Use `uv` for all project-related tasks.

Format:

```bash
uv run ruff format src tests
```

Check:

```bash
uv run ty check src tests
```

Tests:

Tests better run with xdist, use the following command:

```bash
uv run pytest -n auto
```