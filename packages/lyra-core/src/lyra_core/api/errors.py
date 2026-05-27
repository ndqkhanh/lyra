"""API error types.

Consistent error handling across all API operations.
"""
from typing import Any


class APIError(Exception):
    """Base exception for all API errors.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize API error.

        Args:
            message: Error message
            code: Optional error code
            details: Optional additional details
        """
        super().__init__(message)
        self.message = message
        self.code = code or "API_ERROR"
        self.details = details or {}

    def __str__(self) -> str:
        """Return error message."""
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary format.

        Returns:
            Dictionary with error details
        """
        return {
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }
