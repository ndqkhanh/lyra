"""Tests for 6-dimension memory health monitor.

Covers:
  1. Empty records → neutral/floor scores
  2. Staleness: fresh = 1.0, old = decays
  3. Contradiction: no conflicts = 1.0, conflicts reduce score
  4. Hallucination: no unverified = 1.0, unverified reduce score
  5. Confidence: mean across records
  6. Coverage: zero for no records, positive for diverse topics
  7. Freshness: write-rate scoring
  8. Composite: weighted sum bounds [0, 1]
  9. is_healthy / is_critical thresholds
 10. as_dict serialisation
"""
from __future__ import annotations

import time

from lyra_memory.health_monitor import (
    HealthConfig,
    HealthSnapshot,
    MemoryHealthMonitor,
)


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------


def _make_record(
    content: str = "test",
    content_type: str = "fact",
    created_at: float | None = None,
    confidence: float = 0.8,
    verifier_status: str = "verified",
    **kwargs,
) -> dict:
    return {
        "content": content,
        "content_type": content_type,
        "created_at": created_at if created_at is not None else time.monotonic(),
        "confidence": confidence,
        "verifier_status": verifier_status,
        **kwargs,
    }


# ------------------------------------------------------------------
# D1: Staleness
# ------------------------------------------------------------------


def test_staleness_no_records_neutral() -> None:
    monitor = MemoryHealthMonitor()
    assert monitor._probe_staleness([], 0.0, HealthConfig()) == 0.5


def test_staleness_fresh_is_one() -> None:
    monitor = MemoryHealthMonitor()
    now = time.monotonic()
    records = [_make_record(created_at=now)]
    score = monitor._probe_staleness(records, now, HealthConfig())
    assert score == 1.0


def test_staleness_old_decays() -> None:
    monitor = MemoryHealthMonitor()
    cfg = HealthConfig(staleness_max_age_seconds=100.0)
    now = 200.0
    records = [_make_record(created_at=100.0)]
    score = monitor._probe_staleness(records, now, cfg)
    assert score == 0.0  # exactly at max_age


def test_staleness_half_age() -> None:
    monitor = MemoryHealthMonitor()
    cfg = HealthConfig(staleness_max_age_seconds=100.0)
    now = 150.0
    records = [_make_record(created_at=100.0)]
    score = monitor._probe_staleness(records, now, cfg)
    assert abs(score - 0.5) < 1e-9


# ------------------------------------------------------------------
# D2: Contradiction
# ------------------------------------------------------------------


def test_contradiction_empty_is_one() -> None:
    monitor = MemoryHealthMonitor()
    assert monitor._probe_contradiction([], HealthConfig()) == 1.0


def test_contradiction_no_conflicts() -> None:
    monitor = MemoryHealthMonitor()
    records = [
        _make_record(subject="a", fact="hello"),
        _make_record(subject="b", fact="world"),
    ]
    assert monitor._probe_contradiction(records, HealthConfig()) == 1.0


def test_contradiction_with_conflict() -> None:
    monitor = MemoryHealthMonitor()
    records = [
        _make_record(subject="x", fact="alpha"),
        _make_record(subject="x", fact="beta"),  # same subject, different fact
        _make_record(subject="y", fact="gamma"),
    ]
    score = monitor._probe_contradiction(records, HealthConfig())
    assert score < 1.0


def test_contradiction_same_fact_no_conflict() -> None:
    monitor = MemoryHealthMonitor()
    records = [
        _make_record(subject="x", fact="same"),
        _make_record(subject="x", fact="same"),
    ]
    assert monitor._probe_contradiction(records, HealthConfig()) == 1.0


# ------------------------------------------------------------------
# D3: Hallucination
# ------------------------------------------------------------------


def test_hallucination_no_records_is_one() -> None:
    monitor = MemoryHealthMonitor()
    assert monitor._probe_hallucination([], 0.0, HealthConfig()) == 1.0


def test_hallucination_all_verified_is_one() -> None:
    monitor = MemoryHealthMonitor()
    now = time.monotonic()
    records = [
        _make_record(verifier_status="verified", created_at=now),
        _make_record(verifier_status="verified", created_at=now),
    ]
    assert monitor._probe_hallucination(records, now, HealthConfig()) == 1.0


def test_hallucination_unverified_reduces_score() -> None:
    monitor = MemoryHealthMonitor()
    now = time.monotonic()
    records = [
        _make_record(verifier_status="verified", created_at=now),
        _make_record(verifier_status="unverified", created_at=now),
    ]
    score = monitor._probe_hallucination(records, now, HealthConfig())
    assert abs(score - 0.5) < 1e-9


def test_hallucination_old_unverified_ignored() -> None:
    monitor = MemoryHealthMonitor()
    cfg = HealthConfig(hallucination_max_age_seconds=10.0)
    now = 100.0
    records = [
        _make_record(verifier_status="unverified", created_at=10.0),  # too old
    ]
    score = monitor._probe_hallucination(records, now, cfg)
    assert score == 1.0  # no recent records → neutral


# ------------------------------------------------------------------
# D4: Confidence
# ------------------------------------------------------------------


def test_confidence_empty_is_neutral() -> None:
    monitor = MemoryHealthMonitor()
    assert monitor._probe_confidence([]) == 0.5


def test_confidence_mean() -> None:
    monitor = MemoryHealthMonitor()
    records = [
        _make_record(confidence=0.6),
        _make_record(confidence=0.8),
        _make_record(confidence=1.0),
    ]
    expected = (0.6 + 0.8 + 1.0) / 3
    assert abs(monitor._probe_confidence(records) - expected) < 1e-9


# ------------------------------------------------------------------
# D5: Coverage
# ------------------------------------------------------------------


def test_coverage_empty_is_zero() -> None:
    monitor = MemoryHealthMonitor()
    assert monitor._probe_coverage([], HealthConfig()) == 0.0


def test_coverage_single_topic() -> None:
    monitor = MemoryHealthMonitor()
    records = [_make_record(content_type="fact") for _ in range(5)]
    score = monitor._probe_coverage(records, HealthConfig(coverage_min_topics=10))
    # ratio=0.1, Shannon entropy=0 for one topic → 0.5*0.1 + 0.5*0 = 0.05
    assert abs(score - 0.05) < 1e-9


def test_coverage_diverse_topics() -> None:
    monitor = MemoryHealthMonitor()
    topics = ["fact", "skill", "conversation", "code", "reflection", "error", "goal"]
    records = [_make_record(content_type=t) for t in topics]
    score = monitor._probe_coverage(records, HealthConfig(coverage_min_topics=10))
    # 7 topics, uniform → ratio=0.7, entropy_norm=1.0 → 0.5*0.7+0.5*1.0=0.85
    assert score > 0.80


# ------------------------------------------------------------------
# D6: Freshness
# ------------------------------------------------------------------


def test_freshness_no_writes_is_zero() -> None:
    monitor = MemoryHealthMonitor()
    assert monitor._probe_freshness([], 0.0, HealthConfig()) == 0.0


def test_freshness_all_recent_is_one() -> None:
    monitor = MemoryHealthMonitor()
    cfg = HealthConfig(freshness_window_seconds=100.0, freshness_expected_writes=3)
    now = 200.0
    timestamps = [199.0, 198.0, 197.0]  # all within window
    assert monitor._probe_freshness(timestamps, now, cfg) == 1.0


def test_freshness_exceeds_expected_clamped() -> None:
    monitor = MemoryHealthMonitor()
    cfg = HealthConfig(freshness_window_seconds=100.0, freshness_expected_writes=2)
    now = 200.0
    timestamps = [199.0, 198.0, 197.0, 196.0]  # more than expected
    assert monitor._probe_freshness(timestamps, now, cfg) == 1.0


def test_freshness_old_writes_ignored() -> None:
    monitor = MemoryHealthMonitor()
    cfg = HealthConfig(freshness_window_seconds=10.0, freshness_expected_writes=5)
    now = 200.0
    timestamps = [50.0, 60.0]  # all outside window
    assert monitor._probe_freshness(timestamps, now, cfg) == 0.0


# ------------------------------------------------------------------
# Composite / integration
# ------------------------------------------------------------------


def test_probe_empty_store() -> None:
    monitor = MemoryHealthMonitor()
    snap = monitor.probe(memory_records=[], write_timestamps=[])
    assert 0.0 < snap.composite < 1.0
    assert not snap.is_critical


def test_probe_healthy_store() -> None:
    monitor = MemoryHealthMonitor()
    now = time.monotonic()
    records = [
        _make_record(
            content=f"fact-{i}",
            content_type="fact" if i % 3 else "skill",
            created_at=now - i,
            confidence=0.85,
            verifier_status="verified",
            subject=f"subj-{i}",
            fact=f"val-{i}",
        )
        for i in range(20)
    ]
    writes = [now - i for i in range(5)]
    snap = monitor.probe(memory_records=records, write_timestamps=writes, now=now)
    assert snap.is_healthy
    assert not snap.is_critical
    assert snap.composite >= 0.50


def test_probe_critical_store() -> None:
    cfg = HealthConfig(
        staleness_max_age_seconds=10.0,
        hallucination_max_age_seconds=10.0,
        freshness_window_seconds=10.0,
        freshness_expected_writes=20,
    )
    now = time.monotonic()
    # 10 records: stale (age = max), unverified (within window),
    # conflicting (same-subject diff-fact), low confidence, no writes.
    records = []
    for i in range(5):
        records.append(
            _make_record(
                content=f"stale-{i}",
                content_type="conversation",
                created_at=now - 10.0,
                confidence=0.1,
                verifier_status="unverified",
                subject=f"topic-{i}",
                fact="alpha",
            )
        )
        records.append(
            _make_record(
                content=f"stale-{i}-b",
                content_type="conversation",
                created_at=now - 10.0,
                confidence=0.1,
                verifier_status="flagged",
                subject=f"topic-{i}",
                fact="beta",  # conflicts with alpha
            )
        )
    monitor = MemoryHealthMonitor(config=cfg)
    snap = monitor.probe(
        memory_records=records, write_timestamps=[], now=now,
    )
    assert snap.is_critical
    assert snap.composite < 0.30


def test_health_snapshot_as_dict() -> None:
    snap = HealthSnapshot(
        staleness=0.9,
        contradiction=0.8,
        hallucination=0.7,
        confidence=0.6,
        coverage=0.5,
        freshness=0.4,
        composite=0.65,
    )
    d = snap.as_dict()
    assert d["staleness"] == 0.9
    assert d["healthy"] is True
    assert d["critical"] is False


def test_health_snapshot_thresholds() -> None:
    healthy = HealthSnapshot(0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.8)
    assert healthy.is_healthy
    assert not healthy.is_critical

    borderline = HealthSnapshot(0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.50)
    assert borderline.is_healthy
    assert not borderline.is_critical

    critical = HealthSnapshot(0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.25)
    assert not critical.is_healthy
    assert critical.is_critical
