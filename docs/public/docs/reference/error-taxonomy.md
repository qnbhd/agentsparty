# Error taxonomy (/docs/reference/error-taxonomy)

## Every exported error

```python exec
from agentsparty.kernel import errors

names = sorted(
    n for n in dir(errors) if n.endswith('Error') or n.endswith('Refused')
)
print('\n'.join(names))
```

## Families

| Family | Examples | When |
| --- | --- | --- |
| Projection / conformance | ProjectionError, ConformanceError, CompositionError | Before or at bind of illegal types |
| Payload | PayloadError, SelectionError | Codec / label mismatch |
| Model | ModelError, ModelRefusedError, ModelUnavailableError | Provider boundary |
| Limits | StepLimitError, RecursionLimitError, TokenLimitError, AllowanceExceededError, DeadlineExceededError | Budgets and time |
| Journal | JournalError | Decision log integrity |

## Assertions versus errors

Programmer contract breaks raise assertions in debug paths; expected external
failures use the typed errors above.

The most common one to meet is `ProjectionError`; see
[knowledge of alt](/docs/concepts/knowledge-of-alt) for the concept.
Runtime bounds are covered in
[composition and termination](/docs/concepts/composition-and-termination) and
[[agentsparty.kernel.errors.ProjectionError]].

