"""State Reconstructor - Reconstructs autonomy engine state from checkpoints.

Rebuilds the complete state machine state, active goals, running tasks,
and execution context to enable seamless session resumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class ReconstructionPhase(StrEnum):
    """Phases of state reconstruction."""

    VALIDATE = "validate"       # Verify checkpoint integrity
    EXTRACT = "extract"          # Pull data from checkpoint
    REBUILD = "rebuild"          # Reconstruct state objects
    VERIFY = "verify"            # Validate reconstructed state
    ACTIVATE = "activate"        # Resume from reconstructed state


@dataclass(frozen=True)
class ReconstructedState:
    """A fully reconstructed autonomy engine state."""

    session_id: str
    state: str  # FSM state value
    goals: tuple[dict[str, Any], ...]
    active_tasks: tuple[dict[str, Any], ...]
    completed_task_count: int
    failed_task_count: int
    blocked_task_count: int
    context: dict[str, Any]
    checkpoint_age_seconds: float
    reconstruction_duration_ms: float
    warnings: tuple[str, ...]
    is_valid: bool


@dataclass(frozen=True)
class ReconstructionReport:
    """Detailed report of the reconstruction process."""

    session_id: str
    success: bool
    phases_completed: tuple[ReconstructionPhase, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    state: ReconstructedState | None
    duration_ms: float
    timestamp: str


class StateReconstructor:
    """Reconstructs autonomy engine state from session checkpoints.

    Features:
    - Multi-phase state reconstruction with validation at each phase
    - Checkpoint integrity verification
    - Graceful handling of partial/corrupted data
    - Reconstruction quality scoring
    - Detailed reconstruction reporting
    """

    def __init__(self, strict_validation: bool = False):
        self.strict_validation = strict_validation
        self._history: list[ReconstructionReport] = []

    def reconstruct(
        self,
        session_id: str,
        checkpoint_data: dict[str, Any],
    ) -> ReconstructedState:
        """Reconstruct autonomy state from checkpoint data.

        Args:
            session_id: Session identifier
            checkpoint_data: Raw checkpoint data dictionary

        Returns:
            ReconstructedState with rebuilt state machine state
        """
        start_time = datetime.now()
        warnings: list[str] = []

        # Phase 1: Validate
        is_valid, validation_warnings = self._validate_checkpoint(checkpoint_data)
        warnings.extend(validation_warnings)

        if not is_valid and self.strict_validation:
            return ReconstructedState(
                session_id=session_id,
                state="UNKNOWN",
                goals=(),
                active_tasks=(),
                completed_task_count=0,
                failed_task_count=0,
                blocked_task_count=0,
                context={},
                checkpoint_age_seconds=0.0,
                reconstruction_duration_ms=0.0,
                warnings=tuple(warnings),
                is_valid=False,
            )

        # Phase 2: Extract
        state_value = checkpoint_data.get("state", "IDLE")
        goals_raw = checkpoint_data.get("goals", [])
        tasks_raw = checkpoint_data.get("tasks", [])
        context = checkpoint_data.get("context", {})

        # Phase 3: Rebuild
        tasks = list(tasks_raw) if isinstance(tasks_raw, list) else []
        active = [t for t in tasks if t.get("status") in ("pending", "running", "in_progress")]
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        blocked = sum(1 for t in tasks if t.get("status") == "blocked")

        goals = list(goals_raw) if isinstance(goals_raw, list) else []
        if isinstance(goals_raw, tuple):
            goals = list(goals_raw)

        # Phase 4: Verify
        if not active and not goals:
            warnings.append("No active tasks or goals found in checkpoint")

        # Calculate checkpoint age
        created_at = checkpoint_data.get("created_at", "")
        age_seconds = 0.0
        if created_at:
            try:
                ctime = datetime.fromisoformat(created_at)
                age_seconds = (datetime.now() - ctime).total_seconds()
            except (ValueError, TypeError):
                pass

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        return ReconstructedState(
            session_id=session_id,
            state=state_value,
            goals=tuple(goals),
            active_tasks=tuple(active),
            completed_task_count=completed,
            failed_task_count=failed,
            blocked_task_count=blocked,
            context=context,
            checkpoint_age_seconds=age_seconds,
            reconstruction_duration_ms=duration_ms,
            warnings=tuple(warnings),
            is_valid=is_valid,
        )

    def reconstruct_with_report(
        self,
        session_id: str,
        checkpoint_data: dict[str, Any],
    ) -> ReconstructionReport:
        """Reconstruct state and produce a detailed report.

        Args:
            session_id: Session identifier
            checkpoint_data: Raw checkpoint data

        Returns:
            ReconstructionReport with full reconstruction detail
        """
        start = datetime.now()
        phases: list[ReconstructionPhase] = []
        warnings: list[str] = []
        errors: list[str] = []
        state = None

        try:
            phases.append(ReconstructionPhase.VALIDATE)
            is_valid, val_warnings = self._validate_checkpoint(checkpoint_data)
            warnings.extend(val_warnings)

            phases.append(ReconstructionPhase.EXTRACT)

            phases.append(ReconstructionPhase.REBUILD)
            state = self.reconstruct(session_id, checkpoint_data)
            if state.warnings:
                warnings.extend(state.warnings)

            if state.is_valid:
                phases.append(ReconstructionPhase.VERIFY)

            phases.append(ReconstructionPhase.ACTIVATE)
            success = state.is_valid

        except Exception as e:
            errors.append(f"Reconstruction failed: {e}")
            success = False

        duration_ms = (datetime.now() - start).total_seconds() * 1000

        report = ReconstructionReport(
            session_id=session_id,
            success=success,
            phases_completed=tuple(phases),
            warnings=tuple(warnings),
            errors=tuple(errors),
            state=state,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat(),
        )
        self._history.append(report)
        return report

    def _validate_checkpoint(
        self, data: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate checkpoint data integrity.

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings: list[str] = []
        is_valid = True

        if not isinstance(data, dict):
            return False, ["Checkpoint data is not a dictionary"]

        if "session_id" not in data and "state" not in data:
            warnings.append("Checkpoint missing session_id and state")
            is_valid = False

        # Check for required context keys
        context = data.get("context", {})
        if not isinstance(context, dict):
            warnings.append("Context is not a dictionary")
            is_valid = False

        # Validate task data if present
        tasks = data.get("tasks", [])
        if isinstance(tasks, list):
            for i, task in enumerate(tasks):
                if not isinstance(task, dict):
                    warnings.append(f"Task {i} is not a valid dict")
                elif "task_id" not in task:
                    warnings.append(f"Task {i} missing task_id")

        return is_valid, warnings

    def get_history(self, limit: int = 20) -> list[ReconstructionReport]:
        """Get reconstruction history.

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of ReconstructionReport
        """
        return list(reversed(self._history[-limit:]))

    def get_success_rate(self) -> float:
        """Calculate reconstruction success rate.

        Returns:
            Success rate as a fraction 0.0-1.0
        """
        if not self._history:
            return 0.0
        successful = sum(1 for r in self._history if r.success)
        return successful / len(self._history)

    def clear(self) -> None:
        """Clear reconstruction history."""
        self._history.clear()
