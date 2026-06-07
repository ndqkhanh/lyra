"""Custom exceptions for the lyra-skill-loader package."""
from __future__ import annotations


class LoaderError(Exception):
    """Base exception for all skill loader errors."""


class TriggerError(LoaderError):
    """Raised when trigger matching fails."""


class BudgetExceededError(LoaderError):
    """Raised when context budget is exceeded."""


class CompilationError(LoaderError):
    """Raised when skill compilation fails."""


class DependencyError(LoaderError):
    """Raised when dependency resolution fails."""


class ConfigError(LoaderError):
    """Raised when configuration is invalid."""
