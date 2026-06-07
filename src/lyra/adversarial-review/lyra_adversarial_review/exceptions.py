from __future__ import annotations


class ReviewError(Exception):
    """Base exception for all review-related errors."""


class ClaimVerificationError(ReviewError):
    """Raised when claim verification fails."""


class RecoveryError(ReviewError):
    """Raised when autonomous recovery from a failure cannot proceed."""


class CitationVerificationError(ReviewError):
    """Raised when citation verification encounters an unrecoverable issue."""


class LedgerError(ReviewError):
    """Raised when ledger operations fail."""


class ConfigurationError(ReviewError):
    """Raised when review configuration is invalid."""
