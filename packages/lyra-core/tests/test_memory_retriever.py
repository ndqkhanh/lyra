"""Tests for memory/retriever.py (Phase M3 — Hybrid Retriever with RRF)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lyra_core.memory.retriever import (
    DEFAULT_WEIGHTS,
    RecallQuery,
    Retriever,
    _bm25_score,
    _dense_score,
    _jaccard,
    _recency_boost,
    _rrf_fuse,
    _tier_prior,
)
from lyra_core.memory.schema import (
    Fragment,
    FragmentType,
    MemoryTier,
    Provenance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prov() -> Provenance:
    return Provenance(agent_id="agent", session_id="s1")


def _fact(content: str, entities: list[str] | None = None,
          tier: MemoryTier = MemoryTier.T2_SEMANTIC,
          pinned: bool = False, confidence: float = 0.7) -> Fragment:
    return Fragment.make(
        tier=tier,
        type=FragmentType.FACT,
        content=content,
        provenance=_prov(),
        entities=entities or [],
        pinned=pinned,
        confidence=confidence,
        visibility="project",
    )


def _decision(content: str, entities: list[str] | None = None) -> Fragment:
    return Fragment.make(
        tier=MemoryTier.T2_PROCEDURAL,
        type=FragmentType.DECISION,
        content=content,
        provenance=_prov(),
        structured={"rationale": "for testing"},
        entities=entities or [],
        visibility="project",
    )


# ---------------------------------------------------------------------------
# _jaccard
# ---------------------------------------------------------------------------


def test_jaccard_identical():
    assert _jaccard({"a", "b"}, {"a", "b"}) == pytest.approx(1.0)


def test_jaccard_disjoint():
    assert _jaccard({"a"}, {"b"}) == pytest.approx(0.0)


def test_jaccard_empty():
    assert _jaccard(set(), set()) == pytest.approx(0.0)


def test_jaccard_partial():
    result = _jaccard({"a", "b", "c"}, {"b", "c", "d"})
    assert 0.0 < result < 1.0


# ---------------------------------------------------------------------------
# _dense_score
# ---------------------------------------------------------------------------


def test_dense_score_exact_match():
    f = _fact("authentication jwt token validation")
    q = RecallQuery(text="authentication jwt token validation")
    assert _dense_score(f, q) == pytest.approx(1.0)


def test_dense_score_no_overlap():
    f = _fact("database clickhouse migration")
    q = RecallQuery(text="user interface frontend react")
    assert _dense_score(f, q) == pytest.approx(0.0)


def test_dense_score_partial():
    f = _fact("auth module jwt token")
    q = RecallQuery(text="jwt authentication")
    score = _dense_score(f, q)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# _bm25_score
# ---------------------------------------------------------------------------


def test_bm25_score_relevant():
    f = _fact("authentication module uses jwt tokens for validation")
    q = RecallQuery(text="jwt authentication")
    score = _bm25_score(f, q)
    assert score > 0.0


def test_bm25_score_irrelevant():
    f = _fact("database migration clickhouse schema")
    q = RecallQuery(text="jwt authentication")
    score = _bm25_score(f, q)
    assert score == pytest.approx(0.0)


def test_bm25_score_bounded():
    f = _fact("jwt jwt jwt authentication authentication")
    q = RecallQuery(text="jwt authentication")
    assert _bm25_score(f, q) <= 1.0


# ---------------------------------------------------------------------------
# _recency_boost
# ---------------------------------------------------------------------------


def test_recency_boost_fresh_fragment():
    f = _fact("fresh fact")
    boost = _recency_boost(f)
    # created just now → boost close to 1.0
    assert boost > 0.99


def test_recency_boost_old_fragment():
    f = _fact("old fact")
    old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    f.created_at = old_time
    boost = _recency_boost(f)
    assert boost < 0.01


# ---------------------------------------------------------------------------
# _tier_prior
# ---------------------------------------------------------------------------


def test_tier_prior_decision_intent():
    f = _decision("chose Clickhouse")
    assert _tier_prior(f, "decision") == pytest.approx(1.0)


def test_tier_prior_wrong_tier():
    f = _fact("some fact", tier=MemoryTier.T1_SESSION)
    assert _tier_prior(f, "decision") == pytest.approx(0.1)


def test_tier_prior_any_intent():
    f = _fact("any fact")
    assert _tier_prior(f, "any") == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# _rrf_fuse
# ---------------------------------------------------------------------------


def test_rrf_fuse_single_list():
    ranked = [["a", "b", "c"]]
    scores = _rrf_fuse(ranked)
    assert scores["a"] > scores["b"] > scores["c"]


def test_rrf_fuse_agreement_boosts():
    # "a" appears first in both lists → much higher score
    list1 = ["a", "b", "c"]
    list2 = ["a", "c", "b"]
    scores = _rrf_fuse([list1, list2])
    assert scores["a"] > scores["b"]
    assert scores["a"] > scores["c"]


def test_rrf_fuse_empty_lists():
    scores = _rrf_fuse([])
    assert scores == {}


# ---------------------------------------------------------------------------
# Retriever — basic recall
# ---------------------------------------------------------------------------


def test_retriever_returns_relevant_fragment():
    r = Retriever()
    frags = [
        _fact("authentication module uses jwt tokens"),
        _fact("database uses clickhouse for OLAP"),
    ]
    q = RecallQuery(text="jwt authentication", k=5)
    results = r.recall(frags, q)
    assert len(results) >= 1
    assert any("jwt" in f.content.lower() or "authentication" in f.content.lower()
               for f in results)


def test_retriever_excludes_invalidated():
    r = Retriever()
    f_old = _fact("old fact about jwt")
    f_new = _fact("new fact about jwt authentication")
    f_old.invalidate()
    results = r.recall([f_old, f_new], RecallQuery(text="jwt"))
    assert all(f.is_valid for f in results)
    assert f_old not in results


def test_retriever_respects_k():
    r = Retriever()
    frags = [_fact(f"fact {i} about jwt token auth") for i in range(20)]
    results = r.recall(frags, RecallQuery(text="jwt", k=3))
    assert len(results) <= 3


def test_retriever_touches_returned_fragments():
    r = Retriever()
    f = _fact("jwt authentication token")
    r.recall([f], RecallQuery(text="jwt authentication"))
    assert f.access_count >= 1


# ---------------------------------------------------------------------------
# Retriever — tier filtering
# ---------------------------------------------------------------------------


def test_retriever_tier_filter():
    r = Retriever()
    f_semantic = _fact("jwt auth", tier=MemoryTier.T2_SEMANTIC)
    f_procedural = _decision("chose jwt")
    q = RecallQuery(text="jwt", tiers=[MemoryTier.T2_SEMANTIC], k=5)
    results = r.recall([f_semantic, f_procedural], q)
    assert all(f.tier is MemoryTier.T2_SEMANTIC for f in results)


# ---------------------------------------------------------------------------
# Retriever — entity boost
# ---------------------------------------------------------------------------


def test_retriever_entity_boost():
    r = Retriever()
    f_with_entity = _fact("auth module uses jwt", entities=["jwt", "auth"])
    f_without = _fact("database schema migration")
    q = RecallQuery(text="jwt", entities=["jwt"], k=5)
    results = r.recall([f_with_entity, f_without], q)
    # f_with_entity should rank higher
    if len(results) >= 2:
        assert results[0].id == f_with_entity.id


# ---------------------------------------------------------------------------
# Retriever — pin boost
# ---------------------------------------------------------------------------


def test_retriever_pinned_ranks_higher():
    r = Retriever()
    pinned = _fact("pinned architectural fact jwt", pinned=True)
    normal = _fact("normal jwt fact architecture")
    results = r.recall([pinned, normal], RecallQuery(text="jwt architectural", k=5))
    assert len(results) >= 2
    assert results[0].id == pinned.id


# ---------------------------------------------------------------------------
# Retriever — token budget
# ---------------------------------------------------------------------------


def test_retriever_token_budget_respected():
    r = Retriever()
    frags = [_fact("jwt " + "word " * 20) for _ in range(10)]
    q = RecallQuery(text="jwt", k=10, token_budget=100)
    results = r.recall(frags, q)
    total = sum(len(f.content) for f in results)
    assert total <= 100


# ---------------------------------------------------------------------------
# Retriever — access policy
# ---------------------------------------------------------------------------


def test_retriever_private_visible_always():
    r = Retriever()
    f = Fragment.make(
        tier=MemoryTier.T3_USER,
        type=FragmentType.PREFERENCE,
        content="prefer async await pattern",
        provenance=_prov(),
        visibility="private",
    )
    results = r.recall([f], RecallQuery(text="async", scope="private", k=5))
    assert len(results) == 1


def test_retriever_team_scope_blocks_project_only():
    r = Retriever(access_edges=[])  # no edges → team vis requires scope=team
    f_team = Fragment.make(
        tier=MemoryTier.T3_TEAM,
        type=FragmentType.FACT,
        content="team uses trunk-based development",
        provenance=_prov(),
        visibility="team",
    )
    # scope=team → should see team fragments (no edges needed for team scope)
    results = r.recall([f_team], RecallQuery(text="trunk development", scope="team", k=5))
    assert len(results) == 1


def test_retriever_intent_biases_tier():
    r = Retriever()
    f_proc = _decision("chose Clickhouse over Postgres")
    f_sem = _fact("clickhouse is a columnar database")
    q = RecallQuery(text="clickhouse", intent="decision", k=5)
    results = r.recall([f_proc, f_sem], q)
    if len(results) >= 2:
        # procedural fragment (decision tier) should rank higher with decision intent
        assert results[0].id == f_proc.id


# ---------------------------------------------------------------------------
# ScoringWeights defaults
# ---------------------------------------------------------------------------


def test_default_weights_sum_reasonable():
    w = DEFAULT_WEIGHTS
    # alpha + beta + gamma should be dominant signals
    assert w.alpha + w.beta + w.gamma >= 0.7
