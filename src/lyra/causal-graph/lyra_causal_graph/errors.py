"""Custom exceptions for the lyra-causal-graph package."""

from __future__ import annotations


class CausalGraphError(Exception):
    """Base exception for all causal graph errors."""


class GraphConstructionError(CausalGraphError):
    """Raised when graph construction fails (e.g., insufficient data, invalid structure)."""


class InvalidNodeError(CausalGraphError):
    """Raised when referencing a node that does not exist."""


class InvalidEdgeError(CausalGraphError):
    """Raised when adding an invalid edge (e.g., creating a forbidden cycle)."""


class CycleDetectedError(InvalidEdgeError):
    """Raised when an operation would create a cycle in the causal graph."""


class InterventionError(CausalGraphError):
    """Raised when an intervention is invalid or cannot be performed."""


class AdjustmentError(CausalGraphError):
    """Raised when backdoor/front-door adjustment fails."""


class CounterfactualError(CausalGraphError):
    """Raised when counterfactual reasoning fails."""


class SCMError(CausalGraphError):
    """Raised when SCM specification or evaluation fails."""


class RootCauseError(CausalGraphError):
    """Raised when root cause analysis encounters an error."""


class EstimationError(CausalGraphError):
    """Raised when treatment effect estimation fails."""
