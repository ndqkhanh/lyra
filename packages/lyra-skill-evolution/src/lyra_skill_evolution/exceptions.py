"""Custom exceptions for the skill evolution package."""

from __future__ import annotations


class EvolutionError(Exception):
    """Base exception for all skill evolution errors."""


class PatchError(EvolutionError):
    """Raised when a skill patch operation fails."""

    def __init__(self, patch_id: str, reason: str) -> None:
        self.patch_id = patch_id
        super().__init__(f"Patch '{patch_id}' failed: {reason}")


class BenchmarkError(EvolutionError):
    """Raised when benchmark execution fails."""

    def __init__(self, task_id: str, reason: str) -> None:
        self.task_id = task_id
        super().__init__(f"Benchmark task '{task_id}' failed: {reason}")


class RegressionError(EvolutionError):
    """Raised when regression testing detects a failure."""

    def __init__(self, test_id: str, message: str) -> None:
        self.test_id = test_id
        super().__init__(f"Regression test '{test_id}' failed: {message}")


class VersionError(EvolutionError):
    """Raised when version management fails."""

    def __init__(self, skill_id: str, reason: str) -> None:
        self.skill_id = skill_id
        super().__init__(f"Version error for '{skill_id}': {reason}")


class MetricsError(EvolutionError):
    """Raised when evolution metrics computation fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Metrics error: {reason}")
