"""File operation tools for reading, writing, and managing files."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class FileOperation(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    COPY = "copy"
    MOVE = "move"
    LIST = "list"
    EXISTS = "exists"
    STAT = "stat"


@dataclass(frozen=True)
class FileInfo:
    path: str
    size_bytes: int
    is_dir: bool
    modified_at: float
    permissions: str


class FileTool:
    """File system operations with sandbox-aware path resolution.

    Usage::

        tool = FileTool(workspace_root="/app/workspace")
        result = tool.read("src/main.py")
        files = tool.list("src/", pattern="*.py")
    """

    def __init__(self, workspace_root: str = ".") -> None:
        self._root = Path(workspace_root).resolve()

    def resolve(self, path: str) -> Path:
        """Resolve a path within the workspace root."""
        resolved = (self._root / path).resolve()
        if not str(resolved).startswith(str(self._root)):
            raise ValueError(f"Path traversal detected: {path}")
        return resolved

    def read(self, path: str, encoding: str = "utf-8") -> str:
        resolved = self.resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return resolved.read_text(encoding=encoding)

    def write(self, path: str, content: str, encoding: str = "utf-8") -> FileInfo:
        resolved = self.resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding=encoding)
        return self._make_info(resolved)

    def delete(self, path: str) -> None:
        resolved = self.resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if resolved.is_dir():
            resolved.rmdir()
        else:
            resolved.unlink()

    def list(self, path: str = ".", pattern: str = "*") -> list[FileInfo]:
        resolved = self.resolve(path)
        if not resolved.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return [
            self._make_info(p)
            for p in resolved.glob(pattern)
        ]

    def exists(self, path: str) -> bool:
        return self.resolve(path).exists()

    def stat(self, path: str) -> FileInfo:
        resolved = self.resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return self._make_info(resolved)

    def copy(self, src: str, dst: str) -> FileInfo:
        import shutil

        src_path = self.resolve(src)
        dst_path = self.resolve(dst)
        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {src}")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        return self._make_info(dst_path)

    def move(self, src: str, dst: str) -> FileInfo:
        src_path = self.resolve(src)
        dst_path = self.resolve(dst)
        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {src}")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.rename(dst_path)
        return self._make_info(dst_path)

    @staticmethod
    def _make_info(p: Path) -> FileInfo:
        st = p.stat()
        return FileInfo(
            path=str(p),
            size_bytes=st.st_size,
            is_dir=p.is_dir(),
            modified_at=st.st_mtime,
            permissions=oct(st.st_mode)[-3:],
        )


@dataclass(frozen=True)
class FileDiff:
    file_path: str
    additions: int
    deletions: int
    hunks: int
