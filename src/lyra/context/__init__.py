"""
Context module for Lyra workspace state management.

Provides:
- WorkspaceReport: evolving compressed workspace representation
- CompactionStrategy: configurable compression policies
"""

from lyra.context.workspace_report import WorkspaceReport
from lyra.context.compaction import CompactionStrategy, COMPACTION_PROMPTS

__version__ = "0.1.0"

__all__ = [
    "WorkspaceReport",
    "CompactionStrategy",
    "COMPACTION_PROMPTS",
]
