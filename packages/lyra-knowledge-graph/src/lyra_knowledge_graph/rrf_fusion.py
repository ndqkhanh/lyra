"""Reciprocal Rank Fusion for hybrid retrieval.

Combines keyword search results and vector similarity results using
the RRF algorithm. Provides configurable k parameter, score normalization,
and re-ranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FusionResult:
    """A single fused and re-ranked search result."""
    item_id: str
    rank: int
    score: float
    keyword_score: float = 0.0
    vector_score: float = 0.0
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "rank": self.rank,
            "score": self.score,
            "keyword_score": self.keyword_score,
            "vector_score": self.vector_score,
            "sources": list(self.sources),
            "metadata": dict(self.metadata),
        }


class RRFusion:
    """Reciprocal Rank Fusion engine.

    Combines multiple ranked result lists (e.g. keyword search, vector
    similarity) into a single fused ranking using the RRF algorithm.

    Formula: RRF score(d) = sum(1 / (k + rank_i(d))) for each result list i
    """

    def __init__(self, k: int = 60) -> None:
        """Initialize RRFusion with a k parameter (default 60)."""
        if k <= 0:
            raise ValueError("k must be positive")
        self._k = k

    # ── Fusion ─────────────────────────────────────────────────────────────

    def fuse(self, keyword_results: list[dict[str, Any]],
             vector_results: list[dict[str, Any]]) -> list[FusionResult]:
        """Fuse keyword and vector search results using RRF.

        Each result dict should have at least an 'id' field and may have
        a 'score' field. Returns re-ranked list of FusionResult.
        """
        rrf_scores: dict[str, dict[str, Any]] = {}

        # Keyword results
        for rank, result in enumerate(keyword_results):
            item_id = result.get("id", str(result))
            rrf_scores.setdefault(item_id, {
                "keyword_rank": rank + 1,
                "vector_rank": None,
                "keyword_score": result.get("score", 0.0),
                "vector_score": 0.0,
                "metadata": result.get("metadata", {}),
            })
            rrf_scores[item_id]["keyword_rank"] = rank + 1
            rrf_scores[item_id]["keyword_score"] = result.get("score", 0.0)
            rrf_scores[item_id]["metadata"] = result.get("metadata", {})

        # Vector results
        for rank, result in enumerate(vector_results):
            item_id = result.get("id", str(result))
            entry = rrf_scores.setdefault(item_id, {
                "keyword_rank": None,
                "vector_rank": rank + 1,
                "keyword_score": 0.0,
                "vector_score": result.get("score", 0.0),
                "metadata": result.get("metadata", {}),
            })
            entry["vector_rank"] = rank + 1
            entry["vector_score"] = result.get("score", 0.0)
            entry["metadata"] = result.get("metadata", {})

        # RRF score computation
        for _item_id, entry in rrf_scores.items():
            rrf_score = 0.0
            if entry["keyword_rank"] is not None:
                rrf_score += 1.0 / (self._k + entry["keyword_rank"])
            if entry["vector_rank"] is not None:
                rrf_score += 1.0 / (self._k + entry["vector_rank"])
            entry["rrf_score"] = rrf_score

        # Sort by RRF score (descending)
        sorted_items = sorted(
            rrf_scores.items(),
            key=lambda x: x[1]["rrf_score"],
            reverse=True,
        )

        # Normalize scores to [0, 1]
        max_score = max((e["rrf_score"] for _, e in sorted_items), default=1.0)
        if max_score == 0.0:
            max_score = 1.0

        results: list[FusionResult] = []
        for rank, (item_id, entry) in enumerate(sorted_items):
            results.append(FusionResult(
                item_id=item_id,
                rank=rank + 1,
                score=entry["rrf_score"] / max_score,
                keyword_score=entry["keyword_score"],
                vector_score=entry["vector_score"],
                sources=self._determine_sources(entry),
                metadata=entry["metadata"],
            ))

        return results

    # ── Multi-List Fusion ─────────────────────────────────────────────────

    def fuse_multiple(self, result_lists: list[list[dict[str, Any]]]) -> list[FusionResult]:
        """Fuse multiple (2+) ranked result lists using RRF."""
        if not result_lists:
            return []

        rrf_scores: dict[str, dict[str, Any]] = {}

        for list_idx, results in enumerate(result_lists):
            for rank, result in enumerate(results):
                item_id = result.get("id", str(result))
                if item_id not in rrf_scores:
                    rrf_scores[item_id] = {
                        "ranks": {},
                        "scores": {},
                        "metadata": result.get("metadata", {}),
                    }
                rrf_scores[item_id]["ranks"][list_idx] = rank + 1
                rrf_scores[item_id]["scores"][list_idx] = result.get("score", 0.0)

        for _item_id, entry in rrf_scores.items():
            rrf_score = 0.0
            for _list_idx, rank_val in entry["ranks"].items():
                rrf_score += 1.0 / (self._k + rank_val)
            entry["rrf_score"] = rrf_score

        sorted_items = sorted(
            rrf_scores.items(),
            key=lambda x: x[1]["rrf_score"],
            reverse=True,
        )

        max_score = max((e["rrf_score"] for _, e in sorted_items), default=1.0)
        if max_score == 0.0:
            max_score = 1.0

        results: list[FusionResult] = []
        for rank, (item_id, entry) in enumerate(sorted_items):
            kw_score = entry["scores"].get(0, 0.0)
            vec_score = entry["scores"].get(1, 0.0)
            results.append(FusionResult(
                item_id=item_id,
                rank=rank + 1,
                score=entry["rrf_score"] / max_score,
                keyword_score=kw_score,
                vector_score=vec_score,
                sources=[f"list_{i}" for i in entry["ranks"]],
                metadata=entry["metadata"],
            ))

        return results

    # ── Helpers ────────────────────────────────────────────────────────────

    def normalize_scores(self, results: list[dict[str, Any]],
                         key: str = "score") -> list[dict[str, Any]]:
        """Normalize scores in a result list to [0, 1] range."""
        if not results:
            return results
        scores = [r.get(key, 0.0) for r in results]
        min_s = min(scores)
        max_s = max(scores)
        if max_s == min_s:
            return [{**r, key: 0.5} for r in results]
        return [
            {**r, key: (r.get(key, 0.0) - min_s) / (max_s - min_s)}
            for r in results
        ]

    def rerank(self, results: list[FusionResult],
               weight_fn: Any | None = None) -> list[FusionResult]:
        """Re-rank fused results, optionally applying a weight function.

        The weight_fn should accept a FusionResult and return a float multiplier.
        """
        if weight_fn is None:
            scored = sorted(results, key=lambda r: r.score, reverse=True)
        else:
            scored = sorted(
                results,
                key=lambda r: r.score * weight_fn(r),
                reverse=True,
            )

        return [
            FusionResult(
                item_id=r.item_id,
                rank=i + 1,
                score=r.score,
                keyword_score=r.keyword_score,
                vector_score=r.vector_score,
                sources=r.sources,
                metadata=r.metadata,
            )
            for i, r in enumerate(scored)
        ]

    # ── Internal ───────────────────────────────────────────────────────────

    def _determine_sources(self, entry: dict[str, Any]) -> list[str]:
        """Determine which search methods contributed to a result."""
        sources: list[str] = []
        if entry.get("keyword_rank") is not None:
            sources.append("keyword")
        if entry.get("vector_rank") is not None:
            sources.append("vector")
        return sources

    @property
    def k(self) -> int:
        return self._k


class RRFFusion:
    """BM25+vector+RRF hybrid retrieval.

    Applies Reciprocal Rank Fusion to combine vector search and
    BM25/keyword search results.
    """

    def __init__(self, k: int = 60) -> None:
        if k <= 0:
            raise ValueError("k must be positive")
        self._fusion = RRFusion(k=k)

    @property
    def k(self) -> int:
        return self._fusion.k

    async def fuse_results(
        self,
        vector_results: list[dict[str, Any]],
        bm25_results: list[dict[str, Any]],
        k: int = 60,
    ) -> list[FusionResult]:
        """Apply Reciprocal Rank Fusion to combine vector and BM25 results."""
        if k <= 0:
            raise ValueError("k must be positive")
        temp = RRFusion(k=k)
        return temp.fuse(keyword_results=bm25_results, vector_results=vector_results)
