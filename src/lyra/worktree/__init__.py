"""
Worktree isolation layer for parallel agent sessions.

Provides:
- WorktreeManager: git worktree lifecycle (create, switch, cleanup, list)
"""

from lyra.worktree.manager import WorktreeManager

__version__ = "0.1.0"

__all__ = [
    "WorktreeManager",
]
