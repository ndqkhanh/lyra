"""Context Prioritizer — assign disclosure priority levels to context items.

Uses a combination of query relevance (keyword overlap) and item importance
(weight) to score and rank context items into five disclosure levels:
    0 = critical
    1 = important
    2 = relevant
    3 = supplementary
    4 = archival
"""

from __future__ import annotations

from lyra_core.context.pipeline import ContextItem


class ContextPrioritizer:
    """Assigns priority levels to context items based on relevance and importance.

    Scoring formula:
        score = 0.6 * relevance + 0.4 * importance

    Where:
        relevance = fraction of query tokens that appear in the item content
        importance = item.weight / 10.0 (normalized to 0-1)

    Priority levels are assigned by score thresholds:
        >= 0.8  -> level 0 (critical)
        >= 0.6  -> level 1 (important)
        >= 0.4  -> level 2 (relevant)
        >= 0.2  -> level 3 (supplementary)
        <  0.2  -> level 4 (archival)
    """

    def prioritize(
        self,
        items: list[ContextItem],
        query: str,
    ) -> list[tuple[ContextItem, int]]:
        """Score each item and assign a disclosure priority level (0-4).

        Items are returned sorted by score descending (most relevant first).

        Args:
            items: Context items to prioritize.
            query: The query to compute relevance against.

        Returns:
            List of (item, priority_level) tuples.
        """
        scored: list[tuple[ContextItem, float]] = []
        for item in items:
            score = self._compute_score(item, query)
            scored.append((item, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [(item, self._score_to_level(score)) for item, score in scored]

    def _compute_score(self, item: ContextItem, query: str) -> float:
        """Compute a combined relevance + importance score (0-1)."""
        relevance = self._compute_relevance(item.content, query)
        importance = item.weight / 10.0  # weight 0-10 -> normalized 0-1
        return 0.6 * relevance + 0.4 * importance

    def _compute_relevance(self, content: str, query: str) -> float:
        """Compute simple keyword-overlap relevance score (0-1)."""
        query_words = set(query.lower().split())
        if not query_words:
            return 0.0
        content_words = set(content.lower().split())
        intersection = query_words & content_words
        return len(intersection) / len(query_words)

    def _score_to_level(self, score: float) -> int:
        """Map a score (0-1) to a disclosure priority level (0-4)."""
        if score >= 0.8:
            return 0  # critical
        if score >= 0.6:
            return 1  # important
        if score >= 0.4:
            return 2  # relevant
        if score >= 0.2:
            return 3  # supplementary
        return 4  # archival


__all__ = [
    "ContextPrioritizer",
]
