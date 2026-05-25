"""Custom exceptions for the lyra-counterfactual package."""

from __future__ import annotations


class CounterfactualEngineError(Exception):
    """Base exception for all counterfactual engine errors."""


class AbductionError(CounterfactualEngineError):
    """Raised when the abduction step fails (e.g., incompatible evidence)."""


class ActionPredictionError(CounterfactualEngineError):
    """Raised when action prediction fails."""


class PredictionError(CounterfactualEngineError):
    """Raised when counterfactual prediction fails."""


class SCMIntegrationError(CounterfactualEngineError):
    """Raised when SCM integration encounters issues."""


class ConfidenceError(CounterfactualEngineError):
    """Raised when confidence scoring encounters invalid data."""
