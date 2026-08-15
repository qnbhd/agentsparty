"""Assertion helpers: ``safe_assert`` and pre/post-condition checks."""


def safe_assert(*, expr: bool, message: str | None = None) -> None:
    """Assert that ``expr`` holds, raising ``AssertionError`` otherwise.

    Unlike the builtin ``assert`` statement, this check is not stripped under
    ``-O``.

    Args:
        expr: Condition that must hold.
        message: Optional failure message.
    """
    if not expr:
        if message:
            raise AssertionError(message)
        raise AssertionError


def pre(*, expr: bool, message: str | None = None) -> None:
    """Assert a precondition.

    Args:
        expr: Condition that must hold before an operation.
        message: Optional failure message.
    """
    safe_assert(expr=expr, message=message)


def post(*, expr: bool, message: str | None = None) -> None:
    """Assert a postcondition.

    Args:
        expr: Condition that must hold after an operation.
        message: Optional failure message.
    """
    safe_assert(expr=expr, message=message)


def require_nonnegative(field: str, value: int) -> int:
    """Return *value* when it is a non-negative integer."""
    if value < 0:
        raise ValueError(f'{field} must be non-negative, got {value}')
    return value


def require_positive(field: str, value: int) -> int:
    """Return *value* when it is a strictly positive integer."""
    if value <= 0:
        raise ValueError(f'{field} must be positive, got {value}')
    return value
