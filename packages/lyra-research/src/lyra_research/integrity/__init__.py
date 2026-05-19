"""
Integrity Gates Module

Implements mandatory validation checkpoints that cannot be skipped.
Based on Academic Research Skills repository best practices.
"""

from .integrity_gate import IntegrityGate, GateResult
from .validators import (
    MinimumSourceCountValidator,
    SourceDiversityValidator,
    CitationAccessibilityValidator,
    DuplicationDetector,
    CitationFidelityValidator,
    ClaimVerificationValidator,
    TemporalConsistencyValidator,
    CompletenessValidator,
)

__all__ = [
    "IntegrityGate",
    "GateResult",
    "MinimumSourceCountValidator",
    "SourceDiversityValidator",
    "CitationAccessibilityValidator",
    "DuplicationDetector",
    "CitationFidelityValidator",
    "ClaimVerificationValidator",
    "TemporalConsistencyValidator",
    "CompletenessValidator",
]
