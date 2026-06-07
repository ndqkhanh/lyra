"""Self-rewrite exception hierarchy."""

from __future__ import annotations


class SelfRewriteError(Exception):
    """Base exception for all self-rewrite related errors."""


class HyperAgentError(SelfRewriteError):
    """Raised when HyperAgent engine operations fail."""


class GoalMutationError(SelfRewriteError):
    """Raised when goal-driven mutation operations fail."""


class FitnessError(SelfRewriteError):
    """Raised when fitness evaluation operations fail."""


class ConstraintError(SelfRewriteError):
    """Raised when constraint validation fails."""


class GenerationError(SelfRewriteError):
    """Raised when rewrite generation fails."""


class RecursionError(SelfRewriteError):
    """Raised when recursive self-improvement loop fails."""


class RewriteValidationError(SelfRewriteError):
    """Raised when rewrite validation fails."""


class ConvergenceError(SelfRewriteError):
    """Raised when the self-improvement loop cannot converge."""
