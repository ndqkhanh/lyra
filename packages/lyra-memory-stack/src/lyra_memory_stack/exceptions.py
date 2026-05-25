"""Custom exceptions for the lyra-memory-stack package."""

from __future__ import annotations


class MemoryError(Exception):
    """Base exception for all memory errors."""


class MemoryNotFoundError(MemoryError):
    """Raised when a memory entry is not found."""

    def __init__(self, memory_id: str, memory_type: str = "") -> None:
        self.memory_id = memory_id
        self.memory_type = memory_type
        suffix = f" of type '{memory_type}'" if memory_type else ""
        super().__init__(f"Memory entry '{memory_id}'{suffix} not found")


class MemoryCapacityError(MemoryError):
    """Raised when a memory store has reached capacity."""

    def __init__(self, store: str, limit: int, current: int) -> None:
        self.store = store
        self.limit = limit
        self.current = current
        super().__init__(
            f"Memory store '{store}' at capacity: {current}/{limit}"
        )


class PrivacyViolationError(MemoryError):
    """Raised when a privacy tier restriction is violated."""

    def __init__(self, tier: str, operation: str) -> None:
        self.tier = tier
        self.operation = operation
        super().__init__(
            f"Privacy violation: cannot '{operation}' on tier '{tier}'"
        )


class DecayError(MemoryError):
    """Raised when a decay or pruning operation fails."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Decay operation failed: {reason}")


class DreamCycleError(MemoryError):
    """Raised when the dream cycle enrichment process fails."""

    def __init__(self, phase: str, reason: str) -> None:
        self.phase = phase
        self.reason = reason
        super().__init__(f"Dream cycle phase '{phase}' failed: {reason}")


class CompressionError(MemoryError):
    """Raised when symbolic compression fails."""

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"Compression failed for '{source}': {reason}")


class RetrievalError(MemoryError):
    """Raised when multi-layer retrieval fails."""

    def __init__(self, layer: int, reason: str) -> None:
        self.layer = layer
        self.reason = reason
        super().__init__(f"Retrieval layer {layer} failed: {reason}")
