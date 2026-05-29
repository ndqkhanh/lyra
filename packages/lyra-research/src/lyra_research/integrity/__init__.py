"""
Integrity Gates Module

Implements mandatory validation checkpoints that cannot be skipped.
Based on Academic Research Skills repository best practices.
"""

from .integrity_gate import GateResult, IntegrityGate
from .validators import (
    CitationAccessibilityValidator,
    CitationFidelityValidator,
    ClaimVerificationValidator,
    CompletenessValidator,
    DuplicationDetector,
    MinimumSourceCountValidator,
    SourceDiversityValidator,
    TemporalConsistencyValidator,
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
