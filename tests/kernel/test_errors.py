"""Domain error types."""

from agentsparty.kernel.errors import PayloadError, ProjectionError, SelectionError


def test_error_hierarchy() -> None:
    assert issubclass(PayloadError, ValueError)
    assert issubclass(SelectionError, ValueError)
    assert issubclass(ProjectionError, Exception)
