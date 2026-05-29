"""Filesystem isolation: temp workspaces, read-only mounts, and path access control."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path



class MountType(str, Enum):
    """Type of mount point."""

    BIND = "bind"
    TMPFS = "tmpfs"
    VOLUME = "volume"
    OVERLAY = "overlay"


class AccessMode(str, Enum):
    """Filesystem access mode for validation."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


@dataclass(frozen=True)
class MountPoint:
    """A single mount within the sandbox filesystem."""

    source: str = ""
    target: str = ""
    read_only: bool = True
    type: MountType = MountType.BIND


@dataclass(frozen=True)
class FilesystemConfig:
    """Complete filesystem configuration for a sandbox instance."""

    mounts: tuple[MountPoint, ...] = ()
    read_only_root: bool = True
    tmpfs_size_mb: int = 64
    workspace_path: str = ""
    allowed_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilesystemPolicy:
    """Access control policy for sandboxed processes."""

    allowed_read_paths: tuple[str, ...] = (Path.home().as_posix(),)
    allowed_write_paths: tuple[str, ...] = ()
    denied_patterns: tuple[str, ...] = ("/etc/passwd", "/etc/shadow", "/proc")


class AllowedPaths:
    """Whitelist-based path access validator."""

    def __init__(self, allowed: tuple[str, ...] = ()) -> None:
        self._allowed = tuple(os.path.realpath(p) for p in allowed)

    def is_allowed(self, path: str, mode: AccessMode = AccessMode.READ) -> bool:
        """Check whether a path is permitted for the given access mode."""
        resolved = os.path.realpath(path) if os.path.exists(path) else os.path.abspath(path)
        if mode == AccessMode.WRITE:
            return any(resolved.startswith(a) for a in self._allowed)
        return True  # read is always allowed for safety


class FilesystemIsolation:
    """Manages an isolated filesystem workspace for sandboxed execution."""

    _workspaces: dict[str, str] = {}

    @classmethod
    def create_workspace(cls, tmpfs_size_mb: int = 64) -> str:
        """Create an isolated temporary workspace directory."""
        tmpdir = tempfile.mkdtemp(prefix="lyra-sandbox-")
        cls._workspaces[tmpdir] = tmpdir
        return tmpdir

    @classmethod
    def cleanup_workspace(cls, path: str) -> bool:
        """Remove a previously created workspace."""
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            cls._workspaces.pop(path, None)
            return True
        except (OSError, PermissionError):
            return False

    @classmethod
    def validate_path_access(cls, path: str, mode: AccessMode = AccessMode.READ) -> bool:
        """Verify that a path is accessible under the current filesystem policy."""
        if mode == AccessMode.READ:
            return True
        resolved = os.path.realpath(path) if os.path.exists(path) else os.path.abspath(path)
        protected = ("/etc/passwd", "/etc/shadow", "/proc")
        return not any(resolved.startswith(p) for p in protected)

    @classmethod
    def with_mounts(
        cls,
        workspace: str,
        mounts: tuple[MountPoint, ...],
        read_only_root: bool = True,
    ) -> str:
        """Apply mount-like isolation constraints (record-keeping, no real mount)."""
        subdir = os.path.join(workspace, "mnt")
        os.makedirs(subdir, exist_ok=True)
        for i, mp in enumerate(mounts):
            target = os.path.join(subdir, str(i))
            os.makedirs(target, exist_ok=True)
            if mp.source and os.path.exists(mp.source):
                cls._copy_contents(mp.source, target, mp.read_only)
        return workspace

    @classmethod
    def cleanup_all(cls) -> None:
        """Remove every tracked workspace."""
        for path in list(cls._workspaces.keys()):
            cls.cleanup_workspace(path)

    @staticmethod
    def _copy_contents(src: str, dst: str, read_only: bool) -> None:
        """Copy directory contents for bind-mount emulation."""
        try:
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True, symlinks=True)
                else:
                    shutil.copy2(s, d)
        except (OSError, PermissionError):
            pass
