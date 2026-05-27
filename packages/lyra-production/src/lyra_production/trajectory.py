"""TrajectoryOptimizer — AgentDiet-style trajectory reduction for cost savings.

Removes useless, redundant, and expired content from agent trajectories.
Target: 39.9-59.7% fewer tokens, 21.1-35.9% cost reduction.
"""

from .models import TrajectorySegment


class TrajectoryOptimizer:
    """Optimizes agent trajectories by removing useless/redundant/expired content.

    Three optimization passes:
    1. Redundancy removal — deduplicate semantically similar segments
    2. Expiry pruning — remove stale/outdated observations
    3. Relevance filtering — drop low-relevance filler content
    """

    def __init__(self, redundancy_threshold: float = 0.85, relevance_threshold: float = 0.2):
        self._segments: dict[str, TrajectorySegment] = {}
        self._redundancy_threshold = redundancy_threshold
        self._relevance_threshold = relevance_threshold

    def add_segment(self, content: str, relevance_score: float = 0.5) -> TrajectorySegment:
        """Add a trajectory segment for optimization."""
        import uuid

        token_count = _estimate_tokens(content)
        segment = TrajectorySegment(
            id=str(uuid.uuid4()),
            content=content,
            token_count=token_count,
            relevance_score=max(0.0, min(1.0, relevance_score)),
        )
        self._segments[segment.id] = segment
        return segment

    def mark_redundant(self, segment_id: str) -> TrajectorySegment | None:
        segment = self._segments.get(segment_id)
        if segment is None:
            return None
        updated = TrajectorySegment(
            id=segment.id, content=segment.content, token_count=segment.token_count,
            relevance_score=segment.relevance_score, is_redundant=True,
            is_expired=segment.is_expired,
        )
        self._segments[segment_id] = updated
        return updated

    def mark_expired(self, segment_id: str) -> TrajectorySegment | None:
        segment = self._segments.get(segment_id)
        if segment is None:
            return None
        updated = TrajectorySegment(
            id=segment.id, content=segment.content, token_count=segment.token_count,
            relevance_score=segment.relevance_score, is_redundant=segment.is_redundant,
            is_expired=True,
        )
        self._segments[segment_id] = updated
        return updated

    def find_redundant_pairs(self) -> list[tuple[TrajectorySegment, TrajectorySegment]]:
        """Find pairs of segments with high semantic overlap."""
        pairs: list[tuple[TrajectorySegment, TrajectorySegment]] = []
        segs = list(self._segments.values())
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                if _jaccard_similarity(segs[i].content, segs[j].content) >= self._redundancy_threshold:
                    pairs.append((segs[i], segs[j]))
        return pairs

    def optimize(self) -> dict:
        """Run full trajectory optimization and return statistics."""
        redundant = self.find_redundant_pairs()
        for a, b in redundant:
            self.mark_redundant(b.id)

        for seg in self._segments.values():
            if seg.relevance_score < self._relevance_threshold:
                self.mark_expired(seg.id)

        kept = [s for s in self._segments.values() if not (s.is_redundant or s.is_expired)]
        removed = [s for s in self._segments.values() if s.is_redundant or s.is_expired]

        original_tokens = sum(s.token_count for s in self._segments.values())
        kept_tokens = sum(s.token_count for s in kept)
        token_savings = original_tokens - kept_tokens
        savings_pct = (token_savings / original_tokens * 100) if original_tokens > 0 else 0.0

        return {
            "original_segments": len(self._segments),
            "kept_segments": len(kept),
            "removed_segments": len(removed),
            "redundant_removed": sum(1 for s in removed if s.is_redundant),
            "expired_removed": sum(1 for s in removed if s.is_expired),
            "original_tokens": original_tokens,
            "kept_tokens": kept_tokens,
            "token_savings": token_savings,
            "savings_percent": round(savings_pct, 2),
        }

    @property
    def segment_count(self) -> int:
        return len(self._segments)


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return max(1, len(text) // 4)


def _jaccard_similarity(a: str, b: str) -> float:
    """Jaccard similarity between two text segments."""
    import re

    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
