"""Eval pipeline exception hierarchy."""

from __future__ import annotations


class EvalPipelineError(Exception):
    """Base exception for all eval pipeline errors."""


class DomainEvalError(EvalPipelineError):
    """Raised when domain evaluation fails."""


class RubricError(EvalPipelineError):
    """Raised when rubric operations fail."""


class CrossModelError(EvalPipelineError):
    """Raised when cross-model judging fails."""


class BenchGuardError(EvalPipelineError):
    """Raised when bench guard operations fail."""


class LeaderboardError(EvalPipelineError):
    """Raised when leaderboard operations fail."""


class SchedulerError(EvalPipelineError):
    """Raised when eval scheduler operations fail."""


class ReportError(EvalPipelineError):
    """Raised when report generation fails."""
