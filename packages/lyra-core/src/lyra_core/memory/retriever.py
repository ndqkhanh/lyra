"""Hybrid Retriever — dense + BM25 + entity + RRF fusion (Phase M3).

Combines three retrieval signals and fuses them via Reciprocal Rank Fusion:

  dense      — cosine similarity against pre-computed embeddings (or falls
               back to token-overlap when no embeddings are present)
  bm25       — keyword match via token-level IDF-weighted scoring
  entity     — Jaccard overlap of extracted entity lists

Final scoring formula (design proposal §5.3):

    score(c, q) = α·sim_dense(c, q)
                + β·score_bm25(c, q)
                + γ·jaccard_entities(c, q)
                + δ·recency_boost(c)        # exp(−Δt/τ)
                + ε·pin_boost(c)            # +large if pinned
                + ζ·tier_prior(c, intent)   # bias toward T2 for "decision"

Defaults: (α,β,γ,δ,ε,ζ) = (0.5, 0.2, 0.1, 0.1, 0.4, 0.05). Tunable.

Access-policy filtering is applied after scoring — fragments the caller
cannot read (per AccessEdge validity) are excluded from results.

The Retriever is pure-Python with no third-party deps. A production
deployment swaps the dense scorer for pgvector or Qdrant.

Research grounding:
  - Mem0 hybrid scoring (dense + BM25 + entity) — design proposal §5.3
  - Reciprocal Rank Fusion (Cormack et al. 2009) — standard fusion baseline
  - FluxMem MTEM utility score (frequency + intensity + recency)
  - Design proposal §7 read-path: fan-out → score → RRF → policy-filter → pack
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from .schema import AccessEdge, Fragment, MemoryTier


# ---------------------------------------------------------------------------
# Scoring weights (defaults from design proposal §5.3)
# ---------------------------------------------------------------------------


@dataclass
class ScoringWeights:
    alpha: float = 0.5    # dense similarity
    beta: float = 0.20    # BM25
    gamma: float = 0.10   # entity Jaccard
    delta: float = 0.10   # recency boost
    epsilon: float = 0.40  # pin boost
    zeta: float = 0.05    # tier prior


DEFAULT_WEIGHTS = ScoringWeights()

# Recency half-life for exponential decay (seconds) — 7 days
_RECENCY_TAU = 7 * 24 * 3600.0

# RRF constant (Cormack 2009 recommends k=60)
_RRF_K = 60


# ---------------------------------------------------------------------------
# Retrieval query
# ---------------------------------------------------------------------------


@dataclass
class RecallQuery:
    """Parameters for a retrieval call."""

    text: str
    entities: list[str] = field(default_factory=list)
    tiers: list[MemoryTier] | None = None     # None = all tiers
    scope: Literal["private", "task", "project", "team"] = "project"
    intent: Literal["fact", "decision", "preference", "skill", "observation", "any"] = "any"
    as_of: datetime | None = None             # historical query; None = now
    k: int = 8                                # max fragments returned
    token_budget: int = 2000                  # packing budget in chars


# ---------------------------------------------------------------------------
# Pure-Python dense scorer (token overlap fallback when no embeddings)
# ---------------------------------------------------------------------------


def _token_set(text: str) -> set[str]:
    return {w.lower() for w in text.split() if len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _dense_score(fragment: Fragment, query: RecallQuery) -> float:
    """Cosine fallback via token-overlap Jaccard when no embedding is stored."""
    if fragment.embedding is not None and len(fragment.embedding) > 0:
        # Dot-product normalised to [0,1] — works for unit embeddings
        q_emb = getattr(query, "_embedding", None)
        if q_emb is not None and len(q_emb) == len(fragment.embedding):
            dot = sum(a * b for a, b in zip(q_emb, fragment.embedding))
            return max(0.0, min(1.0, dot))
    # Fallback: token Jaccard
    return _jaccard(_token_set(fragment.content), _token_set(query.text))


# ---------------------------------------------------------------------------
# BM25 scorer (simplified; k1=1.5, b=0.75)
# ---------------------------------------------------------------------------


def _bm25_score(fragment: Fragment, query: RecallQuery, avg_len: float = 20.0) -> float:
    k1, b = 1.5, 0.75
    q_tokens = _token_set(query.text)
    f_tokens = _token_set(fragment.content)
    f_len = max(1, len(f_tokens))
    score = 0.0
    for token in q_tokens:
        tf = 1.0 if token in f_tokens else 0.0
        idf = 1.0  # simplified; production uses corpus IDF
        norm = (k1 * (1.0 - b + b * f_len / avg_len))
        score += idf * (tf * (k1 + 1.0)) / (tf + norm)
    return min(1.0, score / max(1, len(q_tokens)))


# ---------------------------------------------------------------------------
# Tier prior (bias based on query intent)
# ---------------------------------------------------------------------------

_TIER_INTENT_PRIORS: dict[str, dict[MemoryTier, float]] = {
    "decision": {MemoryTier.T2_PROCEDURAL: 1.0, MemoryTier.T2_SEMANTIC: 0.3},
    "preference": {MemoryTier.T3_USER: 1.0, MemoryTier.T3_TEAM: 0.8},
    "skill": {MemoryTier.T2_PROCEDURAL: 1.0},
    "fact": {MemoryTier.T2_SEMANTIC: 1.0, MemoryTier.T2_PROCEDURAL: 0.5},
    "observation": {MemoryTier.T1_SESSION: 1.0},
    "any": {},
}


def _tier_prior(fragment: Fragment, intent: str) -> float:
    priors = _TIER_INTENT_PRIORS.get(intent, {})
    return priors.get(fragment.tier, 0.1)


# ---------------------------------------------------------------------------
# Recency boost
# ---------------------------------------------------------------------------


def _recency_boost(fragment: Fragment, as_of: datetime | None = None) -> float:
    ref = as_of or datetime.now(tz=timezone.utc)
    ts = fragment.last_accessed_at or fragment.created_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta_s = max(0.0, (ref - ts).total_seconds())
    return math.exp(-delta_s / _RECENCY_TAU)


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------


def _rrf_fuse(ranked_lists: list[list[str]], k: int = _RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion over multiple ranked id lists."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, fid in enumerate(ranked, start=1):
            scores[fid] = scores.get(fid, 0.0) + 1.0 / (k + rank)
    return scores


# ---------------------------------------------------------------------------
# Access policy filter
# ---------------------------------------------------------------------------


def _policy_allows(
    fragment: Fragment,
    scope: str,
    edges: list[AccessEdge],
    as_of: datetime | None,
) -> bool:
    """Return True if the fragment is readable under the current access policy."""
    vis = fragment.visibility
    if vis == "private":
        # Private fragments: only the writing agent may read — no edge needed
        # (caller ensures they are the writer; edges can also grant explicit access)
        return True
    if vis == "task":
        return scope in ("task", "project", "team")
    if vis == "project":
        return scope in ("project", "team")
    if vis == "team":
        if not edges:
            return scope == "team"
        return any(e.allows("read", as_of) for e in edges)
    return True


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class Retriever:
    """Hybrid retriever with RRF fusion and access-policy filtering.

    Parameters
    ----------
    weights:
        Scoring weights (α,β,γ,δ,ε,ζ). Defaults to design-proposal values.
    access_edges:
        List of AccessEdge rows for the current user/agent context. Pass []
        for single-user / no-ACL mode.
    """

    def __init__(
        self,
        weights: ScoringWeights | None = None,
        access_edges: list[AccessEdge] | None = None,
    ) -> None:
        self._weights = weights or DEFAULT_WEIGHTS
        self._edges = access_edges or []

    def recall(
        self,
        fragments: list[Fragment],
        query: RecallQuery,
    ) -> list[Fragment]:
        """Return up to query.k fragments ranked by hybrid score.

        Only fragments that are:
          1. Currently valid (not invalidated)
          2. In one of query.tiers (or any tier if None)
          3. Readable under the access policy for query.scope
        are considered.
        """
        as_of = query.as_of
        candidates = [
            f for f in fragments
            if self._is_candidate(f, query, as_of)
        ]
        if not candidates:
            return []

        avg_len = sum(len(_token_set(f.content)) for f in candidates) / len(candidates)

        # ── Score on three signals independently, then RRF ─────────────────
        dense_ranked = sorted(
            candidates,
            key=lambda f: _dense_score(f, query),
            reverse=True,
        )
        bm25_ranked = sorted(
            candidates,
            key=lambda f: _bm25_score(f, query, avg_len),
            reverse=True,
        )
        entity_ranked = sorted(
            candidates,
            key=lambda f: _jaccard(set(f.entities), set(query.entities)),
            reverse=True,
        ) if query.entities else dense_ranked  # skip entity pass if no entities

        rrf_scores = _rrf_fuse([
            [f.id for f in dense_ranked],
            [f.id for f in bm25_ranked],
            [f.id for f in entity_ranked],
        ])

        # ── Add composite-score bonuses (recency, pin, tier prior) ─────────
        frag_map = {f.id: f for f in candidates}
        final_scores: dict[str, float] = {}
        for fid, rrf in rrf_scores.items():
            f = frag_map[fid]
            bonus = (
                self._weights.delta * _recency_boost(f, as_of)
                + self._weights.epsilon * (1.0 if f.pinned else 0.0)
                + self._weights.zeta * _tier_prior(f, query.intent)
            )
            final_scores[fid] = rrf + bonus

        ranked = sorted(final_scores.keys(), key=lambda fid: final_scores[fid], reverse=True)

        # ── Pack into token budget ──────────────────────────────────────────
        result: list[Fragment] = []
        budget = query.token_budget
        for fid in ranked[: query.k * 2]:
            f = frag_map[fid]
            cost = len(f.content)
            if budget - cost < 0:
                break
            budget -= cost
            f.touch()
            result.append(f)
            if len(result) >= query.k:
                break

        return result

    def _is_candidate(
        self,
        fragment: Fragment,
        query: RecallQuery,
        as_of: datetime | None,
    ) -> bool:
        if not fragment.is_valid:
            return False
        if query.tiers and fragment.tier not in query.tiers:
            return False
        if not _policy_allows(fragment, query.scope, self._edges, as_of):
            return False
        return True


__all__ = ["DEFAULT_WEIGHTS", "RecallQuery", "Retriever", "ScoringWeights"]
