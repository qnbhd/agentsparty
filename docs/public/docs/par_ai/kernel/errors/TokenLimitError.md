# TokenLimitError (/docs/agentsparty/kernel/errors/TokenLimitError)

Raised when a model has already been billed past its meter.

Sibling of `RecursionLimitError` and `StepLimitError`, with
one honest difference: those refuse a step *before* it is paid for, while
this refuses the *next* call on the strength of receipts already collected.
It cannot refuse the call that overran.
