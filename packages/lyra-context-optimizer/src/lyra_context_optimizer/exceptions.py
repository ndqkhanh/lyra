"""Custom exceptions for the context optimizer package."""

from __future__ import annotations


class ContextOptimizerError(Exception):
    """Base exception for all context optimizer errors."""


class CompactionError(ContextOptimizerError):
    """Raised when compaction planning or execution fails."""

    def __init__(self, reason: str, context_window_size: int | None = None) -> None:
        self.reason = reason
        self.context_window_size = context_window_size
        msg = f"Compaction failed: {reason}"
        if context_window_size is not None:
            msg += f" (window_size={context_window_size})"
        super().__init__(msg)


class CompressionError(ContextOptimizerError):
    """Raised when compression of input or output fails."""

    def __init__(self, target: str, original_size: int, detail: str = "") -> None:
        self.target = target
        self.original_size = original_size
        self.detail = detail
        msg = f"Compression failed for '{target}' ({original_size} tokens)"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class KnowledgeBlockNotFoundError(ContextOptimizerError):
    """Raised when a knowledge block is not found."""

    def __init__(self, block_id: str, registry: str = "") -> None:
        self.block_id = block_id
        self.registry = registry
        msg = f"Knowledge block '{block_id}' not found"
        if registry:
            msg += f" in registry '{registry}'"
        super().__init__(msg)


class DACSConfigError(ContextOptimizerError):
    """Raised when DACS configuration is invalid."""

    def __init__(self, agent_id: str, reason: str) -> None:
        self.agent_id = agent_id
        self.reason = reason
        super().__init__(f"DACS config error for '{agent_id}': {reason}")


class FidelityLossError(ContextOptimizerError):
    """Raised when compaction or compression would lose too much fidelity."""

    def __init__(self, fidelity_score: float, threshold: float, detail: str = "") -> None:
        self.fidelity_score = fidelity_score
        self.threshold = threshold
        self.detail = detail
        msg = (
            f"Fidelity loss too high: score={fidelity_score:.3f}, "
            f"threshold={threshold:.3f}"
        )
        if detail:
            msg += f" ({detail})"
        super().__init__(msg)
