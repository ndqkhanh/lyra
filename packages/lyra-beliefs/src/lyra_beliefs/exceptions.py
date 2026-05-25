"""Custom exceptions for the beliefs package."""

from __future__ import annotations


class BeliefError(Exception):
    """Base exception for all belief system errors."""


class BeliefNotFoundError(BeliefError):
    """Raised when a belief is not found."""

    def __init__(self, belief_id: str) -> None:
        self.belief_id = belief_id
        super().__init__(f"Belief '{belief_id}' not found")


class InconsistentBeliefError(BeliefError):
    """Raised when contradictory beliefs are detected."""

    def __init__(self, belief_a: str, belief_b: str, reason: str) -> None:
        self.belief_a = belief_a
        self.belief_b = belief_b
        super().__init__(f"Inconsistent beliefs '{belief_a}' and '{belief_b}': {reason}")


class InferenceError(BeliefError):
    """Raised when belief inference fails."""

    def __init__(self, message: str, premises: list[str] | None = None) -> None:
        self.premises = premises or []
        super().__init__(f"Inference failed: {message}")


class KnowledgeBaseError(BeliefError):
    """Raised when knowledge base operations fail."""

    def __init__(self, operation: str, reason: str) -> None:
        self.operation = operation
        super().__init__(f"Knowledge base '{operation}' failed: {reason}")


class UpdateError(BeliefError):
    """Raised when belief update fails."""

    def __init__(self, belief_id: str, reason: str) -> None:
        self.belief_id = belief_id
        super().__init__(f"Belief update failed for '{belief_id}': {reason}")


class RevisionError(BeliefError):
    """Raised when belief revision fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Belief revision failed: {message}")


class SourceReliabilityError(BeliefError):
    """Raised when a belief source is unreliable."""

    def __init__(self, source: str, reliability: float) -> None:
        self.source = source
        self.reliability = reliability
        super().__init__(f"Source '{source}' has low reliability ({reliability:.2f})")
