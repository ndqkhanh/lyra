"""
Worktree Include — copy gitignored files into new worktrees.

Implements the ``.lyrainclude`` file protocol: a ``.gitignore``-syntax file
that lists gitignored files (``.env``, ``.env.local``, ``config/secrets.json``,
etc.) which should be copied into every new worktree so that isolated sessions
have their environment and credentials.

Only *gitignored* files matching the patterns are copied — tracked files are
never duplicated (avoiding the ``.worktreeinclude`` footgun where a tracked
file gets stale copies in every worktree).

References
----------
- Claude Code Worktrees: https://code.claude.com/docs/en/worktrees
- Lyra §5.1 rmux Rebuild Plan: plans/5.1-rmux-rebuild.md
"""

from __future__ import annotations

import logging
import os
import pathspec
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_INCLUDE_FILE_NAME = ".lyrainclude"


class WorktreeIncludeError(Exception):
    """Raised when ``.lyrainclude`` processing fails."""


def load_patterns(repo_root: Path) -> Optional[pathspec.PathSpec]:
    """Load ``.lyrainclude`` patterns from the repo root.

    Args:
        repo_root: The repository root directory.

    Returns:
        A compiled ``pathspec.PathSpec``, or ``None`` if no ``.lyrainclude``
        file exists.
    """
    include_file = repo_root / _INCLUDE_FILE_NAME
    if not include_file.is_file():
        logger.debug("no .lyrainclude found at %s", include_file)
        return None

    with open(include_file, "r", encoding="utf-8") as fh:
        lines = [
            ln.strip()
            for ln in fh.readlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]

    if not lines:
        return None

    logger.info("loaded %d .lyrainclude patterns", len(lines))
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def load_gitignore(repo_root: Path) -> pathspec.PathSpec:
    """Load ``.gitignore`` patterns to identify which files are gitignored.

    Args:
        repo_root: The repository root directory.

    Returns:
        A compiled ``pathspec.PathSpec`` from ``.gitignore``.
    """
    gitignore = repo_root / ".gitignore"
    if not gitignore.is_file():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])

    with open(gitignore, "r", encoding="utf-8") as fh:
        lines = [
            ln.strip()
            for ln in fh.readlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]

    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def copy_included_files(
    repo_root: Path,
    worktree_path: Path,
    include_spec: Optional[pathspec.PathSpec] = None,
    gitignore_spec: Optional[pathspec.PathSpec] = None,
) -> list[str]:
    """Copy gitignored files matching ``.lyrainclude`` into a new worktree.

    Only files that are BOTH:
    1. Matched by a ``.lyrainclude`` pattern (the user wants them copied)
    2. Matched by ``.gitignore`` (they are not tracked)

    ...are copied. Tracked files are never duplicated.

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
    if include_spec is None:
        include_spec = load_patterns(repo_root)
    if include_spec is None:
        return []  # No .lyrainclude — nothing to copy

    if gitignore_spec is None:
        gitignore_spec = load_gitignore(repo_root)

    copied: list[str] = []

    # Walk the repo root looking for files that match .lyrainclude
    for dirpath, _dirnames, filenames in os.walk(repo_root):
        dirpath_p = Path(dirpath)

        # Skip the worktrees directory itself
        if ".claude" in dirpath_p.parts or ".lyra" in dirpath_p.parts:
            continue

        for filename in filenames:
            filepath = dirpath_p / filename
            rel_path = filepath.relative_to(repo_root)

            # Must match BOTH .lyrainclude AND .gitignore
            if not include_spec.match_file(str(rel_path)):
                continue
            if not gitignore_spec.match_file(str(rel_path)):
                logger.warning(
                    "skipping %s: matched .lyrainclude but is tracked by git",
                    rel_path,
                )
                continue

            # Copy the file into the worktree, preserving relative path
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
        logger.info(
            "copied %d gitignored files to worktree %s",
            len(copied),
            worktree_path.name,
        )

    return copied


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
        "# Lyra worktree include — gitignored files to copy into new worktrees",
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
