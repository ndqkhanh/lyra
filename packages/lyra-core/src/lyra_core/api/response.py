"""API response format.

Consistent response envelope for all API operations.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class APIResponse:
    """Unified API response format.

    Attributes:
        success: Whether operation succeeded
        data: Response data (None on error)
        error: Error details (None on success)
    """

    success: bool
    data: Any | None = None
    error: dict[str, Any] | None = None

    @classmethod
    def success(cls, data: Any = None) -> "APIResponse":
        """Create successful response.

        Args:
            data: Response data

        Returns:
            APIResponse with success=True
        """
        return cls(success=True, data=data, error=None)

    @classmethod
    def error(
        cls,
        message: str,
        code: str = "API_ERROR",
        details: dict[str, Any] | None = None,
    ) -> "APIResponse":
        """Create error response.

        Args:
            message: Error message
            code: Error code
            details: Additional error details

        Returns:
            APIResponse with success=False
        """
        return cls(
            success=False,
            data=None,
            error={
                "message": message,
                "code": code,
                "details": details or {},
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }
