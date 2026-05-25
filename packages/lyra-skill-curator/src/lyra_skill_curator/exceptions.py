"""Custom exceptions for the lyra-skill-curator package."""
from __future__ import annotations


class CuratorError(Exception):
    """Base exception for lyra-skill-curator errors."""


class MiningError(CuratorError):
    """Raised when skill mining fails."""


class EvaluationError(CuratorError):
    """Raised when quality evaluation fails."""


class PromotionError(CuratorError):
    """Raised when skill promotion validation fails."""


class ExtractionError(CuratorError):
    """Raised when instinct extraction fails."""


class ScorerError(CuratorError):
    """Raised when confidence scoring fails."""


class SyncError(CuratorError):
    """Raised when marketplace sync fails."""
