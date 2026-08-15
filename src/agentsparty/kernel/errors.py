"""The protocol exception hierarchy."""


class ProjectionError(Exception):
    """Raised when a endpoint protocol cannot be derived from a global protocol."""


class ConformanceError(ValueError):
    """Raised when a participant's declared endpoint type does not fit its role.

    Sibling of :class:`ProjectionError` with one difference: a projection error
    says the *choreography* is malformed, this one says the *participant* was
    wired to a role it cannot play. It is raised from a constructor, about an
    argument, which is why it is a ``ValueError``.
    """


class CompositionError(ValueError):
    """Raised when components do not fit their compatibility contract.

    Sibling of :class:`ConformanceError` one level up: conformance says one
    participant cannot play one role, composition says one component cannot
    join the system — it does not match the contract, or its shape cannot be
    built back into the whole.
    """


class PayloadError(ValueError):
    """Raised when a value cannot be parsed as the branch's declared payload type."""


class SelectionError(ValueError):
    """Raised when human input does not name one of the offered branches."""


class AllowanceExceededError(RuntimeError):
    """Raised when a run would spend past its allowance."""


class RecursionLimitError(AllowanceExceededError):
    """Raised when a run exhausts its unfolding allowance."""


class StepLimitError(AllowanceExceededError):
    """Raised when a run exhausts its step allowance."""


class DeadlineExceededError(RuntimeError):
    """Raised when a sender does not choose within a branch's wall-clock window.

    The runtime turns the timeout into this failure and then broadcasts
    :meth:`~agentsparty.participant.Participant.cancel` to every bound participant —
    the same roll-up path used for allowance and payload failures.
    """


class TokenLimitError(AllowanceExceededError):
    """Raised when a model has already been billed past its meter.

    Sibling of :class:`RecursionLimitError` and :class:`StepLimitError`, with
    one honest difference: those refuse a step *before* it is paid for, while
    this refuses the *next* call on the strength of receipts already collected.
    It cannot refuse the call that overran.
    """


class ModelError(RuntimeError):
    """Raised when a language model would not answer a request."""


class ModelUnavailableError(ModelError):
    """Raised when a model would not answer but another attempt may succeed.

    Rate limits, timeouts, dropped connections and server faults. The provider
    sometimes says how long to wait; :attr:`retry_after` carries that answer,
    and ``0`` means it said nothing.
    """

    def __init__(self, message: str, retry_after: float = 0) -> None:
        """Record *message* and how long the provider asked for.

        Args:
            message: What went wrong.
            retry_after: Seconds the provider asked the caller to wait.
        """
        super().__init__(message)
        self.retry_after = retry_after


class ModelRefusedError(ModelError):
    """Raised when a model will not serve this request however often it is asked.

    A malformed or unsupported request, a rejected key, a context window the
    conversation does not fit. Asking again cannot change the outcome, so
    nothing in this project retries it.
    """


# Compatibility aliases preserve the original public names while the concrete
# exception classes follow the conventional ``Error`` suffix.
AllowanceExceeded = AllowanceExceededError
DeadlineExceeded = DeadlineExceededError
ModelUnavailable = ModelUnavailableError
ModelRefused = ModelRefusedError


class JournalError(ValueError):
    """Raised when a journal does not fit the protocol it is replayed against."""


def fault(error: Exception) -> str:
    """How an exception is written down when it is observed, not raised.

    One spelling, because a trace is read by people: the exception's type name,
    then what it said. The session scope writes failures with it
    (:class:`~agentsparty.tracing.signals.Failed`) and so does a cancellation
    notice, so one failure reads the same way wherever it is recorded.

    Args:
        error: The exception to write down.

    Returns:
        The exception's type name and its message, separated by a colon.

    Example:
        >>> from agentsparty.kernel.errors import PayloadError, fault
        >>> fault(PayloadError('not json'))
        'PayloadError: not json'
    """
    return f'{type(error).__name__}: {error}'


__all__ = [
    'AllowanceExceeded',
    'CompositionError',
    'ConformanceError',
    'DeadlineExceeded',
    'JournalError',
    'ModelError',
    'ModelRefused',
    'ModelUnavailable',
    'PayloadError',
    'ProjectionError',
    'RecursionLimitError',
    'SelectionError',
    'StepLimitError',
    'TokenLimitError',
    'fault',
]
