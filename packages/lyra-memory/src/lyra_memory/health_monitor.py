"""6-dimension memory health monitor.

Tracks staleness, contradiction, hallucination, confidence, coverage, and
freshness across the memory store. Produces a composite health score used
by the consolidation engine to prioritise compaction runs and by the
admission gate to dynamically tighten/loosen the threshold.

Dimensions:
  D1 — Staleness: age-weighted decay of stored memories
  D2 — Contradiction: rate of conflicting fact pairs
  D3 — Hallucination: proportion of memories flagged as unverified
  D4 — Confidence: mean verifier confidence across admitted memories
  D5 — Coverage: topic-space entropy (is the store diverse enough?)
  D6 — Freshness: write-rate over recent window
"""
from __future__ import annotations

import math
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class HealthConfig:
    """Tunable thresholds and windows for the 6-dimension monitor.

    Attributes:
        staleness_max_age_seconds: Age beyond which a memory is fully stale.
        contradiction_window: Number of recent memories to scan for conflicts.
        hallucination_max_age_seconds: Window for counting unverified flags.
        coverage_min_topics: Minimum distinct topics for full coverage score.
        freshness_window_seconds: Recent window for write-rate computation.
        freshness_expected_writes: Expected writes per window for score=1.0.
        composite_weights: Per-dimension weight for the composite score.
    """

    staleness_max_age_seconds: float = 86_400.0  # 24 h
    contradiction_window: int = 500
    hallucination_max_age_seconds: float = 3600.0
    coverage_min_topics: int = 10
    freshness_window_seconds: float = 600.0  # 10 min
    freshness_expected_writes: int = 5
    composite_weights: tuple[float, float, float, float, float, float] = field(
        default=(0.25, 0.20, 0.20, 0.15, 0.10, 0.10)
    )


@dataclass(frozen=True)
class HealthSnapshot:
    """Single-point-in-time health reading across all six dimensions."""

    staleness: float
    contradiction: float
    hallucination: float
    confidence: float
    coverage: float
    freshness: float
    composite: float

    @property
    def is_healthy(self) -> bool:
        return self.composite >= 0.50

    @property
    def is_critical(self) -> bool:
        return self.composite < 0.30

    def as_dict(self) -> dict:
        return {
            "staleness": round(self.staleness, 4),
            "contradiction": round(self.contradiction, 4),
            "hallucination": round(self.hallucination, 4),
            "confidence": round(self.confidence, 4),
            "coverage": round(self.coverage, 4),
            "freshness": round(self.freshness, 4),
            "composite": round(self.composite, 4),
            "healthy": self.is_healthy,
            "critical": self.is_critical,
        }


class MemoryHealthMonitor:
    """6-dimension health monitor for a memory store.

    Feeds lightweight structured probes to the store and returns a
    :class:`HealthSnapshot`. Designed to be called from the consolidation
    loop (every N minutes) and from the admission gate when the reject
    rate spikes.

    Usage::

        monitor = MemoryHealthMonitor()
        snap = monitor.probe(
            memory_records=store.recent(500),
            write_timestamps=store.write_timestamps(600),
        )
        if snap.is_critical:
            consolidation_engine.compact(urgent=True)
    """

    def __init__(self, config: HealthConfig | None = None) -> None:
        self._config = config or HealthConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def probe(
        self,
        *,
        memory_records: Sequence[dict],
        write_timestamps: Sequence[float] = (),
        now: float | None = None,
    ) -> HealthSnapshot:
        """Run all six probes and return a composite snapshot."""
        t = now if now is not None else time.monotonic()
        cfg = self._config

        d1 = self._probe_staleness(memory_records, t, cfg)
        d2 = self._probe_contradiction(memory_records, cfg)
        d3 = self._probe_hallucination(memory_records, t, cfg)
        d4 = self._probe_confidence(memory_records)
        d5 = self._probe_coverage(memory_records, cfg)
        d6 = self._probe_freshness(write_timestamps, t, cfg)

        w = cfg.composite_weights
        composite = (
            w[0] * d1 + w[1] * d2 + w[2] * d3 + w[3] * d4 + w[4] * d5 + w[5] * d6
        )
        # All dimensions are scored such that higher = healthier,
        # except staleness, contradiction, and hallucination which are
        # inverted before weighting.
        return HealthSnapshot(
            staleness=d1,
            contradiction=d2,
            hallucination=d3,
            confidence=d4,
            coverage=d5,
            freshness=d6,
            composite=round(max(0.0, min(1.0, composite)), 4),
        )

    # ------------------------------------------------------------------
    # Dimension probes
    # ------------------------------------------------------------------

    @staticmethod
    def _probe_staleness(
        records: Sequence[dict], now: float, cfg: HealthConfig
    ) -> float:
        """D1: 1.0 = all fresh, 0.0 = all fully stale."""
        if not records:
            return 0.5  # neutral — no data
        max_age = cfg.staleness_max_age_seconds
        scores: list[float] = []
        for r in records:
            created = r.get("created_at", r.get("captured_at", 0.0))
            age = max(0.0, now - float(created))
            scores.append(max(0.0, 1.0 - age / max_age))
        return sum(scores) / len(scores)

    @staticmethod
    def _probe_contradiction(
        records: Sequence[dict], cfg: HealthConfig
    ) -> float:
        """D2: 1.0 = no contradictions, 0.0 = many conflicts.

        Uses a lightweight key-fact overlap heuristic: if two memories
        share a subject key but assert opposite values, they conflict.
        """
        window = records[-cfg.contradiction_window:] if len(records) > cfg.contradiction_window else records
        if len(window) < 2:
            return 1.0

        # Gather subject-key → list of (fact, confidence) pairs.
        subjects: dict[str, list[tuple[str, float]]] = {}
        for r in window:
            subject = str(r.get("subject", r.get("key", r.get("content", ""))[:80]))
            fact = str(r.get("fact", r.get("value", r.get("content", ""))[:120]))
            conf = float(r.get("confidence", 0.5))
            subjects.setdefault(subject, []).append((fact, conf))

        conflict_count = 0
        pair_count = 0
        for facts in subjects.values():
            if len(facts) < 2:
                continue
            for i in range(len(facts)):
                for j in range(i + 1, len(facts)):
                    pair_count += 1
                    if facts[i][0] != facts[j][0]:
                        # Different facts for the same subject = conflict.
                        conflict_count += 1

        if pair_count == 0:
            return 1.0
        return max(0.0, 1.0 - conflict_count / pair_count)

    @staticmethod
    def _probe_hallucination(
        records: Sequence[dict], now: float, cfg: HealthConfig
    ) -> float:
        """D3: 1.0 = no unverified, 0.0 = all unverified."""
        window_age = cfg.hallucination_max_age_seconds
        recent = [
            r for r in records
            if now - float(r.get("created_at", r.get("captured_at", 0.0))) <= window_age
        ]
        if not recent:
            return 1.0  # no recent writes → no hallucination signal
        unverified = sum(
            1 for r in recent
            if str(r.get("verifier_status", "")).lower() in ("unverified", "flagged", "hallucination")
        )
        return max(0.0, 1.0 - unverified / len(recent))

    @staticmethod
    def _probe_confidence(records: Sequence[dict]) -> float:
        """D4: mean confidence of admitted memories."""
        if not records:
            return 0.5
        confidences = [float(r.get("confidence", 0.5)) for r in records]
        return sum(confidences) / len(confidences)

    @staticmethod
    def _probe_coverage(
        records: Sequence[dict], cfg: HealthConfig
    ) -> float:
        """D5: topic diversity score (entropy-based)."""
        if not records:
            return 0.0
        topics: Counter[str] = Counter()
        for r in records:
            topic = str(
                r.get("content_type")
                or r.get("type")
                or r.get("category")
                or "unknown"
            )
            topics[topic] += 1
        distinct = len(topics)
        ratio = min(1.0, distinct / cfg.coverage_min_topics)
        total = sum(topics.values())
        # Normalised Shannon entropy: 0.0 when single topic, 1.0 when uniform.
        max_entropy = math.log(max(distinct, 1))
        entropy = 0.0
        for count in topics.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log(p)
        entropy_norm = entropy / max_entropy if max_entropy > 0 else 0.0
        return round(0.5 * ratio + 0.5 * entropy_norm, 4)

    @staticmethod
    def _probe_freshness(
        write_timestamps: Sequence[float], now: float, cfg: HealthConfig
    ) -> float:
        """D6: write-rate in the freshness window vs expected."""
        window = cfg.freshness_window_seconds
        recent = sum(1 for ts in write_timestamps if now - ts <= window)
        return min(1.0, recent / max(cfg.freshness_expected_writes, 1))


__all__ = [
    "HealthConfig",
    "HealthSnapshot",
    "MemoryHealthMonitor",
]
