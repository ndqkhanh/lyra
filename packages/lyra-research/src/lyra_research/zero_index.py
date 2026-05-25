"""
Zero-Index Retrieval — Direct Corpus Search Without Pre-Built Indexes.

Provides tiered context management by searching the filesystem directly
using system tools (ripgrep / grep), then returning results at configurable
context levels (truncation, compaction, summarisation, full, raw).

Designed for scenarios where building and maintaining a search index is
impractical — ephemeral workspaces, one-off investigations, or extremely
large heterogeneous corpora.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

__all__ = [
    "ContextLevel",
    "SearchResult",
    "ZeroIndexConfig",
    "ZeroIndexRetriever",
    "CorpusStats",
]

_CONTEXT_LINES: Dict["ContextLevel", int] = {}


@dataclass(frozen=True)
class SearchResult:
    """A single match from a zero-index search.

    Attributes:
        file_path: Absolute path to the matching file.
        line_number: 1-based line number of the match.
        content: The matching line content.
        relevance_score: Heuristic relevance score in ``[0.0, 1.0]``.
        context_level: The :class:`ContextLevel` at which this result was
            originally fetched.
    """

    file_path: str
    line_number: int
    content: str
    relevance_score: float = 0.5
    context_level: ContextLevel = field(default_factory=lambda: ContextLevel.COMPACTION)  # noqa: F821 — forward ref handled by __future__ annotations


class ContextLevel(Enum):
    """Context depth levels for result expansion.

    Each level provides progressively more surrounding context.
    """

    TRUNCATION = 1
    """Level 1 — Only the matching line plus 1 line above/below (3 lines)."""

    COMPACTION = 2
    """Level 2 — 5 lines above/below (11 lines).  Default level."""

    SUMMARIZATION = 3
    """Level 3 — 15 lines above/below (31 lines) with LLM-friendly markers."""

    FULL = 4
    """Level 4 — 25 lines above/below (51 lines)."""

    RAW = 5
    """Level 5 — 50 lines above/below (101 lines).  Maximum detail."""


# Populate the context-line lookup now that the class exists.
_CONTEXT_LINES[ContextLevel.TRUNCATION] = 3
_CONTEXT_LINES[ContextLevel.COMPACTION] = 10
_CONTEXT_LINES[ContextLevel.SUMMARIZATION] = 30
_CONTEXT_LINES[ContextLevel.FULL] = 50
_CONTEXT_LINES[ContextLevel.RAW] = 100


@dataclass(frozen=True)
class ZeroIndexConfig:
    """Configuration for :class:`ZeroIndexRetriever`.

    Attributes:
        max_results: Maximum number of results to return per query.
        max_context_chars: Hard character limit for accumulated context.
        default_level: Default :class:`ContextLevel` for search results.
        grep_timeout_ms: Timeout (milliseconds) for each grep invocation.
        allowed_extensions: File extensions to include in searches.
    """

    max_results: int = 50
    max_context_chars: int = 50000
    default_level: ContextLevel = ContextLevel.COMPACTION
    grep_timeout_ms: int = 5000
    allowed_extensions: Tuple[str, ...] = (
        ".py", ".ts", ".tsx", ".js", ".md", ".json", ".yaml", ".toml",
    )


class ZeroIndexRetriever:
    """Search a corpus directly via ripgrep (or grep fallback).

    No pre-built index is required — every ``search()`` call runs a fresh
    filesystem scan.
    """

    def __init__(self: ZeroIndexRetriever) -> None:
        self._search_times: List[float] = []

    # ------------------------------------------------------------------
    # Core search
    # ------------------------------------------------------------------

    def search(
        self: ZeroIndexRetriever,
        query: str,
        corpus_path: str,
        config: Optional[ZeroIndexConfig] = None,
    ) -> List[SearchResult]:
        """Search the corpus for the given query.

        Uses ripgrep (``rg``) when available, falling back to ``grep -r``.
        Results are sorted by decreasing relevance score.

        Args:
            query: The text search pattern.
            corpus_path: Root directory of the corpus to search.
            config: Search configuration; uses sensible defaults when
                ``None``.

        Returns:
            A list of :class:`SearchResult` instances.
        """
        cfg = config or ZeroIndexConfig()
        start = time.perf_counter()

        raw_output = self._run_search(query, corpus_path, cfg)
        results = self._parse_output(raw_output, cfg)
        results = self._filter_by_extension(results, cfg)
        results = self._score_and_sort(results, query)

        elapsed = (time.perf_counter() - start) * 1000
        self._search_times.append(elapsed)

        return results[: cfg.max_results]

    def _run_search(
        self: ZeroIndexRetriever,
        query: str,
        corpus_path: str,
        config: ZeroIndexConfig,
    ) -> str:
        """Execute the underlying search command."""
        glob_expr = f"*.{{{','.join(e.lstrip('.') for e in config.allowed_extensions)}}}"

        # Prefer ripgrep for speed
        rg_cmd = [
            "rg",
            "--no-heading",
            "--line-number",
            "--with-filename",
            "--glob",
            glob_expr,
            "--",
            query,
            corpus_path,
        ]
        try:
            proc = subprocess.run(
                rg_cmd,
                capture_output=True,
                text=True,
                timeout=config.grep_timeout_ms / 1000,
            )
            if proc.returncode in (0, 1):
                return proc.stdout
            # Fall through to grep on non-zero return (>1 = error)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: grep -rn
        grep_cmd = [
            "grep",
            "-rn",
            "--include",
            glob_expr,
            query,
            corpus_path,
        ]
        try:
            proc = subprocess.run(
                grep_cmd,
                capture_output=True,
                text=True,
                timeout=config.grep_timeout_ms / 1000,
            )
            if proc.returncode in (0, 1):
                return proc.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return ""

    @staticmethod
    def _parse_output(
        raw: str,
        config: ZeroIndexConfig,
    ) -> List[SearchResult]:
        """Parse ripgrep/grep output into ``SearchResult`` instances.

        Handles the standard format::

            /path/to/file.py:42:content here
        """
        results: List[SearchResult] = []
        # Regex: <filepath>:<lineno>:<content>
        pattern = re.compile(r"^(.+?):(\d+):(.+)$")

        for line in raw.splitlines():
            m = pattern.match(line)
            if m is None:
                continue
            file_path = m.group(1)
            line_number = int(m.group(2))
            content = m.group(3)

            # Skip if content would exceed the character budget
            if len(content) > config.max_context_chars:
                continue

            result = SearchResult(
                file_path=file_path,
                line_number=line_number,
                content=content,
                context_level=config.default_level,
            )
            results.append(result)

        return results

    @staticmethod
    def _filter_by_extension(
        results: List[SearchResult],
        config: ZeroIndexConfig,
    ) -> List[SearchResult]:
        """Remove results whose file extension is not allowed."""
        if not config.allowed_extensions:
            return results
        return [
            r
            for r in results
            if any(r.file_path.endswith(ext) for ext in config.allowed_extensions)
        ]

    @staticmethod
    def _score_and_sort(
        results: List[SearchResult],
        query: str,
    ) -> List[SearchResult]:
        """Assign relevance scores and sort by descending score.

        Heuristic scoring considers:
        - Exact phrase match bonus
        - Case-insensitive word-match density
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored: List[SearchResult] = []
        for r in results:
            content_lower = r.content.lower()
            score = 0.0

            # Exact match in content
            if query_lower in content_lower:
                score += 0.3

            # Word-level overlap density
            if query_words:
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                score += 0.7 * (overlap / len(query_words))

            scored.append(SearchResult(
                file_path=r.file_path,
                line_number=r.line_number,
                content=r.content,
                relevance_score=min(round(score, 4), 1.0),
                context_level=r.context_level,
            ))

        scored.sort(key=lambda r: r.relevance_score, reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Context retrieval
    # ------------------------------------------------------------------

    def get_context(
        self: ZeroIndexRetriever,
        result: SearchResult,
        level: Optional[ContextLevel] = None,
    ) -> str:
        """Fetch surrounding context for a search result.

        Args:
            result: The ``SearchResult`` to expand.
            level: Desired context depth.  Uses the result's own level
                when ``None``.

        Returns:
            A string containing the surrounding lines with line-number
            annotations.
        """
        ctx_level = level or result.context_level
        half_window = _CONTEXT_LINES.get(ctx_level, 10)
        start_line = max(1, result.line_number - half_window // 2)
        end_line = result.line_number + half_window // 2

        try:
            with open(result.file_path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except (OSError, IOError):
            return f"# Unable to read {result.file_path}"

        total_lines = len(lines)
        end_line = min(end_line, total_lines)

        context_parts: List[str] = []

        if ctx_level == ContextLevel.SUMMARIZATION:
            context_parts.append("# --- Context block start ---")

        for i in range(start_line - 1, end_line):
            lineno = i + 1
            marker = ">>" if lineno == result.line_number else "  "
            context_parts.append(f"{marker} {lineno}: {lines[i].rstrip()}")

        if ctx_level == ContextLevel.SUMMARIZATION:
            context_parts.append("# --- Context block end ---")

        return "\n".join(context_parts)

    # ------------------------------------------------------------------
    # Batch search
    # ------------------------------------------------------------------

    def batch_search(
        self: ZeroIndexRetriever,
        queries: List[str],
        corpus_path: str,
        config: Optional[ZeroIndexConfig] = None,
    ) -> Dict[str, List[SearchResult]]:
        """Run multiple queries against the same corpus.

        Results are deduplicated: if the same ``(file_path, line_number)``
        appears in multiple query results, only the highest-scoring entry
        is kept per query bucket.

        Args:
            queries: A list of search query strings.
            corpus_path: Root directory of the corpus.
            config: Optional configuration override.

        Returns:
            A dict mapping each query to its list of results.
        """
        cfg = config or ZeroIndexConfig()
        output: Dict[str, List[SearchResult]] = {}

        for q in queries:
            output[q] = self.search(q, corpus_path, cfg)

        # Deduplicate within each bucket
        for q in queries:
            seen: set[tuple[str, int]] = set()
            deduped: List[SearchResult] = []
            for r in output[q]:
                key = (r.file_path, r.line_number)
                if key not in seen:
                    seen.add(key)
                    deduped.append(r)
            output[q] = deduped

        return output

    # ------------------------------------------------------------------
    # Token estimation and budget fitting
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_tokens(results: List[SearchResult]) -> int:
        """Estimate the token count of a list of results.

        Uses the rough heuristic of ``len(content) / 4`` per result,
        plus 2 tokens for structural overhead.

        Returns:
            Estimated token count (integer).
        """
        total = 0
        for r in results:
            total += len(r.content) // 4 + 2
        return total

    @staticmethod
    def fit_to_budget(
        results: List[SearchResult],
        max_tokens: int,
    ) -> List[SearchResult]:
        """Trim results to fit a token budget, keeping highest relevance.

        Assumes the input list is already sorted by descending relevance.
        Results are greedily included until adding the next result would
        exceed *max_tokens*.

        Args:
            results: Search results sorted by relevance (descending).
            max_tokens: Maximum permitted token count.

        Returns:
            A prefix of the input list that fits within the budget.
        """
        fitted: List[SearchResult] = []
        running_tokens = 0

        for r in results:
            cost = len(r.content) // 4 + 2
            if running_tokens + cost > max_tokens:
                break
            fitted.append(r)
            running_tokens += cost

        return fitted

    # ------------------------------------------------------------------
    # Statistical queries
    # ------------------------------------------------------------------

    def corpus_stats(
        self: ZeroIndexRetriever,
        corpus_path: str,
        config: Optional[ZeroIndexConfig] = None,
    ) -> CorpusStats:
        """Gather statistics about the corpus.

        Args:
            corpus_path: Root directory of the corpus.
            config: Configuration whose ``allowed_extensions`` is used
                for file counting.

        Returns:
            A :class:`CorpusStats` instance.
        """
        cfg = config or ZeroIndexConfig()
        total_files = 0
        total_lines = 0

        for root, _dirs, files in os.walk(corpus_path):
            for fname in files:
                if any(fname.endswith(ext) for ext in cfg.allowed_extensions):
                    total_files += 1
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "rb") as fh:
                            total_lines += sum(1 for _ in fh)
                    except OSError:
                        continue

        avg_time = (
            sum(self._search_times) / len(self._search_times)
            if self._search_times
            else 0.0
        )

        return CorpusStats(
            total_files=total_files,
            total_lines=total_lines,
            searchable_extensions=cfg.allowed_extensions,
            avg_search_time_ms=round(avg_time, 2),
        )


@dataclass(frozen=True)
class CorpusStats:
    """Aggregate statistics for a searched corpus.

    Attributes:
        total_files: Number of searchable files found.
        total_lines: Total line count across all searchable files.
        searchable_extensions: File extensions that were included.
        avg_search_time_ms: Average search execution time in milliseconds.
    """

    total_files: int = 0
    total_lines: int = 0
    searchable_extensions: Tuple[str, ...] = field(
        default_factory=lambda: (".py", ".ts", ".tsx", ".js", ".md", ".json", ".yaml", ".toml")
    )
    avg_search_time_ms: float = 0.0
