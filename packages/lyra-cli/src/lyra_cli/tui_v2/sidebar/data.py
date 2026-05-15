"""Pure helpers feeding the sidebar tabs.

These return list-of-dict structures (one dict per row). Rendering
lives in :mod:`tabs`. Keeping the data layer pure lets the tests run
without Textual and lets the same helpers feed slash commands or
future sidebar variants.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Skills + MCP discovery already lives in the slash-command module —
# the sidebar layer is a thin adapter on top.
from ..commands import skills_mcp


_GLOBAL_MEMORY = Path.home() / ".claude" / "memory"
_PLAN_DIRS = (".lyra/plans", ".lyra/plan")
_MEMORY_DIRS = (".lyra/memory", ".lyra/memories", ".lyra/notes")


# ---------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------


def list_plans(root: Path) -> list[dict[str, Any]]:
    """Return plan metadata for files under ``<repo>/.lyra/plan(s)/``.

    Each entry is ``{name, path, updated, mtime}`` sorted newest-first.
    Plans are usually markdown (``*.md``) but ``.json`` shows up too —
    accept both so the tab matches the on-disk reality.
    """
    out: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for rel in _PLAN_DIRS:
        base = (root / rel).resolve()
        if not base.is_dir():
            continue
        for path in base.iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml"}:
                continue
            if path in seen:
                continue
            seen.add(path)
            stat = path.stat()
            out.append({
                "name": path.name,
                "path": str(path),
                "mtime": stat.st_mtime,
                "updated": _relative_age(stat.st_mtime),
            })
    out.sort(key=lambda e: -e["mtime"])
    return out


# ---------------------------------------------------------------------
# Skills (adapter over skills_mcp._list_skills)
# ---------------------------------------------------------------------


def list_sidebar_skills(root: Path) -> list[dict[str, Any]]:
    """Adapt the slash-command skill discovery to dict rows."""
    return [
        {"source": source, "name": name, "description": desc}
        for source, name, desc in skills_mcp._list_skills(root)
    ]


# ---------------------------------------------------------------------
# MCP (adapter)
# ---------------------------------------------------------------------


def list_mcp_servers(root: Path) -> list[dict[str, Any]]:
    """Adapt the slash-command MCP discovery to dict rows."""
    return [
        {"name": name, "transport": transport}
        for name, transport in skills_mcp._list_mcp(root)
    ]


# ---------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------


def list_memory_files(root: Path) -> list[dict[str, Any]]:
    """Return memory entries from project + global memory roots.

    Project entries (under ``<repo>/.lyra/memory/``) are labelled
    ``project``; entries under ``~/.claude/memory/`` are labelled
    ``global``. The MEMORY.md index file lives under the global root
    and is hidden from the listing — its content is metadata, not a
    note the user wrote.
    """
    out: list[dict[str, Any]] = []
    seen: set[Path] = set()
    candidates: list[tuple[str, Path]] = []
    for rel in _MEMORY_DIRS:
        candidates.append(("project", (root / rel).resolve()))
    candidates.append(("global", _GLOBAL_MEMORY))

    for source, base in candidates:
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".md":
                continue
            if path.name == "MEMORY.md":
                continue
            if path in seen:
                continue
            seen.add(path)
            out.append({
                "source": source,
                "name": path.stem,
                "path": str(path),
            })
    return out


# ---------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------


def _relative_age(mtime: float, *, now: float | None = None) -> str:
    """Render ``mtime`` as a short relative age (e.g. ``3m``, ``2h``, ``5d``)."""
    now_ts = now if now is not None else time.time()
    delta = max(0.0, now_ts - mtime)
    if delta < 60:
        return f"{int(delta)}s"
    if delta < 3600:
        return f"{int(delta / 60)}m"
    if delta < 86400:
        return f"{int(delta / 3600)}h"
    if delta < 30 * 86400:
        return f"{int(delta / 86400)}d"
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
