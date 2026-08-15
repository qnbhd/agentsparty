# DeadlineExceededError (/docs/agentsparty/kernel/errors/DeadlineExceededError)

Raised when a sender does not choose within a branch's wall-clock window.

The runtime turns the timeout into this failure and then broadcasts
[`cancel`](/docs/agentsparty/participant/Participant) to every bound participant —
the same roll-up path used for allowance and payload failures.
