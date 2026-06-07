"""
Worktree isolation layer for parallel agent sessions.

Provides:

- :class:`WorktreeManager`: git worktree lifecycle (create, switch, cleanup, list)
  plus non-git fallback (:meth:`~WorktreeManager.create_fallback`) and
  session binding (:meth:`~WorktreeManager.bind_session` / ``unbind``).
- :class:`LyraInclude`: ``.lyrainclude`` pattern parsing and file filtering.
"""

from lyra.worktree.lyrainclude import (
    LyraInclude,
    WorktreeIncludeError,
    copy_included_files,
    create_default_lyrainclude,
    load_gitignore,
    load_patterns,
)
from lyra.worktree.manager import (
    SessionBindInfo,
    WorktreeCleanupError,
    WorktreeCreateError,
    WorktreeError,
    WorktreeFallbackError,
    WorktreeInfo,
    WorktreeManager,
    WorktreeSwitchError,
)

__version__ = "0.1.0"

__all__ = [
    "LyraInclude",
    "SessionBindInfo",
    "WorktreeCleanupError",
    "WorktreeCreateError",
    "WorktreeError",
    "WorktreeFallbackError",
    "WorktreeIncludeError",
    "WorktreeInfo",
    "WorktreeManager",
    "WorktreeSwitchError",
    "copy_included_files",
    "create_default_lyrainclude",
    "load_gitignore",
    "load_patterns",
]
