"""CorpusMount — bound the investigate-mode agent to one filesystem root.

DCI-Agent-Lite takes ``--cwd <corpus_root>`` and assumes the agent's
shell is confined to that directory. Lyra's permissions grammar can
enforce that, but only if we describe the mount as a value object the
grammar can read and the runner can hand to ``codesearch`` and
``read_file``.

The mount is a *contract*, not a sandbox — it tells the runner which
paths are legal. The actual sandbox (process isolation, no-net flag,
chroot-style binds) lives in ``lyra_core/permissions/`` and
``lyra_core/safety/`` and reads from this object.

Cite: arXiv:2605.05242 §3; DCI-Agent-Lite README "--cwd <corpus_root>".
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path


class CorpusMountError(ValueError):
    """Raised when a CorpusMount is constructed with invalid inputs."""


@dataclass(frozen=True)
class CorpusMount:
    """A read-only-by-default corpus directory bound to an investigation.

    Attributes:
        root: Absolute directory the agent may search. All paths the
            agent returns are relative to this root.
        read_only: When ``True`` (the default), writes inside the mount
            are denied by the permissions grammar.
        max_file_bytes: Single-file size cap. Files larger than this
            are skipped by walks and rejected by reads; protects the
            agent's context from being flooded by a 4 GB log.
        excluded_globs: Path globs (relative to ``root``) that the
            walker must skip — ``.git``, ``node_modules``, etc.
            Defaults to the same ignore-set ``codesearch`` already uses.
    """

    root: Path
    read_only: bool = True
    max_file_bytes: int = 10_000_000
    excluded_globs: tuple[str, ...] = field(
        default=(
            ".git/**", ".hg/**", ".svn/**",
            "node_modules/**", ".venv/**", "venv/**", "env/**",
            "__pycache__/**", ".pytest_cache/**", ".mypy_cache/**",
            ".ruff_cache/**", "dist/**", "build/**",
            ".next/**", ".turbo/**", ".lyra/**",
        ),
    )

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            raise CorpusMountError(
                f"root must be a Path, got {type(self.root).__name__}"
            )
        if not self.root.is_absolute():
            raise CorpusMountError(
                f"root must be absolute, got {self.root!r}"
            )
        if self.max_file_bytes <= 0:
            raise CorpusMountError(
                f"max_file_bytes must be positive, got {self.max_file_bytes}"
            )

    def contains(self, path: Path) -> bool:
        """Return ``True`` iff *path* resolves under :attr:`root`.

        Symlinks pointing outside the mount return ``False`` — the
        whole point of the contract is to defeat that escape.
        """
        try:
            resolved = path.resolve()
            resolved.relative_to(self.root.resolve())
        except (OSError, ValueError):
            return False
        return True

    def is_excluded(self, relpath: str) -> bool:
        """Return ``True`` iff *relpath* (POSIX, relative) matches a glob."""
        return any(fnmatch.fnmatch(relpath, g) for g in self.excluded_globs)

    def assert_readable(self, path: Path) -> Path:
        """Resolve *path*, verify it is inside the mount and within size.

        Raises:
            CorpusMountError: if *path* escapes the mount, doesn't exist,
                or exceeds :attr:`max_file_bytes`.
        """
        if not self.contains(path):
            raise CorpusMountError(f"path escapes mount: {path}")
        resolved = path.resolve()
        if not resolved.exists():
            raise CorpusMountError(f"path does not exist: {path}")
        if resolved.is_file():
            size = resolved.stat().st_size
            if size > self.max_file_bytes:
                raise CorpusMountError(
                    f"file exceeds max_file_bytes ({size} > "
                    f"{self.max_file_bytes}): {path}"
                )
        return resolved


__all__ = ["CorpusMount", "CorpusMountError"]
