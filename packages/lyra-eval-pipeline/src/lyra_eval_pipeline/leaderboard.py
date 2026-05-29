"""Model and domain leaderboard management."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .exceptions import LeaderboardError


@dataclass(frozen=True)
class LeaderboardEntry:
    """A single entry in a leaderboard."""

    rank: int
    name: str
    score: float
    change: int = 0
    domain: str = ""
    num_evals: int = 0


@dataclass(frozen=True)
class Leaderboard:
    """A leaderboard with ranked entries."""

    entries: tuple[LeaderboardEntry, ...]
    category: str
    updated_at: float
    total_entries: int


@dataclass(frozen=True)
class HistoricalEntry:
    """Historical scores for a model/domain over time."""

    name: str
    scores: tuple[tuple[float, float], ...]  # (timestamp, score)


class LeaderboardManager:
    """Manages leaderboards for models and domains."""

    def __init__(self) -> None:
        # category -> {name -> (score, num_evals, last_change)}
        self._entries: dict[str, dict[str, tuple[float, int, int]]] = {}
        self._history: dict[str, list[tuple[float, float]]] = {}  # name -> [(timestamp, score)]

    async def update_entry(self, name: str, score: float, domain: str) -> None:
        """Update or create a leaderboard entry."""
        cat = domain if domain else "overall"

        if cat not in self._entries:
            self._entries[cat] = {}

        prev = self._entries[cat].get(name)
        if prev is not None:
            prev_score, prev_count, _ = prev
            change = int(round((score - prev_score) * 100))
            new_count = prev_count + 1
        else:
            change = 0
            new_count = 1

        self._entries[cat][name] = (score, new_count, change)

        # Record history
        if name not in self._history:
            self._history[name] = []
        self._history[name].append((time.time(), score))

    async def get_leaderboard(self, category: str = "overall", top_k: int = 10) -> Leaderboard:
        """Get the leaderboard for a category."""
        cat_entries = self._entries.get(category)
        if cat_entries is None:
            return Leaderboard(
                entries=(),
                category=category,
                updated_at=time.time(),
                total_entries=0,
            )

        # Sort by score descending
        sorted_items = sorted(cat_entries.items(), key=lambda x: x[1][0], reverse=True)

        entries_list: list[LeaderboardEntry] = []
        for i, (name, (score, num_evals, change)) in enumerate(sorted_items[:top_k]):
            entries_list.append(
                LeaderboardEntry(
                    rank=i + 1,
                    name=name,
                    score=round(score, 4),
                    change=change,
                    domain=category,
                    num_evals=num_evals,
                )
            )

        return Leaderboard(
            entries=tuple(entries_list),
            category=category,
            updated_at=time.time(),
            total_entries=len(cat_entries),
        )

    async def get_history(self, name: str) -> HistoricalEntry:
        """Get historical scores for an entry."""
        hist = self._history.get(name)
        if hist is None:
            raise LeaderboardError(f"No history found for: {name}")
        return HistoricalEntry(
            name=name,
            scores=tuple(hist),
        )

    async def compare_models(self, names: tuple[str, ...]) -> Leaderboard:
        """Compare multiple models across domains."""
        if not names:
            raise LeaderboardError("No models specified for comparison")
        if len(names) < 2:
            raise LeaderboardError("Need at least 2 models to compare")

        # Aggregate scores across all domains for the given models
        model_scores: dict[str, list[float]] = {n: [] for n in names}
        for _cat, cat_entries in self._entries.items():
            for name, (score, _, _) in cat_entries.items():
                if name in model_scores:
                    model_scores[name].append(score)

        # Compute average scores
        avg_scores: list[tuple[str, float]] = []
        for name in names:
            scores = model_scores[name]
            if not scores:
                raise LeaderboardError(f"No scores found for model: {name}")
            avg = sum(scores) / len(scores)
            avg_scores.append((name, avg))

        avg_scores.sort(key=lambda x: x[1], reverse=True)

        entries = tuple(
            LeaderboardEntry(
                rank=i + 1,
                name=name,
                score=round(score, 4),
                domain="comparison",
            )
            for i, (name, score) in enumerate(avg_scores)
        )

        return Leaderboard(
            entries=entries,
            category="comparison",
            updated_at=time.time(),
            total_entries=len(entries),
        )
