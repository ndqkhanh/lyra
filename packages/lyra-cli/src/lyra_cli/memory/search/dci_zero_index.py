"""DCI Zero-Index — grep/rg-based search outperforming vector search.

In agentic contexts (code, terminal output, structured data), rg often
outperforms vector search: zero embedding cost, instant updates,
line-level precision.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from enum import StrEnum


class MatchType(StrEnum):
    EXACT = "exact"
    SUBSTRING = "substring"
    CASE_INSENSITIVE = "case_insensitive"
    REGEX = "regex"


@dataclass(frozen=True)
class GrepResult:
    file_path: str
    line_number: int
    line_content: str
    match_type: MatchType
    score: float


class DCIZeroIndex:
    """grep/rg-based zero-index search for agentic contexts.

    Tier 0 retrieval — tried before BM25/vector/RRF.
    """

    def __init__(self, index_paths: list[str] | None = None) -> None:
        self._paths: list[str] = index_paths or ["."]
        self._file_cache: dict[str, list[str]] = {}
        self._has_rg = self._check_rg()

    @staticmethod
    def _check_rg() -> bool:
        try:
            subprocess.run(
                ["rg", "--version"],
                capture_output=True,
                timeout=2,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def search(
        self,
        query: str,
        limit: int = 10,
        paths: list[str] | None = None,
    ) -> list[GrepResult]:
        search_paths = paths or self._paths
        results: list[GrepResult] = []

        if self._has_rg:
            results = self._rg_search(query, search_paths, limit)
        else:
            results = self._python_search(query, search_paths, limit)

        results.sort(key=lambda r: -r.score)
        return results[:limit]

    def _rg_search(
        self, query: str, paths: list[str], _limit: int
    ) -> list[GrepResult]:
        results: list[GrepResult] = []
        try:
            proc = subprocess.run(
                [
                    "rg", "--no-heading", "--line-number",
                    "--max-count", str(_limit * 3),
                    "-e", re.escape(query),
                    *paths,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in proc.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    results.append(GrepResult(
                        file_path=parts[0],
                        line_number=int(parts[1]),
                        line_content=parts[2].strip(),
                        match_type=MatchType.EXACT if query in parts[2] else MatchType.SUBSTRING,
                        score=1.0 if query in parts[2] else 0.7,
                    ))
        except (subprocess.TimeoutExpired, OSError):
            pass
        return results

    def _python_search(
        self, query: str, paths: list[str], limit: int
    ) -> list[GrepResult]:
        results: list[GrepResult] = []
        query_lower = query.lower()

        for path in paths:
            if not os.path.isfile(path):
                continue
            if path not in self._file_cache:
                try:
                    with open(path) as f:
                        self._file_cache[path] = f.readlines()
                except (OSError, UnicodeDecodeError):
                    continue

            for i, line in enumerate(self._file_cache[path], 1):
                stripped = line.strip()
                if not stripped:
                    continue

                if query in stripped:
                    match_type = MatchType.EXACT
                    score = 1.0
                elif query_lower in stripped.lower():
                    match_type = MatchType.CASE_INSENSITIVE
                    score = 0.8
                elif re.search(re.escape(query), stripped, re.IGNORECASE):
                    match_type = MatchType.REGEX
                    score = 0.6
                else:
                    continue

                results.append(GrepResult(
                    file_path=path,
                    line_number=i,
                    line_content=stripped,
                    match_type=match_type,
                    score=score,
                ))

        return results

    def index_file(self, filepath: str) -> None:
        try:
            with open(filepath) as f:
                self._file_cache[filepath] = f.readlines()
        except (OSError, UnicodeDecodeError):
            pass

    def invalidate(self, filepath: str | None = None) -> None:
        if filepath:
            self._file_cache.pop(filepath, None)
        else:
            self._file_cache.clear()

    def stats(self) -> dict:
        return {
            "indexed_files": len(self._file_cache),
            "total_lines": sum(len(v) for v in self._file_cache.values()),
            "backend": "rg" if self._has_rg else "python",
            "search_paths": self._paths,
        }
