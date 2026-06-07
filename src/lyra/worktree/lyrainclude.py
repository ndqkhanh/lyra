"""
Worktree Include — copy gitignored files into new worktrees.

Implements the ``.lyrainclude`` file protocol: a ``.gitignore``-syntax file
that lists gitignored files (``.env``, ``.env.local``, ``config/secrets.json``,
etc.) which should be copied into every new worktree so that isolated sessions
have their environment and credentials.

The :class:`LyraInclude` class wraps pattern loading and provides
``should_include`` and ``apply_lyrainclude`` for filtering files in a
worktree tree. The free functions (``load_patterns``, ``copy_included_files``,
``create_default_lyrainclude``) are retained for backward compatibility.

Only *gitignored* files matching the patterns are copied -- tracked files
are never duplicated (avoiding the ``.worktreeinclude`` footgun where a
tracked file gets stale copies in every worktree).

References
----------
- Claude Code Worktrees: https://code.claude.com/docs/en/worktrees
- Lyra section 5.1 rmux Rebuild Plan: plans/5.1-rmux-rebuild.md
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

_INCLUDE_FILE_NAME = ".lyrainclude"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WorktreeIncludeError(Exception):
    """Raised when ``.lyrainclude`` processing fails."""


# ---------------------------------------------------------------------------
# LyraInclude class
# ---------------------------------------------------------------------------


@dataclass
class LyraInclude:
    """Parsed ``.lyrainclude`` with include/exclude logic.

    Loads patterns from ``.lyrainclude`` and ``.gitignore`` (if present)
    and provides methods to query whether a file should be included in a
    worktree and to apply filtering to an existing worktree directory.

    Usage::

        inc = LyraInclude.load(repo_root)
        if inc.should_include("config/secrets.json"):
            ...
        removed = inc.apply_lyrainclude(worktree_path)
    """

    repo_root: Path
    include_spec: Optional["pathspec.PathSpec"] = field(default=None, repr=False)
    gitignore_spec: Optional["pathspec.PathSpec"] = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        repo_root: Path,
        include_spec: Optional["pathspec.PathSpec"] = None,
        gitignore_spec: Optional["pathspec.PathSpec"] = None,
    ) -> LyraInclude:
        """Load ``.lyrainclude`` and ``.gitignore`` from *repo_root*.

        Parameters
        ----------
        repo_root:
            Repository root directory.
        include_spec:
            Optional pre-compiled ``.lyrainclude`` spec. When ``None`` the
            file is loaded automatically.
        gitignore_spec:
            Optional pre-compiled ``.gitignore`` spec. When ``None`` the
            file is loaded automatically.

        Returns
        -------
        LyraInclude instance ready for querying.
        """
        if include_spec is None:
            include_spec = _load_spec(repo_root, _INCLUDE_FILE_NAME)

        if gitignore_spec is None:
            gitignore_spec = _load_spec(repo_root, ".gitignore")

        return cls(
            repo_root=repo_root,
            include_spec=include_spec,
            gitignore_spec=gitignore_spec,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def should_include(self, filepath: str | Path) -> bool:
        """Check whether *filepath* should be included in a worktree.

        A file is included if it matches any ``.lyrainclude`` pattern AND
        is gitignored. Tracked files (not gitignored) are never copied.

        Parameters
        ----------
        filepath:
            Relative file path (string or ``Path``) to check.

        Returns
        -------
        ``True`` if the file should be included, ``False`` otherwise.
        """
        rel = str(filepath)

        # No include spec means nothing is included
        if self.include_spec is None:
            return False

        if not self.include_spec.match_file(rel):
            return False

        # If no gitignore spec, assume file is gitignored (lenient for non-git)
        if self.gitignore_spec is None:
            return True

        return self.gitignore_spec.match_file(rel)

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def apply_lyrainclude(self, worktree_path: Path) -> list[str]:
        """Remove non-included files from *worktree_path*.

        Walks the directory tree and deletes files whose paths do not
        satisfy :meth:`should_include`.  The ``.lyrainclude`` config file
        itself is always preserved.

        Parameters
        ----------
        worktree_path:
            Directory to filter (typically a non-git fallback worktree).

        Returns
        -------
        List of relative paths that were removed.
        """
        if not worktree_path.is_dir():
            return []

        removed: list[str] = []

        for dirpath, dirnames, filenames in os.walk(worktree_path):
            dirpath_p = Path(dirpath)

            for filename in filenames:
                filepath = dirpath_p / filename
                rel_path = filepath.relative_to(worktree_path)

                # Never remove the lyrainclude config itself
                if rel_path.name == _INCLUDE_FILE_NAME:
                    continue

                if not self.should_include(rel_path):
                    try:
                        filepath.unlink()
                        removed.append(str(rel_path))
                    except OSError:
                        logger.warning("could not remove non-included file", path=str(rel_path))

            # Remove empty directories (post-file-removal check)
            # Re-scan dirnames to handle leaf dirs that are now empty
            if not any(dirpath_p.iterdir()):
                try:
                    dirpath_p.rmdir()
                except OSError:
                    pass

        if removed:
            logger.info("removed %d non-included files", len(removed))

        return removed

    def copy_included_files(self, worktree_path: Path) -> list[str]:
        """Copy gitignored files matching ``.lyrainclude`` into *worktree_path*.

        Only files that are BOTH matched by a ``.lyrainclude`` pattern AND
        gitignored are copied. Tracked files are never duplicated.

        Parameters
        ----------
        worktree_path:
            Destination worktree directory.

        Returns
        -------
        List of relative file paths that were copied.

        Raises
        ------
        WorktreeIncludeError
            If a file copy fails.
        """
        if self.include_spec is None:
            return []

        copied: list[str] = []

        for dirpath, _dirnames, filenames in os.walk(self.repo_root):
            dirpath_p = Path(dirpath)

            # Skip the worktrees and lyra internal directories
            if ".claude" in dirpath_p.parts or ".lyra" in dirpath_p.parts:
                continue

            for filename in filenames:
                filepath = dirpath_p / filename
                rel_path = filepath.relative_to(self.repo_root)

                if not self.should_include(rel_path):
                    continue

                dest = worktree_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(filepath, dest)
                    copied.append(str(rel_path))
                except OSError as exc:
                    raise WorktreeIncludeError(
                        f"Failed to copy {rel_path} to worktree: {exc}"
                    ) from exc

        if copied:
            logger.info("copied %d gitignored files to worktree %s", len(copied), worktree_path.name)

        return copied


# ---------------------------------------------------------------------------
# Module-level helpers (backward compatible)
# ---------------------------------------------------------------------------


def _load_spec(repo_root: Path, filename: str) -> Optional["pathspec.PathSpec"]:
    """Load a ``pathspec.PathSpec`` from a gitignore-style file.

    Returns ``None`` if the file does not exist or contains no patterns.
    """
    # Lazy import to keep the module import cheap when only the class is used
    import pathspec  # type: ignore[import-untyped]

    filepath = repo_root / filename
    if not filepath.is_file():
        logger.debug("no %s found at %s", filename, filepath)
        return None

    with open(filepath, "r", encoding="utf-8") as fh:
        lines = [
            ln.strip()
            for ln in fh.readlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]

    if not lines:
        return None

    logger.info("loaded %d patterns from %s", len(lines), filename)
    return pathspec.PathSpec.from_lines("gitignore", lines)


def load_patterns(repo_root: Path) -> Optional["pathspec.PathSpec"]:
    """Load ``.lyrainclude`` patterns from the repo root.

    .. deprecated::
        Prefer :meth:`LyraInclude.load` which provides richer query
        methods.

    Args:
        repo_root: The repository root directory.

    Returns:
        A compiled ``pathspec.PathSpec``, or ``None`` if no ``.lyrainclude``
        file exists.
    """
    return _load_spec(repo_root, _INCLUDE_FILE_NAME)


def load_gitignore(repo_root: Path) -> Optional["pathspec.PathSpec"]:
    """Load ``.gitignore`` patterns.

    Args:
        repo_root: The repository root directory.

    Returns:
        A compiled ``pathspec.PathSpec`` from ``.gitignore`` (may be empty).
    """
    spec = _load_spec(repo_root, ".gitignore")
    if spec is None:
        import pathspec

        return pathspec.PathSpec.from_lines("gitignore", [])
    return spec


def copy_included_files(
    repo_root: Path,
    worktree_path: Path,
    include_spec: Optional["pathspec.PathSpec"] = None,
    gitignore_spec: Optional["pathspec.PathSpec"] = None,
) -> list[str]:
    """Copy gitignored files matching ``.lyrainclude`` into a new worktree.

    .. deprecated::
        Prefer ``LyraInclude.load(repo_root).copy_included_files(worktree_path)``.

    Args:
        repo_root: The repository root (source of files).
        worktree_path: The new worktree directory (destination).
        include_spec: Pre-loaded ``.lyrainclude`` patterns, or ``None`` to
            auto-load from ``repo_root``.
        gitignore_spec: Pre-loaded ``.gitignore`` patterns, or ``None`` to
            auto-load from ``repo_root``.

    Returns:
        List of relative file paths that were copied.

    Raises:
        WorktreeIncludeError: If a file copy fails.
    """
    inc = LyraInclude.load(repo_root, include_spec=include_spec, gitignore_spec=gitignore_spec)
    return inc.copy_included_files(worktree_path)


def create_default_lyrainclude(repo_root: Path) -> Path:
    """Create a sensible default ``.lyrainclude`` if none exists.

    The default includes common gitignored config files:
    - ``.env``, ``.env.local``, ``.env.*``
    - ``config/secrets.*``, ``credentials.*``
    - ``*.pem``, ``*.key`` (private keys)

    Args:
        repo_root: The repository root.

    Returns:
        Path to the created (or existing) ``.lyrainclude`` file.
    """
    include_path = repo_root / _INCLUDE_FILE_NAME
    if include_path.exists():
        return include_path

    defaults = [
        "# Lyra worktree include -- gitignored files to copy into new worktrees",
        "# Only gitignored files matching these patterns are copied.",
        "# Tracked files are never duplicated.",
        "",
        "# Environment files",
        ".env",
        ".env.local",
        ".env.*",
        "",
        "# Secrets and credentials",
        "config/secrets.json",
        "config/secrets.*",
        "credentials.json",
        "credentials.*",
        "",
        "# API keys and certificates",
        "*.pem",
        "*.key",
        "service-account.json",
        "",
        "# Local config overrides",
        ".lyra.local.toml",
        ".lyra.local.json",
    ]

    with open(include_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(defaults) + "\n")

    logger.info("created default .lyrainclude at %s", include_path)
    return include_path


__all__ = [
    "LyraInclude",
    "WorktreeIncludeError",
    "load_patterns",
    "load_gitignore",
    "copy_included_files",
    "create_default_lyrainclude",
]
