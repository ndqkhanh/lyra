"""
Writing Quality Module

Implements AI slop detection and 5-pass editing pipeline.
Based on Academic Research Skills repository best practices.
"""

from .ai_detector import (
    AIContentDetector,
    AIDetectionResult,
    AIPattern,
)
from .five_pass_editor import (
    FivePassEditor,
    EditPass,
    EditResult,
)
from .burstiness_analyzer import (
    BurstinessAnalyzer,
    BurstinessResult,
)

__all__ = [
    "AIContentDetector",
    "AIDetectionResult",
    "AIPattern",
    "FivePassEditor",
    "EditPass",
    "EditResult",
    "BurstinessAnalyzer",
    "BurstinessResult",
]
