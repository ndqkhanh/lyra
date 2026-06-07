from __future__ import annotations


class ReasoningError(Exception):
    """Base exception for all reasoning-flow errors."""


class FlowCompositionError(ReasoningError):
    """Raised when a flow cannot be composed from the given capabilities."""


class MCTSSearchError(ReasoningError):
    """Raised when MCTS search fails to find a valid path."""


class HorizonEstimationError(ReasoningError):
    """Raised when planning-horizon estimation fails."""


class ReActLoopError(ReasoningError):
    """Raised when the ReAct loop encounters an unrecoverable error."""


class TraceError(ReasoningError):
    """Raised when trace recording or retrieval fails."""
