"""Search and replace tools for codebase exploration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class SearchMode(StrEnum):
    EXACT = "exact"
    REGEX = "regex"
    GLOB = "glob"
    FUZZY = "fuzzy"


@dataclass(frozen=True)
class SearchMatch:
    file_path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int
    context_before: tuple[str, ...] = ()
    context_after: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchResult:
    query: str
    mode: SearchMode
    matches: tuple[SearchMatch, ...]
    total_files_searched: int
    duration_ms: float
    truncated: bool = False


@dataclass(frozen=True)
class ReplaceOperation:
    file_path: str
    line_number: int
    old_text: str
    new_text: str
    applied: bool = False
    error: str = ""


class SearchTool:
    """File content search with regex, glob, and fuzzy modes.

    Usage::

        tool = SearchTool(root="/app/workspace")
        results = tool.search("def main", mode=SearchMode.REGEX)
        replacements = tool.replace_all("old_func", "new_func", "*.py")
    """

    def __init__(self, root: str = ".") -> None:
        self._root = Path(root).resolve()

    def search(
        self,
        query: str,
        path: str = ".",
        mode: SearchMode = SearchMode.EXACT,
        file_pattern: str = "*",
        max_results: int = 100,
        context_lines: int = 0,
    ) -> SearchResult:
        import time

        start = time.monotonic()
        search_root = (self._root / path).resolve()
        matches: list[SearchMatch] = []
        files_searched = 0

        for file_path in search_root.rglob(file_pattern):
            if not file_path.is_file():
                continue
            files_searched += 1
            try:
                content = file_path.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            for line_num, line in enumerate(content.splitlines(), start=1):
                found = self._match_line(line, query, mode)
                if found:
                    ctx_before, ctx_after = self._get_context(
                        content, line_num, context_lines
                    )
                    matches.append(
                        SearchMatch(
                            file_path=str(file_path.relative_to(self._root)),
                            line_number=line_num,
                            line_content=line,
                            match_start=found[0],
                            match_end=found[1],
                            context_before=ctx_before,
                            context_after=ctx_after,
                        )
                    )
                    if len(matches) >= max_results:
                        return SearchResult(
                            query=query,
                            mode=mode,
                            matches=tuple(matches),
                            total_files_searched=files_searched,
                            duration_ms=(time.monotonic() - start) * 1000,
                            truncated=True,
                        )

        return SearchResult(
            query=query,
            mode=mode,
            matches=tuple(matches),
            total_files_searched=files_searched,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def replace_all(
        self,
        old: str,
        new: str,
        file_pattern: str = "*",
        dry_run: bool = True,
    ) -> list[ReplaceOperation]:
        operations: list[ReplaceOperation] = []
        for file_path in self._root.rglob(file_pattern):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            if old not in content:
                continue
            op = ReplaceOperation(
                file_path=str(file_path.relative_to(self._root)),
                line_number=0,
                old_text=old,
                new_text=new,
            )
            try:
                if not dry_run:
                    new_content = content.replace(old, new)
                    file_path.write_text(new_content)
                operations.append(op)
            except OSError:
                operations.append(
                    ReplaceOperation(
                        file_path=op.file_path,
                        line_number=0,
                        old_text=old,
                        new_text=new,
                        error="Permission denied",
                    )
                )
        return operations

    @staticmethod
    def _match_line(line: str, query: str, mode: SearchMode) -> tuple[int, int] | None:
        if mode == SearchMode.EXACT:
            idx = line.find(query)
            return (idx, idx + len(query)) if idx >= 0 else None
        if mode == SearchMode.REGEX:
            m = re.search(query, line)
            return (m.start(), m.end()) if m else None
        if mode == SearchMode.GLOB:
            import fnmatch

            return (0, len(line)) if fnmatch.fnmatch(line, f"*{query}*") else None
        return None

    @staticmethod
    def _get_context(
        content: str, line_num: int, context_lines: int
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if context_lines <= 0:
            return (), ()
        all_lines = content.splitlines()
        start = max(0, line_num - 1 - context_lines)
        end = min(len(all_lines), line_num + context_lines)
        before = tuple(all_lines[start : line_num - 1])
        after = tuple(all_lines[line_num : end])
        return before, after


@dataclass(frozen=True)
class FileIndex:
    """Pre-built file index for fast lookups."""

    root: str
    file_count: int
    total_size_bytes: int
    extension_counts: dict[str, int] = field(default_factory=dict)
    indexed_at: float = 0.0
