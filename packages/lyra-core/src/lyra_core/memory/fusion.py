"""Reciprocal Rank Fusion (RRF) — distribution-invariant rank merge.

Reciprocal Rank Fusion is the cheapest way to merge rankings from
different scorers without normalising score distributions: for every
ranking, contribute ``1 / (k + rank)`` to the item's RRF score; sum
across rankings; sort descending. The constant ``k`` (default 60, per
Cormack et al. 2009) damps the tail so a #1-on-one-list-only-or-#100
spread still ranks the unique-#1.

Why this matters for Lyra: ``MemoryToolset.recall(scope="any")`` calls
three independent substores (auto, procedural, reasoning bank). Their
score distributions are **not** comparable — Jaccard overlap (auto)
ranges 0–1, FTS5 BM25 (procedural) is unbounded, MMR with diversity
(lessons) sits somewhere else. RRF lets us merge them without picking
arbitrary normalisation constants. Idea lifted from agentmemory's
hybrid retrieval layer.

Pure function. No state. No side effects. The function returns RRF
scores plus the merged-name order so callers can either re-look-up
records or pass through their own ``RecallResult`` objects.
"""
from __future__ import annotations

from typing import Iterable, Sequence


def rrf(
    rankings: Sequence[Sequence[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Merge a list of rankings into one descending-sorted list.

    Each ``rankings[i]`` is a list of ids in best-first order. The same
    id may appear in multiple rankings — its RRF score is the sum of
    its per-list contributions. Items appearing in no ranking are
    dropped.

    ``k`` is the RRF constant. The Cormack et al. default is 60; the
    smaller ``k`` is, the more aggressively a #1 dominates a #2.
    """
    if k <= 0:
        raise ValueError("rrf: k must be positive (default 60)")
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            if not item_id:
                continue
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    # Sort by -score, then alphabetically for a stable tie-break.
    return sorted(scores.items(), key=lambda row: (-row[1], row[0]))


def rrf_topk(
    rankings: Sequence[Sequence[str]],
    *,
    top_k: int,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Convenience wrapper: full RRF then truncate."""
    return rrf(rankings, k=k)[:top_k]


__all__ = ["rrf", "rrf_topk"]
