"""Phase 1 native tools: Read, Glob, Grep, Edit, Write.

All tools share a ``repo_root`` that defines the workspace boundary. They
reject paths that resolve outside this boundary (via ``Path.resolve()`` +
``Path.is_relative_to`` on 3.9 we roll our own).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

from harness_core.tools import Tool, ToolError, ToolRegistry
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve_under_root(repo_root: Path, raw: str) -> Path:
    """Resolve ``raw`` as a path and verify it is under ``repo_root``.

    Uses realpath so symlinks cannot escape; rejects with ``ToolError`` on
    escape. This is a cheap sandbox; real sandboxing is a Phase-7 concern.
    """
    repo_root = Path(repo_root).resolve()
    if os.path.isabs(raw):
        p = Path(raw).resolve()
    else:
        p = (repo_root / raw).resolve()
    try:
        p.relative_to(repo_root)
    except ValueError as e:
        raise ToolError(
            f"path escape rejected: {raw!r} resolves outside repo_root ({repo_root})"
        ) from e
    return p


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class _ReadArgs(BaseModel):
    path: str = Field(..., description="Path relative to repo root or absolute inside it.")
    offset: int = Field(0, ge=0, description="Zero-indexed starting line.")
    limit: Optional[int] = Field(  # noqa: UP045 - pydantic v2 runtime-eval on py39
        default=None, ge=1, description="Max lines to return; None = all."
    )


class ReadTool(Tool):
    name = "Read"
    description = "Read a file under the repo root. Supports optional offset/limit."
    risk = "low"
    writes = False
    ArgsModel = _ReadArgs  # pyright: ignore[reportAssignmentType]

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def run(self, args: Any) -> str:
        a: _ReadArgs = args  # type: ignore[assignment]
        p = _resolve_under_root(self.repo_root, a.path)
        if not p.exists():
            raise ToolError(f"file not found: {a.path!r}")
        if not p.is_file():
            raise ToolError(f"not a file: {a.path!r}")
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ToolError(f"read failed: {e}") from e
        lines = text.splitlines()
        start = a.offset
        stop = len(lines) if a.limit is None else min(len(lines), start + a.limit)
        chunk = lines[start:stop]
        # Human-friendly header: lands as the result preview in the REPL
        # tool-card. Plain prose beats the angle-bracket repr (which
        # users perceived as a debug escape sequence).
        header = (
            f"read {a.path} (lines {start + 1}-{stop} of {len(lines)})"
        )
        body = "\n".join(chunk)
        return f"{header}\n{body}\n"


# ---------------------------------------------------------------------------
# Glob
# ---------------------------------------------------------------------------


class _GlobArgs(BaseModel):
    pattern: str = Field(
        ...,
        description=(
            "Glob pattern (supports ** for recursion). Examples: "
            "'**/*.py', 'src/**/*.ts', 'packages/lyra-cli/**/*'. "
            "Bare directory references like 'packages/' or 'packages/**' are "
            "auto-expanded to match files inside."
        ),
    )
    limit: int = Field(200, ge=1, le=10_000)


class GlobTool(Tool):
    name = "Glob"
    description = (
        "Find files matching a glob pattern under the repo root. "
        "Use '**/*' for recursive file matching; a bare directory like "
        "'packages/' is auto-expanded to 'packages/**/*'."
    )
    risk = "low"
    writes = False
    ArgsModel = _GlobArgs  # pyright: ignore[reportAssignmentType]

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    @staticmethod
    def _normalize_pattern(pattern: str) -> str:
        """Rewrite common dir-only patterns into file-matching ones.

        pathlib's ``**`` matches **directories only**, so ``packages/**``
        returns zero hits once we filter to ``is_file()``. Users (and
        LLMs) write ``packages/**`` expecting "everything under
        packages", so fix it transparently.
        """
        p = pattern.strip()
        if not p:
            return p
        if p.endswith("/**"):
            return p + "/*"
        if p == "**":
            return "**/*"
        if p.endswith("/"):
            return p + "**/*"
        return p

    def run(self, args: Any) -> str:
        a: _GlobArgs = args  # type: ignore[assignment]
        pattern = self._normalize_pattern(a.pattern)
        matches = sorted(self.repo_root.glob(pattern))
        matches = [m for m in matches if m.is_file()]
        truncated = False
        if len(matches) > a.limit:
            matches = matches[: a.limit]
            truncated = True
        rels = [str(m.relative_to(self.repo_root)) for m in matches]
        # Echo the *normalised* pattern so the LLM/user can learn the
        # canonical form from the trace.
        if pattern == a.pattern:
            shown = pattern
        else:
            shown = f"{a.pattern} → {pattern}"
        suffix = " (truncated)" if truncated else ""
        n = len(rels)
        header = f"glob '{shown}' → {n} file{'s' if n != 1 else ''}{suffix}"
        return f"{header}\n" + "\n".join(rels) + "\n"


# ---------------------------------------------------------------------------
# Grep
# ---------------------------------------------------------------------------


class _GrepArgs(BaseModel):
    pattern: str = Field(..., description="Regex pattern (Python re).")
    path: Optional[str] = Field(  # noqa: UP045 - pydantic v2 runtime-eval on py39
        default=None, description="Subdirectory to restrict search."
    )
    file_glob: Optional[str] = Field(  # noqa: UP045 - pydantic v2 runtime-eval on py39
        default=None, description="Glob filter e.g. '*.py'."
    )
    limit: int = Field(200, ge=1, le=10_000)
    ignore_case: bool = Field(default=False)


class GrepTool(Tool):
    name = "Grep"
    description = "Search file contents for a regex under the repo root."
    risk = "low"
    writes = False
    ArgsModel = _GrepArgs  # pyright: ignore[reportAssignmentType]

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def run(self, args: Any) -> str:
        a: _GrepArgs = args  # type: ignore[assignment]
        root = (
            _resolve_under_root(self.repo_root, a.path)
            if a.path
            else self.repo_root
        )
        if not root.exists():
            raise ToolError(f"grep path not found: {a.path!r}")
        flags = re.IGNORECASE if a.ignore_case else 0
        try:
            pat = re.compile(a.pattern, flags)
        except re.error as e:
            raise ToolError(f"invalid regex: {e}") from e

        hits: list[str] = []
        glob_filter = a.file_glob
        candidates: list[Path]
        if root.is_file():
            candidates = [root]
        else:
            candidates = [p for p in root.rglob(glob_filter or "*") if p.is_file()]

        count = 0
        for p in candidates:
            if count >= a.limit:
                break
            rel = str(p.relative_to(self.repo_root))
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if pat.search(line):
                    hits.append(f"{rel}:{i}: {line}")
                    count += 1
                    if count >= a.limit:
                        break
        n = len(hits)
        header = f"grep /{a.pattern}/ → {n} hit{'s' if n != 1 else ''}"
        return f"{header}\n" + "\n".join(hits) + "\n"


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class _WriteArgs(BaseModel):
    path: str
    content: str


class WriteTool(Tool):
    name = "Write"
    description = "Write (or overwrite) a file under the repo root; creates parent dirs."
    risk = "medium"
    writes = True
    ArgsModel = _WriteArgs  # pyright: ignore[reportAssignmentType]

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def run(self, args: Any) -> str:
        a: _WriteArgs = args  # type: ignore[assignment]
        p = _resolve_under_root(self.repo_root, a.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(a.content, encoding="utf-8")
        n_bytes = len(a.content.encode("utf-8"))
        return f"wrote {a.path} ({n_bytes} byte{'s' if n_bytes != 1 else ''})"


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


class _EditArgs(BaseModel):
    path: str
    old: str
    new: str
    replace_all: bool = False


class EditTool(Tool):
    name = "Edit"
    description = "Replace a unique substring in a file; or replace_all on demand."
    risk = "medium"
    writes = True
    ArgsModel = _EditArgs  # pyright: ignore[reportAssignmentType]

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def run(self, args: Any) -> str:
        a: _EditArgs = args  # type: ignore[assignment]
        p = _resolve_under_root(self.repo_root, a.path)
        if not p.exists():
            raise ToolError(f"edit failed: file not found: {a.path!r}")
        text = p.read_text(encoding="utf-8")
        count = text.count(a.old)
        if count == 0:
            raise ToolError(f"edit failed: old-string not found in {a.path!r}")
        if count > 1 and not a.replace_all:
            raise ToolError(
                f"edit failed: old-string appears {count} times in {a.path!r}; "
                f"not unique (pass replace_all=True or provide more context)"
            )
        if a.replace_all:
            new_text = text.replace(a.old, a.new)
        else:
            new_text = text.replace(a.old, a.new, 1)
        p.write_text(new_text, encoding="utf-8")
        n = count if a.replace_all else 1
        return f"edited {a.path} ({n} replacement{'s' if n != 1 else ''})"


# ---------------------------------------------------------------------------
# registration helper
# ---------------------------------------------------------------------------


def register_builtin_tools(
    registry: ToolRegistry,
    *,
    repo_root: Path,
    ask_user_prompter: Any = None,
) -> None:
    """Register Lyra's built-in tools into a :class:`ToolRegistry`.

    The five Phase-1 tools (Read/Write/Edit/Glob/Grep) are always
    installed. ``AskUserQuestion`` is opt-in: pass an ``ask_user_prompter``
    callable to make the agent able to pause for a structured choice.
    Without one, leaving ``AskUserQuestion`` unregistered keeps non-
    interactive runs (CI, ``--print``) from hanging on stdin reads.

    v3.13+: WebFetch and WebSearch are now registered by default for
    research and deep-dive workflows. They're read-only operations with
    URL safety validation.
    """
    registry.register(ReadTool(repo_root=repo_root))
    registry.register(WriteTool(repo_root=repo_root))
    registry.register(EditTool(repo_root=repo_root))
    registry.register(GlobTool(repo_root=repo_root))
    registry.register(GrepTool(repo_root=repo_root))

    # Web tools (v3.13+)
    try:
        from .web_fetch import WebFetchTool
        from .web_search import WebSearchTool
        registry.register(WebFetchTool())
        registry.register(WebSearchTool())
    except ImportError:
        # Optional dependencies (httpx, beautifulsoup4) not installed
        pass

    if ask_user_prompter is not None:
        from .ask_user import AskUserQuestionTool
        registry.register(AskUserQuestionTool(prompter=ask_user_prompter))
