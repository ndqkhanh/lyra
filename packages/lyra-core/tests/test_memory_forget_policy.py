"""Tests for memory/forget_policy.py (Phase M4 — ForgetPolicy)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lyra_core.memory.forget_policy import ForgetPolicy, utility_score
from lyra_core.memory.schema import Fragment, FragmentType, MemoryTier, Provenance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _prov() -> Provenance:
    return Provenance(agent_id="agent", session_id="s1")


def _fragment(
    tier: MemoryTier = MemoryTier.T2_SEMANTIC,
    ftype: FragmentType = FragmentType.FACT,
    content: str = "some fact",
    confidence: float = 0.7,
    pinned: bool = False,
    access_count: int = 0,
    days_old: int = 0,
) -> Fragment:
    f = Fragment.make(
        tier=tier,
        type=ftype,
        content=content,
        provenance=_prov(),
        confidence=confidence,
        pinned=pinned,
        structured={} if ftype is not FragmentType.DECISION else {"rationale": "r"},
    )
    f.access_count = access_count
    if days_old > 0:
        old = _now() - timedelta(days=days_old)
        f.created_at = old
        f.last_accessed_at = old
    return f


def _t1(content: str = "session fact", access_count: int = 0, days_old: int = 0) -> Fragment:
    return _fragment(tier=MemoryTier.T1_SESSION, content=content,
                     access_count=access_count, days_old=days_old)


# ---------------------------------------------------------------------------
# utility_score
# ---------------------------------------------------------------------------


def test_utility_score_fresh_high_confidence():
    f = _fragment(confidence=0.9, access_count=5)
    score = utility_score(f)
    assert score > 0.5


def test_utility_score_old_unaccessed():
    f = _fragment(confidence=0.7, access_count=0, days_old=365)
    score = utility_score(f)
    assert score < 0.5


def test_utility_score_pinned_very_high():
    f = _fragment(pinned=True, confidence=0.5, access_count=0, days_old=200)
    score = utility_score(f)
    # w_pin=10 dominates all other terms
    assert score > 5.0


def test_utility_score_many_accesses_boosts():
    f_hot = _fragment(access_count=50)
    f_cold = _fragment(access_count=0)
    assert utility_score(f_hot) > utility_score(f_cold)


def test_utility_score_recency_matters():
    f_fresh = _fragment(days_old=0)
    f_old = _fragment(days_old=60)
    assert utility_score(f_fresh) > utility_score(f_old)


# ---------------------------------------------------------------------------
# ForgetPolicy — confidence decay
# ---------------------------------------------------------------------------


def test_confidence_decay_applied_to_old_fragment():
    policy = ForgetPolicy(eviction_threshold=-999.0)  # disable eviction
    f = _fragment(tier=MemoryTier.T2_SEMANTIC, confidence=0.9, days_old=30)
    original = f.confidence
    policy.forget_pass([f])
    assert f.confidence < original


def test_confidence_decay_not_applied_to_pinned():
    policy = ForgetPolicy(eviction_threshold=-999.0)
    f = _fragment(tier=MemoryTier.T2_SEMANTIC, confidence=0.9, pinned=True, days_old=30)
    original = f.confidence
    policy.forget_pass([f])
    assert f.confidence == pytest.approx(original)


def test_confidence_decay_not_applied_to_t1():
    policy = ForgetPolicy(eviction_threshold=-999.0, t1_capacity=100)
    f = _t1(days_old=30)
    original = f.confidence
    policy.forget_pass([f])
    assert f.confidence == pytest.approx(original)


def test_confidence_decay_report_count():
    policy = ForgetPolicy(eviction_threshold=-999.0)
    frags = [_fragment(tier=MemoryTier.T2_SEMANTIC, days_old=10) for _ in range(5)]
    report = policy.forget_pass(frags)
    assert report.decayed_count == 5


def test_confidence_floor_at_zero():
    policy = ForgetPolicy(
        eviction_threshold=-999.0,
        confidence_decay_per_day=0.5,  # aggressive decay
    )
    f = _fragment(tier=MemoryTier.T2_SEMANTIC, confidence=0.1, days_old=100)
    policy.forget_pass([f])
    assert f.confidence >= 0.0


# ---------------------------------------------------------------------------
# ForgetPolicy — T2/T3 utility-based archive
# ---------------------------------------------------------------------------


def test_low_utility_fragment_archived():
    policy = ForgetPolicy(eviction_threshold=0.9)  # very high threshold → almost all archived
    f = _fragment(tier=MemoryTier.T2_SEMANTIC, confidence=0.1, access_count=0, days_old=300)
    report = policy.forget_pass([f])
    assert report.archived_count >= 1
    assert not f.is_valid


def test_high_utility_fragment_kept():
    policy = ForgetPolicy(eviction_threshold=0.05)
    f = _fragment(tier=MemoryTier.T2_SEMANTIC, confidence=0.9, access_count=20, days_old=1)
    policy.forget_pass([f])
    assert f.is_valid


def test_pinned_never_archived():
    policy = ForgetPolicy(eviction_threshold=0.99)  # threshold ensures all else archived
    f = _fragment(tier=MemoryTier.T2_PROCEDURAL, pinned=True, days_old=365)
    policy.forget_pass([f])
    assert f.is_valid


def test_already_invalid_skipped():
    policy = ForgetPolicy(eviction_threshold=0.0)
    f = _fragment(tier=MemoryTier.T2_SEMANTIC)
    f.invalidate()
    report = policy.forget_pass([f])
    assert report.archived_count == 0


def test_archived_ids_recorded():
    policy = ForgetPolicy(eviction_threshold=0.99)
    f = _fragment(tier=MemoryTier.T2_SEMANTIC, confidence=0.1, days_old=300)
    report = policy.forget_pass([f])
    assert f.id in report.archived_ids


# ---------------------------------------------------------------------------
# ForgetPolicy — T1 LRU eviction
# ---------------------------------------------------------------------------


def test_t1_lru_evicts_oldest():
    policy = ForgetPolicy(t1_capacity=2, eviction_threshold=-999.0)
    # Three T1 fragments: oldest accessed first
    f_old = _t1(content="old", days_old=10)
    f_mid = _t1(content="mid", days_old=5)
    f_new = _t1(content="new", days_old=1)
    report = policy.forget_pass([f_old, f_mid, f_new])
    assert report.lru_evicted_count == 1
    # Oldest should be evicted
    assert not f_old.is_valid
    assert f_mid.is_valid
    assert f_new.is_valid


def test_t1_under_capacity_no_eviction():
    policy = ForgetPolicy(t1_capacity=10, eviction_threshold=-999.0)
    frags = [_t1(f"fact {i}") for i in range(5)]
    report = policy.forget_pass(frags)
    assert report.lru_evicted_count == 0
    assert all(f.is_valid for f in frags)


def test_t1_lru_report_count():
    policy = ForgetPolicy(t1_capacity=3, eviction_threshold=-999.0)
    frags = [_t1(f"fact {i}", days_old=i) for i in range(6)]
    report = policy.forget_pass(frags)
    assert report.lru_evicted_count == 3


# ---------------------------------------------------------------------------
# ForgetPolicy — soft_delete
# ---------------------------------------------------------------------------


def test_soft_delete_archives_with_marker():
    policy = ForgetPolicy()
    f = _fragment()
    policy.soft_delete(f)
    assert not f.is_valid
    assert f.structured.get("_deleted") is True


def test_soft_delete_preserves_content():
    policy = ForgetPolicy()
    f = _fragment(content="important fact")
    policy.soft_delete(f)
    assert f.content == "important fact"


def test_soft_delete_sets_invalid_at():
    policy = ForgetPolicy()
    f = _fragment()
    policy.soft_delete(f)
    assert f.invalid_at is not None


# ---------------------------------------------------------------------------
# ForgetReport
# ---------------------------------------------------------------------------


def test_forget_report_str():
    policy = ForgetPolicy(t1_capacity=1, eviction_threshold=0.99)
    f1 = _fragment(tier=MemoryTier.T2_SEMANTIC, confidence=0.1, days_old=300)
    f2 = _t1(days_old=10)
    f3 = _t1(days_old=5)
    report = policy.forget_pass([f1, f2, f3])
    assert "archived" in str(report).lower()
