"""Repo-map code context — Aider-style symbol extraction and ranking.

Replaces whole-file dumps with a compact token-budgeted symbol map that
shows the repository skeleton and lets the LLM ask for specific functions
on demand. The map is stable between turns and lands in the cached prefix.

Research grounding: §6.2 (Aider repo-map: tree-sitter + PageRank +
token-budgeted output), §11 step 2c ("RAG-replace file contents —
carrying the whole file across 30 turns is the largest single waste
class"), Bottom Line #4 ("replace verbatim file content with retrieval").

This implementation uses Python's stdlib ``ast`` for Python files and
regex-based extraction for other languages, so it has zero extra deps.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Symbol:
    """One extracted definition or reference."""

    name: str
    kind: str          # "class", "function", "method", "variable"
    file: str          # relative path
    line: int
    parent: str = ""   # enclosing class name for methods


@dataclass
class RepoMapEntry:
    """One file's extracted symbols."""

    file: str
    symbols: list[Symbol]
    score: float = 0.0  # PageRank-style importance score


# ---------------------------------------------------------------------------
# Language-specific regex patterns
# ---------------------------------------------------------------------------

_LANG_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    ".js": [
        ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
        ("class", re.compile(r"^\s*(?:export\s+)?class\s+(\w+)")),
        ("method", re.compile(r"^\s+(?:async\s+)?(\w+)\s*\(")),
    ],
    ".ts": [
        ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
        ("class", re.compile(r"^\s*(?:export\s+)?class\s+(\w+)")),
        ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+(\w+)")),
        ("method", re.compile(r"^\s+(?:async\s+)?(\w+)\s*\(")),
    ],
    ".go": [
        ("function", re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(")),
        ("struct", re.compile(r"^type\s+(\w+)\s+struct")),
    ],
    ".rs": [
        ("function", re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)")),
        ("struct", re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)")),
        ("impl", re.compile(r"^impl(?:<[^>]+>)?\s+(?:\w+\s+for\s+)?(\w+)")),
    ],
    ".java": [
        ("class", re.compile(r"^\s*(?:public\s+)?(?:abstract\s+)?class\s+(\w+)")),
        ("method", re.compile(
            r"^\s+(?:public|private|protected|static|\s)+\s+\w+\s+(\w+)\s*\("
        )),
    ],
}


# ---------------------------------------------------------------------------
# SymbolExtractor
# ---------------------------------------------------------------------------


class SymbolExtractor:
    """Extract symbol definitions from source files.

    Uses ``ast`` for Python (accurate) and regex for other languages
    (fast, no dependencies).

    Usage::
        extractor = SymbolExtractor()
        symbols = extractor.extract_file(Path("src/auth.py"))
    """

    def extract_file(self, path: Path) -> list[Symbol]:
        """Extract all symbols from *path*. Returns [] on parse error."""
        suffix = path.suffix.lower()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        if suffix == ".py":
            return self._extract_python(text, str(path))
        return self._extract_regex(text, str(path), suffix)

    def extract_directory(
        self,
        root: Path,
        *,
        extensions: tuple[str, ...] = (".py", ".js", ".ts", ".go", ".rs", ".java"),
        max_files: int = 200,
    ) -> list[RepoMapEntry]:
        """Recursively extract symbols from all matching files under *root*."""
        entries: list[RepoMapEntry] = []
        count = 0
        for path in sorted(root.rglob("*")):
            if count >= max_files:
                break
            if not path.is_file():
                continue
            if path.suffix.lower() not in extensions:
                continue
            if any(p in path.parts for p in (".git", "__pycache__", "node_modules", ".venv")):
                continue
            symbols = self.extract_file(path)
            if symbols:
                rel = str(path.relative_to(root))
                entries.append(RepoMapEntry(file=rel, symbols=symbols))
                count += 1
        return entries

    # ------------------------------------------------------------------
    # Python extraction via ast
    # ------------------------------------------------------------------

    def _extract_python(self, source: str, filepath: str) -> list[Symbol]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        symbols: list[Symbol] = []
        self._walk_python(tree, filepath, parent="", symbols=symbols)
        return symbols

    def _walk_python(
        self,
        node: ast.AST,
        filepath: str,
        parent: str,
        symbols: list[Symbol],
    ) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                symbols.append(
                    Symbol(
                        name=child.name,
                        kind="class",
                        file=filepath,
                        line=child.lineno,
                        parent=parent,
                    )
                )
                self._walk_python(child, filepath, parent=child.name, symbols=symbols)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "method" if parent else "function"
                symbols.append(
                    Symbol(
                        name=child.name,
                        kind=kind,
                        file=filepath,
                        line=child.lineno,
                        parent=parent,
                    )
                )
                # Don't recurse into functions for nested defs (keep map shallow)
            else:
                self._walk_python(child, filepath, parent=parent, symbols=symbols)

    # ------------------------------------------------------------------
    # Regex extraction for other languages
    # ------------------------------------------------------------------

    def _extract_regex(
        self, source: str, filepath: str, suffix: str
    ) -> list[Symbol]:
        patterns = _LANG_PATTERNS.get(suffix, [])
        if not patterns:
            return []
        symbols: list[Symbol] = []
        for lineno, line in enumerate(source.splitlines(), 1):
            for kind, pattern in patterns:
                m = pattern.match(line)
                if m:
                    name = m.group(1)
                    if name and not name.startswith("_"):
                        symbols.append(
                            Symbol(name=name, kind=kind, file=filepath, line=lineno)
                        )
                    break
        return symbols


# ---------------------------------------------------------------------------
# RepoMapRanker
# ---------------------------------------------------------------------------


class RepoMapRanker:
    """Score repo-map entries by importance to the current conversation.

    Importance combines:
    - File mentions in the active conversation (direct score boost)
    - Cross-file reference density (PageRank proxy: files with many
      incoming references from other files score higher)

    Usage::
        ranker = RepoMapRanker()
        ranked = ranker.rank(entries, active_files=["src/auth.py"])
    """

    def rank(
        self,
        entries: list[RepoMapEntry],
        *,
        active_files: list[str] | None = None,
        conversation_text: str = "",
    ) -> list[RepoMapEntry]:
        """Return entries sorted by score (highest first)."""
        active = set(active_files or [])

        # Count how many other files reference each file (by import/require)
        ref_counts = self._count_references(entries)

        scored: list[RepoMapEntry] = []
        for entry in entries:
            score = ref_counts.get(entry.file, 0) * 0.5
            # Direct mention in active set
            if any(entry.file.endswith(af) or af.endswith(entry.file) for af in active):
                score += 10.0
            # Mention in conversation text
            basename = Path(entry.file).stem
            if basename and basename in conversation_text:
                score += 2.0
            # Symbol name mentions in conversation
            for sym in entry.symbols:
                if sym.name in conversation_text:
                    score += 0.5
            scored.append(RepoMapEntry(
                file=entry.file, symbols=entry.symbols, score=score
            ))

        return sorted(scored, key=lambda e: e.score, reverse=True)

    def _count_references(self, entries: list[RepoMapEntry]) -> dict[str, int]:
        """Count how many entries reference each file's symbols."""
        symbol_to_file: dict[str, str] = {}
        for entry in entries:
            for sym in entry.symbols:
                symbol_to_file[sym.name] = entry.file

        ref_counts: dict[str, int] = {}
        for entry in entries:
            text = " ".join(sym.name for sym in entry.symbols)
            for sym_name, target_file in symbol_to_file.items():
                if target_file != entry.file and sym_name in text:
                    ref_counts[target_file] = ref_counts.get(target_file, 0) + 1
        return ref_counts


# ---------------------------------------------------------------------------
# FunctionWindowRetriever
# ---------------------------------------------------------------------------


class FunctionWindowRetriever:
    """Retrieve function/method source slices (not whole files).

    Usage::
        retriever = FunctionWindowRetriever()
        snippet = retriever.get(Path("src/auth.py"), function_name="login")
    """

    def __init__(self, *, max_lines: int = 60) -> None:
        self.max_lines = max_lines

    def get(self, path: Path, *, function_name: str) -> str | None:
        """Return the source of *function_name* from *path*, or None."""
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        if path.suffix == ".py":
            return self._get_python(source, function_name)
        return self._get_regex(source, path.suffix.lower(), function_name)

    def _get_python(self, source: str, name: str) -> str | None:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None
        lines = source.splitlines()
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name
            ):
                start = node.lineno - 1
                end = getattr(node, "end_lineno", start + self.max_lines)
                end = min(end, start + self.max_lines)
                return "\n".join(lines[start:end])
        return None

    def _get_regex(self, source: str, suffix: str, name: str) -> str | None:
        patterns = _LANG_PATTERNS.get(suffix, [])
        lines = source.splitlines()
        for i, line in enumerate(lines):
            for _, pattern in patterns:
                m = pattern.match(line)
                if m and m.group(1) == name:
                    end = min(i + self.max_lines, len(lines))
                    return "\n".join(lines[i:end])
        return None


# ---------------------------------------------------------------------------
# RepoMapCache
# ---------------------------------------------------------------------------


@dataclass
class _CacheEntry:
    mtime: float
    symbols: list[dict[str, Any]]


class RepoMapCache:
    """Disk-backed cache for extracted symbols, keyed by file mtime.

    The repo-map is stable between turns as long as files don't change.
    Cache hits mean the map lands in the Anthropic cached prefix.

    Usage::
        cache = RepoMapCache(Path(".lyra/repo_map_cache.json"))
        symbols = cache.get_or_extract(path, extractor)
    """

    def __init__(self, cache_path: Path | None = None) -> None:
        self._cache: dict[str, _CacheEntry] = {}
        self._cache_path = cache_path
        if cache_path and cache_path.exists():
            self._load(cache_path)

    def get_or_extract(
        self, path: Path, extractor: SymbolExtractor
    ) -> list[Symbol]:
        """Return cached symbols or extract and cache them."""
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return extractor.extract_file(path)

        key = str(path)
        entry = self._cache.get(key)
        if entry and entry.mtime == mtime:
            return [Symbol(**s) for s in entry.symbols]

        symbols = extractor.extract_file(path)
        self._cache[key] = _CacheEntry(
            mtime=mtime,
            symbols=[asdict(s) for s in symbols],
        )
        if self._cache_path:
            self._save(self._cache_path)
        return symbols

    def invalidate(self, path: Path) -> None:
        self._cache.pop(str(path), None)

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self._cache.items()}
        path.write_text(json.dumps(data, indent=2))

    def _load(self, path: Path) -> None:
        try:
            raw = json.loads(path.read_text())
            self._cache = {k: _CacheEntry(**v) for k, v in raw.items()}
        except (json.JSONDecodeError, TypeError, KeyError):
            self._cache = {}


# ---------------------------------------------------------------------------
# render_repo_map — format map as a compact string within a token budget
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN = 4


def render_repo_map(
    entries: list[RepoMapEntry],
    *,
    token_budget: int = 1024,
) -> str:
    """Format ranked entries as a token-budgeted symbol map string."""
    budget_chars = token_budget * _CHARS_PER_TOKEN
    lines: list[str] = ["## Repository Map\n"]
    used = len(lines[0])

    for entry in entries:
        header = f"\n### {entry.file}\n"
        if used + len(header) > budget_chars:
            break
        lines.append(header)
        used += len(header)
        for sym in entry.symbols:
            prefix = "  " if sym.parent else ""
            indicator = f"({sym.parent}.)" if sym.parent else ""
            line = f"{prefix}{sym.kind} {indicator}{sym.name}  [L{sym.line}]\n"
            if used + len(line) > budget_chars:
                lines.append("  ... [truncated]\n")
                break
            lines.append(line)
            used += len(line)

    return "".join(lines)


__all__ = [
    "Symbol",
    "RepoMapEntry",
    "SymbolExtractor",
    "RepoMapRanker",
    "FunctionWindowRetriever",
    "RepoMapCache",
    "render_repo_map",
]
