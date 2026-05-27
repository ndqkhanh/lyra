"""Filesystem tool implementations — file_delete, file_move, file_copy, dir_create, dir_list.

Each function returns a dict suitable for LLM tool-call marshalling. All paths
are resolved relative to a repo_root (or cwd), and destructive operations are
explicitly marked.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def _resolve(path: str, root: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path(root) / p
    return p.resolve()


def _is_within_root(resolved: Path, root: Path) -> bool:
    try:
        resolved.relative_to(root)
        return True
    except ValueError:
        return False


def file_delete(
    file_path: str,
    *,
    repo_root: str = ".",
    missing_ok: bool = False,
) -> dict[str, Any]:
    """Delete a file at the specified path."""
    root = Path(repo_root).resolve()
    target = _resolve(file_path, repo_root)

    if not _is_within_root(target, root):
        return {"error": f"path outside repo root: {file_path}", "deleted": False}

    if not target.exists():
        if missing_ok:
            return {"path": str(target), "deleted": False, "reason": "not_found"}
        return {"error": f"file not found: {file_path}", "deleted": False}

    if target.is_dir():
        return {"error": f"path is a directory, use dir_delete: {file_path}", "deleted": False}

    target.unlink()
    return {"path": str(target), "deleted": True}


def file_move(
    source: str,
    destination: str,
    *,
    repo_root: str = ".",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Move or rename a file."""
    root = Path(repo_root).resolve()
    src = _resolve(source, repo_root)
    dst = _resolve(destination, repo_root)

    if not _is_within_root(src, root):
        return {"error": f"source outside repo root: {source}", "moved": False}
    if not _is_within_root(dst, root):
        return {"error": f"destination outside repo root: {destination}", "moved": False}

    if not src.exists():
        return {"error": f"source not found: {source}", "moved": False}

    if dst.exists() and not overwrite:
        return {"error": f"destination exists (use overwrite=true): {destination}", "moved": False}

    # Ensure parent dirs exist
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return {"source": str(src), "destination": str(dst), "moved": True}


def file_copy(
    source: str,
    destination: str,
    *,
    repo_root: str = ".",
    overwrite: bool = False,
    preserve_metadata: bool = True,
) -> dict[str, Any]:
    """Copy a file to a new location."""
    root = Path(repo_root).resolve()
    src = _resolve(source, repo_root)
    dst = _resolve(destination, repo_root)

    if not _is_within_root(src, root):
        return {"error": f"source outside repo root: {source}", "copied": False}
    if not _is_within_root(dst, root):
        return {"error": f"destination outside repo root: {destination}", "copied": False}

    if not src.exists():
        return {"error": f"source not found: {source}", "copied": False}

    if dst.exists() and not overwrite:
        return {"error": f"destination exists (use overwrite=true): {destination}", "copied": False}

    dst.parent.mkdir(parents=True, exist_ok=True)

    if preserve_metadata:
        shutil.copy2(str(src), str(dst))
    else:
        shutil.copy(str(src), str(dst))

    return {"source": str(src), "destination": str(dst), "copied": True}


def dir_create(
    path: str,
    *,
    repo_root: str = ".",
    parents: bool = True,
    exist_ok: bool = True,
) -> dict[str, Any]:
    """Create a new directory."""
    root = Path(repo_root).resolve()
    target = _resolve(path, repo_root)

    if not _is_within_root(target, root):
        return {"error": f"path outside repo root: {path}", "created": False}

    target.mkdir(parents=parents, exist_ok=exist_ok)
    return {"path": str(target), "created": True}


def dir_list(
    path: str | None = None,
    *,
    repo_root: str = ".",
    recursive: bool = False,
    pattern: str = "*",
    include_hidden: bool = False,
    max_entries: int = 500,
) -> dict[str, Any]:
    """List contents of a directory."""
    root = Path(repo_root).resolve()
    target = _resolve(path or ".", repo_root)

    if not _is_within_root(target, root):
        return {"error": f"path outside repo root: {path}", "entries": []}

    if not target.exists():
        return {"error": f"directory not found: {path}", "entries": []}

    if not target.is_dir():
        return {"error": f"not a directory: {path}", "entries": []}

    entries: list[dict[str, Any]] = []
    glob_iter = target.rglob(pattern) if recursive else target.glob(pattern)

    for p in glob_iter:
        if len(entries) >= max_entries:
            break
        if not include_hidden and p.name.startswith("."):
            continue
        try:
            st = p.stat()
            entries.append({
                "name": p.name,
                "path": str(p.relative_to(root)),
                "is_dir": p.is_dir(),
                "size": st.st_size,
                "modified_at": st.st_mtime,
            })
        except OSError:
            entries.append({
                "name": p.name,
                "path": str(p.relative_to(root)),
                "is_dir": p.is_dir(),
                "size": 0,
                "modified_at": 0.0,
            })

    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return {"path": str(target), "entries": entries, "count": len(entries)}


__all__ = [
    "file_delete",
    "file_move",
    "file_copy",
    "dir_create",
    "dir_list",
]
