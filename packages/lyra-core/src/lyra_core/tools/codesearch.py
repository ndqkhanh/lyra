"""Agent-facing codesearch tool (opencode parity).

Why a dedicated tool when ``grep``/``rg`` already exist? Two reasons:

1. **Deterministic shape.** The tool returns a list of
   ``{path, line, column, text}`` dicts so the LLM can chain into an
   ``apply_patch`` call without re-parsing shell output.
2. **Sandbox-safe fallback.** The tool auto-detects ``rg`` for speed
   but falls back to a pure-Python walker when ripgrep is unavailable
   or the sandbox blocks subprocesses — so the CI environment and the
   real dev loop both light up the same tool surface.

The tool is registered with the same ``__tool_schema__`` shape as the
other builtins so ``AgentLoop._tool_defs`` can advertise it to the
model unchanged.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator


@dataclass(frozen=True)
class CodesearchHit:
    """One match returned by the tool."""

    path: str
    line: int
    column: int
    text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "text": self.text,
        }


_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".next",
        ".turbo",
        ".lyra",
    }
)

# Files we never search into — avoids binary crashes in the pure-Python path.
_TEXT_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
        ".toml", ".md", ".rst", ".txt", ".html", ".css", ".scss", ".sh",
        ".rs", ".go", ".java", ".kt", ".swift", ".sql", ".c", ".h",
        ".cpp", ".hpp", ".cs", ".rb", ".php",
    }
)


def _python_search(
    *,
    pattern: str,
    root: Path,
    flags: int,
    max_hits: int,
) -> Iterator[CodesearchHit]:
    compiled = re.compile(pattern, flags)
    for path in _walk(root):
        if path.suffix not in _TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in compiled.finditer(line):
                rel = path.relative_to(root).as_posix()
                yield CodesearchHit(
                    path=rel, line=lineno, column=m.start() + 1, text=line
                )
                max_hits -= 1
                if max_hits <= 0:
                    return


def _walk(root: Path) -> Iterable[Path]:
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name in _IGNORE_DIRS:
                    continue
                stack.append(entry)
                continue
            yield entry


def _rg_search(
    *,
    pattern: str,
    root: Path,
    case_insensitive: bool,
    max_hits: int,
) -> list[CodesearchHit]:
    """Shell out to ripgrep with a structured `--json` parse.

    Falls back to the python path if ``rg`` is missing or the invocation
    fails (e.g. sandbox denies exec).
    """
    rg = shutil.which("rg")
    if rg is None:
        return []
    cmd = [rg, "--json", "--max-count", str(max_hits), pattern, str(root)]
    if case_insensitive:
        cmd.insert(1, "-i")
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if res.returncode not in (0, 1):
        return []

    import json

    hits: list[CodesearchHit] = []
    for line in res.stdout.splitlines():
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") != "match":
            continue
        data = evt.get("data", {})
        path = data.get("path", {}).get("text", "")
        try:
            rel = Path(path).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = path
        for sub in data.get("submatches", []):
            col = int(sub.get("start", 0)) + 1
            text = data.get("lines", {}).get("text", "").rstrip("\n")
            hits.append(
                CodesearchHit(
                    path=rel,
                    line=int(data.get("line_number", 0)),
                    column=col,
                    text=text,
                )
            )
            if len(hits) >= max_hits:
                return hits
    return hits


def make_codesearch_tool(
    *, repo_root: Path | str, max_hits: int = 100
) -> Callable[..., dict]:
    """Build the LLM-callable ``codesearch`` tool.

    Args:
        repo_root: Filesystem root to search under. All returned
            paths are relative to this root.
        max_hits: Hard cap on hits returned per call; protects the LLM
            from being flooded on popular strings.
    """
    root = Path(repo_root).resolve()

    def codesearch(
        pattern: str,
        *,
        case_insensitive: bool = False,
        regex: bool = True,
    ) -> dict:
        """Search the repo for ``pattern`` (regex by default)."""
        if not pattern:
            return {"pattern": pattern, "hits": [], "error": "empty pattern"}
        flags = re.IGNORECASE if case_insensitive else 0
        search_pattern = pattern if regex else re.escape(pattern)

        hits = _rg_search(
            pattern=search_pattern,
            root=root,
            case_insensitive=case_insensitive,
            max_hits=max_hits,
        )
        if not hits:
            hits = list(
                _python_search(
                    pattern=search_pattern,
                    root=root,
                    flags=flags,
                    max_hits=max_hits,
                )
            )
        return {
            "pattern": pattern,
            "hits": [h.as_dict() for h in hits],
            "truncated": len(hits) >= max_hits,
        }

    codesearch.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "codesearch",
        "description": (
            "Search the repo for a regex / literal pattern. Returns a list "
            "of {path, line, column, text} hits suitable for chaining into "
            "apply_patch or read-then-edit workflows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "case_insensitive": {"type": "boolean", "default": False},
                "regex": {"type": "boolean", "default": True},
            },
            "required": ["pattern"],
        },
    }
    return codesearch


__all__ = ["CodesearchHit", "make_codesearch_tool"]
