"""AGI Score Leaderboard — version tracking, standardized scoring, comparison.

Tracks Lyra's AGI progression across versions. Public API for community
comparison. Standardized AGI score across all benchmark dimensions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "LeaderboardEntry",
    "VersionComparison",
    "AGILeaderboard",
]


@dataclass
class LeaderboardEntry:
    version: str
    agi_score: float
    benchmark_scores: dict[str, float]
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VersionComparison:
    version_a: str
    version_b: str
    score_a: float
    score_b: float
    improvement: float
    regressions: list[str]
    improvements: list[str]


class AGILeaderboard:
    """Public AGI score leaderboard with version tracking."""

    def __init__(self):
        self.entries: list[LeaderboardEntry] = []

    def record(self, version: str, agi_score: float, benchmark_scores: dict[str, float]) -> LeaderboardEntry:
        entry = LeaderboardEntry(
            version=version,
            agi_score=agi_score,
            benchmark_scores=benchmark_scores,
            timestamp=time.time(),
        )
        self.entries.append(entry)
        return entry

    def compare(self, version_a: str, version_b: str) -> Optional[VersionComparison]:
        def find(v: str) -> Optional[LeaderboardEntry]:
            for e in reversed(self.entries):
                if e.version == v:
                    return e
            return None

        a = find(version_a)
        b = find(version_b)
        if not a or not b:
            return None

        regressions = []
        improvements = []
        all_benchmarks = set(a.benchmark_scores) | set(b.benchmark_scores)
        for bench in all_benchmarks:
            score_a = a.benchmark_scores.get(bench, 0)
            score_b = b.benchmark_scores.get(bench, 0)
            if score_b < score_a:
                regressions.append(bench)
            elif score_b > score_a:
                improvements.append(bench)

        return VersionComparison(
            version_a=version_a,
            version_b=version_b,
            score_a=a.agi_score,
            score_b=b.agi_score,
            improvement=b.agi_score - a.agi_score,
            regressions=regressions,
            improvements=improvements,
        )

    def get_top_versions(self, n: int = 5) -> list[LeaderboardEntry]:
        sorted_entries = sorted(self.entries, key=lambda e: e.agi_score, reverse=True)
        return sorted_entries[:n]

    def get_version_progress(self, version_prefix: str) -> list[LeaderboardEntry]:
        return [e for e in self.entries if e.version.startswith(version_prefix)]

    @property
    def stats(self) -> dict[str, Any]:
        if not self.entries:
            return {"entries": 0, "best_score": 0}
        best = max(self.entries, key=lambda e: e.agi_score)
        return {
            "total_entries": len(self.entries),
            "best_version": best.version,
            "best_score": best.agi_score,
            "versions": list(set(e.version for e in self.entries)),
        }
