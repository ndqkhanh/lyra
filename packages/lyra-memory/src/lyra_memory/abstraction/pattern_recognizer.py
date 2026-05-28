"""Cross-episode pattern recognition for memory abstraction.

Detects recurring patterns across memory episodes to trigger
concept abstraction and generalization.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CrossEpisodePattern:
    pattern_id: str
    description: str
    episode_ids: list[str]
    occurrence_count: int
    first_seen: float
    last_seen: float
    confidence: float


class PatternRecognizer:
    """Detects recurring patterns across multiple memory episodes.

    When the same pattern appears across enough episodes with sufficient
    confidence, it triggers concept abstraction in the ConceptAbstractor.
    """

    def __init__(self, min_occurrences: int = 3, min_confidence: float = 0.6) -> None:
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence
        self._patterns: dict[str, CrossEpisodePattern] = {}
        self._episode_signatures: dict[str, list[str]] = {}

    def observe(self, episode_id: str, signature: str) -> CrossEpisodePattern | None:
        pattern_id = hashlib.sha256(signature.encode()).hexdigest()[:12]

        if pattern_id in self._patterns:
            existing = self._patterns[pattern_id]
            updated = CrossEpisodePattern(
                pattern_id=pattern_id,
                description=signature,
                episode_ids=list(set(existing.episode_ids + [episode_id])),
                occurrence_count=existing.occurrence_count + 1,
                first_seen=existing.first_seen,
                last_seen=time.time(),
                confidence=min(1.0, existing.confidence + 0.15),
            )
        else:
            updated = CrossEpisodePattern(
                pattern_id=pattern_id,
                description=signature,
                episode_ids=[episode_id],
                occurrence_count=1,
                first_seen=time.time(),
                last_seen=time.time(),
                confidence=0.3,
            )

        self._patterns[pattern_id] = updated
        self._episode_signatures.setdefault(episode_id, []).append(pattern_id)

        if self._is_significant(updated):
            return updated
        return None

    def get_significant(self) -> list[CrossEpisodePattern]:
        return [p for p in self._patterns.values() if self._is_significant(p)]

    def get_for_episode(self, episode_id: str) -> list[CrossEpisodePattern]:
        pattern_ids = self._episode_signatures.get(episode_id, [])
        return [self._patterns[pid] for pid in pattern_ids if pid in self._patterns]

    def _is_significant(self, pattern: CrossEpisodePattern) -> bool:
        return (
            pattern.occurrence_count >= self.min_occurrences
            and pattern.confidence >= self.min_confidence
        )

    def stats(self) -> dict:
        significant = self.get_significant()
        return {
            "total_patterns": len(self._patterns),
            "significant_patterns": len(significant),
            "episodes_analyzed": len(self._episode_signatures),
        }
