"""
Research subsystem — Deep Research Pipeline (P6).

Orchestrates query analysis, parallel search, content extraction,
workspace report synthesis (via S4), and citation verification.
"""

from src.research.pipeline import (
    SearchResult,
    Citation,
    ResearchReport,
    DeepResearchPipeline,
)

__all__ = [
    "SearchResult",
    "Citation",
    "ResearchReport",
    "DeepResearchPipeline",
]
