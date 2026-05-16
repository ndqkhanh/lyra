"""
RRF (Reciprocal Rank Fusion) hybrid search implementation.

Combines BM25 (keyword) and vector (semantic) search without weight tuning.
"""

from typing import List, Tuple, Callable, TypeVar, Generic
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class SearchResult(Generic[T]):
    """Search result with RRF score."""

    item: T
    rrf_score: float
    bm25_rank: int = -1
    vector_rank: int = -1


def rrf_merge(
    bm25_results: List[Tuple[T, float]],
    vector_results: List[Tuple[T, float]],
    get_id: Callable[[T], str],
    k: int = 60,
) -> List[SearchResult[T]]:
    """
    Merge BM25 and vector search results using RRF.

    Args:
        bm25_results: List of (item, score) from BM25 search
        vector_results: List of (item, score) from vector search
        get_id: Function to extract unique ID from item
        k: RRF constant (default: 60, standard value)

    Returns:
        List of SearchResult with RRF scores, sorted by score descending
    """
    # Build RRF score map
    score_map = {}

    # Process BM25 results
    for rank, (item, _score) in enumerate(bm25_results):
        item_id = get_id(item)
        rrf_score = 1.0 / (k + rank + 1)

        if item_id not in score_map:
            score_map[item_id] = {
                "item": item,
                "rrf_score": 0.0,
                "bm25_rank": -1,
                "vector_rank": -1,
            }

        score_map[item_id]["rrf_score"] += rrf_score
        score_map[item_id]["bm25_rank"] = rank

    # Process vector results
    for rank, (item, _score) in enumerate(vector_results):
        item_id = get_id(item)
        rrf_score = 1.0 / (k + rank + 1)

        if item_id not in score_map:
            score_map[item_id] = {
                "item": item,
                "rrf_score": 0.0,
                "bm25_rank": -1,
                "vector_rank": -1,
            }

        score_map[item_id]["rrf_score"] += rrf_score
        score_map[item_id]["vector_rank"] = rank

    # Convert to SearchResult objects
    results = [
        SearchResult(
            item=data["item"],
            rrf_score=data["rrf_score"],
            bm25_rank=data["bm25_rank"],
            vector_rank=data["vector_rank"],
        )
        for data in score_map.values()
    ]

    # Sort by RRF score descending
    results.sort(key=lambda x: x.rrf_score, reverse=True)

    logger.info(
        f"RRF merged {len(bm25_results)} BM25 + {len(vector_results)} vector "
        f"results into {len(results)} unique results"
    )

    return results


def hybrid_search(
    query: str,
    query_embedding: List[float],
    bm25_search_fn: Callable[[str, int], List[Tuple[T, float]]],
    vector_search_fn: Callable[[List[float], int], List[Tuple[T, float]]],
    get_id: Callable[[T], str],
    limit: int = 10,
    k: int = 60,
) -> List[SearchResult[T]]:
    """
    Perform hybrid search with 3-tier fallback strategy.

    Tier 1: BM25 + Vector + RRF (preferred)
    Tier 2: BM25 only (vector failed)
    Tier 3: Empty results (both failed)

    Args:
        query: Text query for BM25
        query_embedding: Vector for semantic search
        bm25_search_fn: Function to perform BM25 search
        vector_search_fn: Function to perform vector search
        get_id: Function to extract unique ID from item
        limit: Maximum results to return
        k: RRF constant

    Returns:
        List of SearchResult with RRF scores
    """
    bm25_results = []
    vector_results = []

    # Tier 1: Try hybrid search
    try:
        bm25_results = bm25_search_fn(query, limit * 2)  # Fetch more for RRF
        logger.debug(f"BM25 search returned {len(bm25_results)} results")
    except Exception as e:
        logger.warning(f"BM25 search failed: {e}")

    try:
        vector_results = vector_search_fn(query_embedding, limit * 2)
        logger.debug(f"Vector search returned {len(vector_results)} results")
    except Exception as e:
        logger.warning(f"Vector search failed: {e}")

    # Tier 2: Fallback to BM25 only if vector failed
    if bm25_results and not vector_results:
        logger.info("Using BM25-only results (vector search failed)")
        return [
            SearchResult(
                item=item,
                rrf_score=score,
                bm25_rank=rank,
                vector_rank=-1,
            )
            for rank, (item, score) in enumerate(bm25_results[:limit])
        ]

    # Tier 3: Empty results if both failed
    if not bm25_results and not vector_results:
        logger.warning("Both BM25 and vector search failed")
        return []

    # Tier 1: Merge with RRF
    results = rrf_merge(bm25_results, vector_results, get_id, k)

    return results[:limit]
