"""Progress tracker for monitoring role execution progress.

Tracks progress of individual roles and overall pipeline progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from lyra_research.coordination.role_state_machine import RoleState


@dataclass
class RoleProgress:
    """Progress information for a single role.

    Attributes:
        role_name: Name of the role
        state: Current state
        progress: Progress percentage (0.0 to 1.0)
        started_at: When role started
        completed_at: When role completed
        error: Error message if failed
        metadata: Additional metadata
    """

    role_name: str
    state: RoleState = RoleState.PENDING
    progress: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, any] = field(default_factory=dict)

    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds.

        Returns:
            Duration in seconds, or 0.0 if not started/completed
        """
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at or datetime.now(timezone.utc)
        return (end_time - self.started_at).total_seconds()

    def is_complete(self) -> bool:
        """Check if role is complete.

        Returns:
            True if role is completed or failed
        """
        return self.state in (RoleState.COMPLETED, RoleState.FAILED)


class ProgressTracker:
    """Tracker for monitoring role execution progress.

    Tracks progress of individual roles and calculates overall pipeline progress.
    """

    def __init__(self, role_names: list[str]) -> None:
        """Initialize progress tracker.

        Args:
            role_names: List of role names in pipeline order
        """
        self._role_names = role_names
        self._progress: dict[str, RoleProgress] = {
            name: RoleProgress(role_name=name) for name in role_names
        }
        self._pipeline_started_at: datetime | None = None
        self._pipeline_completed_at: datetime | None = None

    def start_pipeline(self) -> None:
        """Mark pipeline as started."""
        self._pipeline_started_at = datetime.now(timezone.utc)

    def complete_pipeline(self) -> None:
        """Mark pipeline as completed."""
        self._pipeline_completed_at = datetime.now(timezone.utc)

    def start_role(self, role_name: str) -> None:
        """Mark role as started.

        Args:
            role_name: Name of the role
        """
        if role_name not in self._progress:
            raise ValueError(f"Unknown role: {role_name}")

        progress = self._progress[role_name]
        progress.state = RoleState.RUNNING
        progress.started_at = datetime.now(timezone.utc)
        progress.progress = 0.0

    def complete_role(self, role_name: str, error: str | None = None) -> None:
        """Mark role as completed.

        Args:
            role_name: Name of the role
            error: Error message if failed
        """
        if role_name not in self._progress:
            raise ValueError(f"Unknown role: {role_name}")

        progress = self._progress[role_name]
        progress.completed_at = datetime.now(timezone.utc)
        progress.progress = 1.0

        if error:
            progress.state = RoleState.FAILED
            progress.error = error
        else:
            progress.state = RoleState.COMPLETED

    def update_role_progress(self, role_name: str, progress: float) -> None:
        """Update progress of a role.

        Args:
            role_name: Name of the role
            progress: Progress percentage (0.0 to 1.0)
        """
        if role_name not in self._progress:
            raise ValueError(f"Unknown role: {role_name}")

        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {progress}")

        self._progress[role_name].progress = progress

    def update_role_state(self, role_name: str, state: RoleState) -> None:
        """Update state of a role.

        Args:
            role_name: Name of the role
            state: New state
        """
        if role_name not in self._progress:
            raise ValueError(f"Unknown role: {role_name}")

        self._progress[role_name].state = state

    def add_role_metadata(self, role_name: str, key: str, value: any) -> None:
        """Add metadata to a role.

        Args:
            role_name: Name of the role
            key: Metadata key
            value: Metadata value
        """
        if role_name not in self._progress:
            raise ValueError(f"Unknown role: {role_name}")

        self._progress[role_name].metadata[key] = value

    def get_role_progress(self, role_name: str) -> float:
        """Get progress of a role.

        Args:
            role_name: Name of the role

        Returns:
            Progress percentage (0.0 to 1.0)
        """
        if role_name not in self._progress:
            raise ValueError(f"Unknown role: {role_name}")

        return self._progress[role_name].progress

    def get_role_status(self, role_name: str) -> dict[str, any]:
        """Get detailed status of a role.

        Args:
            role_name: Name of the role

        Returns:
            Dict with role status information
        """
        if role_name not in self._progress:
            raise ValueError(f"Unknown role: {role_name}")

        progress = self._progress[role_name]
        return {
            "role_name": progress.role_name,
            "state": progress.state.value,
            "progress": progress.progress,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "duration_seconds": progress.duration_seconds(),
            "error": progress.error,
            "metadata": progress.metadata,
        }

    def get_pipeline_progress(self) -> float:
        """Get overall pipeline progress.

        Returns:
            Progress percentage (0.0 to 1.0)
        """
        if not self._progress:
            return 0.0

        total_progress = sum(p.progress for p in self._progress.values())
        return total_progress / len(self._progress)

    def get_pipeline_status(self) -> dict[str, any]:
        """Get overall pipeline status.

        Returns:
            Dict with pipeline status information
        """
        completed_roles = sum(1 for p in self._progress.values() if p.is_complete())
        failed_roles = sum(1 for p in self._progress.values() if p.state == RoleState.FAILED)

        duration = 0.0
        if self._pipeline_started_at:
            end_time = self._pipeline_completed_at or datetime.now(timezone.utc)
            duration = (end_time - self._pipeline_started_at).total_seconds()

        return {
            "total_roles": len(self._progress),
            "completed_roles": completed_roles,
            "failed_roles": failed_roles,
            "overall_progress": self.get_pipeline_progress(),
            "started_at": (
                self._pipeline_started_at.isoformat() if self._pipeline_started_at else None
            ),
            "completed_at": (
                self._pipeline_completed_at.isoformat() if self._pipeline_completed_at else None
            ),
            "duration_seconds": duration,
            "roles": {name: self.get_role_status(name) for name in self._role_names},
        }

    def reset(self) -> None:
        """Reset all progress tracking."""
        self._progress = {name: RoleProgress(role_name=name) for name in self._role_names}
        self._pipeline_started_at = None
        self._pipeline_completed_at = None
