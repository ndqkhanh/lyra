"""Base class for specialized roles in Lyra Research.

Each role has:
- Clear responsibility (discovery, analysis, synthesis, review, curation)
- Model assignment (Haiku/Sonnet/Opus/GPT)
- Context manager for layered context
- Input/output validation
- Execution logic
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

from lyra_core.context.layered_context import LayeredContextManager


class RoleStatus(str, Enum):
    """Status of role execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    VALIDATION_ERROR = "validation_error"


@dataclass
class RoleResult:
    """Base result from role execution."""

    role_name: str
    status: RoleStatus
    data: Any
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_complete(self) -> None:
        """Mark result as complete."""
        self.completed_at = datetime.now(timezone.utc)

    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds."""
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()


T = TypeVar("T", bound=RoleResult)


class Role(ABC, Generic[T]):
    """
    Base class for specialized roles.

    Each role:
    1. Validates input before execution
    2. Executes role-specific logic
    3. Validates output before handoff
    4. Returns typed RoleResult
    """

    def __init__(
        self,
        name: str,
        model: str,
        context_manager: LayeredContextManager,
    ) -> None:
        """
        Initialize role.

        Args:
            name: Role name (e.g., "Discovery", "Analysis")
            model: Model to use (e.g., "claude-haiku-4-5", "gpt-4o-mini")
            context_manager: Layered context manager for context optimization
        """
        self.name = name
        self.model = model
        self.context_manager = context_manager

    @abstractmethod
    async def execute(self, input_data: Any) -> T:
        """
        Execute role-specific logic.

        Args:
            input_data: Input data for the role

        Returns:
            Typed RoleResult with execution results
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input before execution.

        Args:
            input_data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def validate_output(self, output: Any) -> bool:
        """
        Validate output before handoff to next role.

        Args:
            output: Output data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    async def run(self, input_data: Any) -> T:
        """
        Run role with validation.

        Args:
            input_data: Input data for the role

        Returns:
            RoleResult with execution results

        Raises:
            ValueError: If input validation fails
        """
        # Validate input
        if not self.validate_input(input_data):
            result = RoleResult(
                role_name=self.name,
                status=RoleStatus.VALIDATION_ERROR,
                data=None,
                error=f"Input validation failed for {self.name}",
            )
            result.mark_complete()
            return result  # type: ignore

        # Execute
        try:
            result = await self.execute(input_data)
            result.status = RoleStatus.SUCCESS

            # Validate output
            if not self.validate_output(result.data):
                result.status = RoleStatus.VALIDATION_ERROR
                result.error = f"Output validation failed for {self.name}"

            result.mark_complete()
            return result

        except Exception as e:
            result = RoleResult(
                role_name=self.name,
                status=RoleStatus.FAILED,
                data=None,
                error=str(e),
            )
            result.mark_complete()
            return result  # type: ignore
