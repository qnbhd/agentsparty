# ModelRefusedError (/docs/agentsparty/kernel/errors/ModelRefusedError)

Raised when a model will not serve this request however often it is asked.

A malformed or unsupported request, a rejected key, a context window the
conversation does not fit. Asking again cannot change the outcome, so
nothing in this project retries it.
