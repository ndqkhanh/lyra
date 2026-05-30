"""Error Recovery Pattern Recognizer - Classifies errors and identifies patterns."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ErrorCategory(StrEnum):
    """Classification of error types."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    LOGIC = "logic"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ErrorPattern:
    """A recognized error pattern."""

    pattern_id: str
    category: ErrorCategory
    signature: str  # Fingerprint to match
    recovery_hint: str
    occurrence_count: int = 1
    first_seen: str = ""
    last_seen: str = ""


@dataclass(frozen=True)
class ErrorSequence:
    """A sequence of errors that occurred together."""

    errors: tuple[str, ...]
    categories: tuple[ErrorCategory, ...]
    successful_recovery: str | None  # Strategy that worked
    occurrence_count: int = 1


class PatternRecognizer:
    """Recognizes error patterns from execution traces.

    Features:
    - Error classification into 9 categories
    - Error pattern fingerprinting
    - Error sequence correlation
    - Recovery hint generation
    """

    def __init__(self):
        self._patterns: dict[str, ErrorPattern] = {}
        self._sequences: dict[str, ErrorSequence] = {}

    def classify(self, error: Exception, context: dict | None = None) -> ErrorCategory:
        """Classify an error into a category.

        Args:
            error: The exception to classify
            context: Optional context (file, operation, etc.)

        Returns:
            ErrorCategory
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Timeout/networking errors
        if any(kw in error_str for kw in ["timeout", "timed out", "connection"]):
            return ErrorCategory.TIMEOUT
        if "timeouterror" in error_type:
            return ErrorCategory.TIMEOUT

        # Permission errors
        if any(kw in error_str for kw in ["permission", "forbidden", "unauthorized", "access denied"]):
            return ErrorCategory.PERMISSION

        # Resource errors
        if any(kw in error_str for kw in ["memory", "out of", "quota", "rate limit", "too many"]):
            return ErrorCategory.RESOURCE

        # Validation errors
        if any(kw in error_str for kw in ["invalid", "validation", "type error", "value error"]):
            return ErrorCategory.VALIDATION

        # Dependency errors
        if any(kw in error_str for kw in ["import", "module", "dependency", "not found", "no module"]):
            return ErrorCategory.DEPENDENCY

        # Logic errors
        if any(kw in error_str for kw in ["assert", "logic", "index", "attribute"]):
            return ErrorCategory.LOGIC
        if any(kw in error_type for kw in ["keyerror", "indexerror", "attributeerror", "typeerror"]):
            return ErrorCategory.LOGIC

        # Transient errors
        if any(kw in error_str for kw in ["retry", "temporary", "unavailable", "busy"]):
            return ErrorCategory.TRANSIENT

        # Permanent errors
        if any(kw in error_str for kw in ["fatal", "critical", "unsupported", "not implement"]):
            return ErrorCategory.PERMANENT

        return ErrorCategory.UNKNOWN

    def fingerprint(self, error: Exception, context: dict | None = None) -> str:
        """Generate a fingerprint for an error pattern.

        Args:
            error: The exception to fingerprint
            context: Optional context

        Returns:
            Fingerprint string
        """
        category = self.classify(error, context)
        error_type = type(error).__name__
        msg = str(error)[:100]
        return f"{category}:{error_type}:{hash(msg) & 0xFFFF:04x}"

    def learn_pattern(self, error: Exception, context: dict | None = None) -> ErrorPattern:
        """Learn from an error occurrence.

        Args:
            error: The exception
            context: Optional context

        Returns:
            The learned ErrorPattern
        """
        signature = self.fingerprint(error, context)
        now = datetime.now().isoformat()

        if signature in self._patterns:
            existing = self._patterns[signature]
            pattern = ErrorPattern(
                pattern_id=existing.pattern_id,
                category=existing.category,
                signature=signature,
                recovery_hint=existing.recovery_hint,
                occurrence_count=existing.occurrence_count + 1,
                first_seen=existing.first_seen,
                last_seen=now,
            )
        else:
            category = self.classify(error, context)
            pattern = ErrorPattern(
                pattern_id=signature,
                category=category,
                signature=signature,
                recovery_hint=self._generate_hint(category, error),
                occurrence_count=1,
                first_seen=now,
                last_seen=now,
            )

        self._patterns[signature] = pattern
        return pattern

    def learn_sequence(
        self,
        errors: list[Exception],
        successful_recovery: str | None = None,
    ) -> ErrorSequence:
        """Learn from an error sequence.

        Args:
            errors: List of exceptions in order
            successful_recovery: Recovery strategy that worked

        Returns:
            ErrorSequence
        """
        signatures = tuple(self.fingerprint(e) for e in errors)
        categories = tuple(self.classify(e) for e in errors)
        seq_key = "|".join(signatures)

        if seq_key in self._sequences:
            existing = self._sequences[seq_key]
            sequence = ErrorSequence(
                errors=signatures,
                categories=categories,
                successful_recovery=successful_recovery or existing.successful_recovery,
                occurrence_count=existing.occurrence_count + 1,
            )
        else:
            sequence = ErrorSequence(
                errors=signatures,
                categories=categories,
                successful_recovery=successful_recovery,
                occurrence_count=1,
            )

        self._sequences[seq_key] = sequence
        return sequence

    def find_similar(self, error: Exception, limit: int = 5) -> list[ErrorPattern]:
        """Find similar error patterns.

        Args:
            error: The exception to match
            limit: Maximum number to return

        Returns:
            List of matching patterns
        """
        category = self.classify(error)
        similar = [p for p in self._patterns.values() if p.category == category]
        similar.sort(key=lambda p: p.occurrence_count, reverse=True)
        return similar[:limit]

    def _generate_hint(self, category: ErrorCategory, error: Exception) -> str:
        """Generate a recovery hint based on category."""
        hints = {
            ErrorCategory.TRANSIENT: "Retry with exponential backoff",
            ErrorCategory.PERMANENT: "Replan or escalate — error is not recoverable",
            ErrorCategory.DEPENDENCY: "Verify dependency installation and version",
            ErrorCategory.RESOURCE: "Increase resource allocation or implement quota backoff",
            ErrorCategory.LOGIC: "Review logic and add validation",
            ErrorCategory.TIMEOUT: "Increase timeout or break into smaller operations",
            ErrorCategory.PERMISSION: "Check access permissions and credentials",
            ErrorCategory.VALIDATION: "Add input validation before processing",
            ErrorCategory.UNKNOWN: "Investigate error context and classify manually",
        }
        return hints.get(category, "Investigate and classify")
