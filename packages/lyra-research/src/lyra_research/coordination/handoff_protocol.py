"""Handoff protocol for data transfer between roles.

Manages data validation and transfer between roles in the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from lyra_research.roles.role_base import Role


@dataclass
class HandoffData:
    """Data passed between roles.

    Attributes:
        role_from: Source role name
        role_to: Target role name
        data: Data being transferred
        metadata: Additional metadata
        timestamp: When handoff was created
        validated: Whether data has been validated
        validation_errors: List of validation errors
    """

    role_from: str
    role_to: str
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validated: bool = False
    validation_errors: list[str] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate handoff data completeness.

        Returns:
            True if data is valid
        """
        self.validation_errors.clear()

        # Check required fields
        if not self.role_from:
            self.validation_errors.append("role_from is required")
        if not self.role_to:
            self.validation_errors.append("role_to is required")
        if self.data is None:
            self.validation_errors.append("data is required")

        # Check data is not empty
        if isinstance(self.data, (list, dict, str)) and len(self.data) == 0:
            self.validation_errors.append("data cannot be empty")

        self.validated = len(self.validation_errors) == 0
        return self.validated

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to handoff.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)


class HandoffProtocol:
    """Protocol for managing handoffs between roles.

    Handles data preparation, validation, execution, and rollback.
    """

    def __init__(self) -> None:
        """Initialize handoff protocol."""
        self._handoff_history: list[HandoffData] = []
        self._failed_handoffs: list[HandoffData] = []

    def prepare_handoff(
        self, from_role: Role, to_role: Role, data: Any, metadata: dict[str, Any] | None = None
    ) -> HandoffData:
        """Prepare data for handoff.

        Args:
            from_role: Source role
            to_role: Target role
            data: Data to transfer
            metadata: Optional metadata

        Returns:
            HandoffData ready for validation
        """
        handoff = HandoffData(
            role_from=from_role.name,
            role_to=to_role.name,
            data=data,
            metadata=metadata or {},
        )

        # Add role metadata
        handoff.add_metadata("from_model", from_role.model)
        handoff.add_metadata("to_model", to_role.model)

        return handoff

    def validate_handoff(self, handoff: HandoffData, from_role: Role, to_role: Role) -> tuple[bool, list[str]]:
        """Validate handoff data.

        Args:
            handoff: Handoff to validate
            from_role: Source role
            to_role: Target role

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        # Basic validation
        if not handoff.validate():
            errors.extend(handoff.validation_errors)

        # Validate output from source role
        if not from_role.validate_output(handoff.data):
            errors.append(f"Output validation failed for {from_role.name}")

        # Validate input for target role
        if not to_role.validate_input(handoff.data):
            errors.append(f"Input validation failed for {to_role.name}")

        return len(errors) == 0, errors

    def execute_handoff(
        self, handoff: HandoffData, from_role: Role, to_role: Role
    ) -> tuple[bool, str | None]:
        """Execute handoff with validation.

        Args:
            handoff: Handoff to execute
            from_role: Source role
            to_role: Target role

        Returns:
            Tuple of (success, error_message)
        """
        # Validate handoff
        is_valid, errors = self.validate_handoff(handoff, from_role, to_role)

        if not is_valid:
            error_msg = f"Handoff validation failed: {'; '.join(errors)}"
            self._failed_handoffs.append(handoff)
            return False, error_msg

        # Record successful handoff
        self._handoff_history.append(handoff)
        return True, None

    def rollback_handoff(self, handoff: HandoffData) -> None:
        """Rollback failed handoff.

        Args:
            handoff: Handoff to rollback
        """
        # Remove from history if present
        if handoff in self._handoff_history:
            self._handoff_history.remove(handoff)

        # Add to failed handoffs
        if handoff not in self._failed_handoffs:
            self._failed_handoffs.append(handoff)

    def get_handoff_history(self) -> list[HandoffData]:
        """Get history of successful handoffs.

        Returns:
            List of successful handoffs
        """
        return self._handoff_history.copy()

    def get_failed_handoffs(self) -> list[HandoffData]:
        """Get history of failed handoffs.

        Returns:
            List of failed handoffs
        """
        return self._failed_handoffs.copy()

    def get_handoff_chain(self) -> list[str]:
        """Get chain of role handoffs.

        Returns:
            List of role names in handoff order
        """
        if not self._handoff_history:
            return []

        chain = [self._handoff_history[0].role_from]
        for handoff in self._handoff_history:
            chain.append(handoff.role_to)

        return chain

    def clear_history(self) -> None:
        """Clear handoff history."""
        self._handoff_history.clear()
        self._failed_handoffs.clear()

    def get_handoff_stats(self) -> dict[str, Any]:
        """Get handoff statistics.

        Returns:
            Dict with handoff statistics
        """
        return {
            "total_handoffs": len(self._handoff_history),
            "failed_handoffs": len(self._failed_handoffs),
            "success_rate": (
                len(self._handoff_history) / (len(self._handoff_history) + len(self._failed_handoffs))
                if (len(self._handoff_history) + len(self._failed_handoffs)) > 0
                else 0.0
            ),
            "handoff_chain": self.get_handoff_chain(),
        }
