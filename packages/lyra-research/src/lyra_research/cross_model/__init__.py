"""
Cross-Model Review Module

Implements heterogeneous model verification with disagreement resolution.
Based on Academic Research Skills repository best practices.
"""

from .cross_model_reviewer import (
    CrossModelReviewer,
    DisagreementResolution,
    ExecutionResult,
    ModelType,
    ReviewDecision,
    ReviewResult,
)

__all__ = [
    "CrossModelReviewer",
    "ExecutionResult",
    "ReviewResult",
    "DisagreementResolution",
    "ModelType",
    "ReviewDecision",
]
