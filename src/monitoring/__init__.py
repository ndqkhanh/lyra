"""
Monitoring module for token usage analysis and observability.

Provides tools for monitoring token consumption, identifying waste patterns,
and generating optimization recommendations.
"""

from src.monitoring.token_observatory import (
    Activity,
    ActivityCategory,
    ActivityClassifier,
    BurnReport,
    TokenObservatory,
    Turn,
    WasteAnalyzer,
    WasteInstance,
    WastePattern,
)

__version__ = "0.1.0"

__all__ = [
    # Enums
    "ActivityCategory",
    "WastePattern",
    # Data types
    "Turn",
    "Activity",
    "WasteInstance",
    "BurnReport",
    # Components
    "ActivityClassifier",
    "WasteAnalyzer",
    # Main observatory
    "TokenObservatory",
]
