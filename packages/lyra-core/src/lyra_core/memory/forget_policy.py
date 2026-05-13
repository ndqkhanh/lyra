"""ForgetPolicy — utility-weighted eviction for T2/T3, LRU for T0/T1 (Phase M4).

Two eviction strategies, one per storage tier:

  T0/T1 (working + session):
    Pure LRU within a fragment-count capacity. The session buffer holds at
    most ``t1_capacity`` fragments; oldest-accessed are evicted first.
    T0 (working memory) is never explicitly managed here — compaction handles
    it at the context layer.

  T2/T3 (project + user/team):
    Utility-weighted eviction. A background ``forget_pass()`` scores every
    non-pinned fragment with:

        U(m) = w_f·access_count + w_r·recency + w_c·confidence
               + w_pin·pinned − w_age·age_days

    Fragments below ``eviction_threshold`` and not pinned are *archived*:
    their ``invalid_at`` is set to now() so they are hidden from default
    retrieval but preserved for audit (soft-delete, not hard delete).

Confidence decay:
    Every fragment's confidence is multiplied by ``confidence_decay_per_day``
    (default 0.99) for each day since last access. Applied during
    ``forget_pass()`` before utility scoring.

Pinned fragments:
    Never evicted or confidence-decayed. They are the user's explicit
    assertions about permanent facts.

Explicit user forget:
    ``soft_delete(fragment)`` sets ``invalid_at = now()`` and marks
    the fragment as user-deleted in ``structured["_deleted"] = True``.
    Audit chain is preserved.

Research grounding:
  - FluxMem utility score U(s) = w₁·c(s) + w₂·ℓ(s) + w₃·d(s) (ICML 2026)
  - MemoryBank Ebbinghaus-curve decay (arXiv:2305.10250)
  - Design proposal §8: T0/T1 LRU capacity, T2/T3 utility, confidence 0.99/day
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from .schema import Fragment, MemoryTier


# ---------------------------------------------------------------------------
# Utility weights
# ---------------------------------------------------------------------------


@dataclass
class UtilityWeights:
    w_access: float = 0.30    # access_count contribution
    w_recency: float = 0.25   # recency (exp decay) contribution
    w_confidence: float = 0.25  # confidence contribution
    w_pin: float = 10.0       # large bonus for pinned (effectively never evicted)
    w_age: float = 0.20       # penalty for age in days


DEFAULT_UTILITY_WEIGHTS = UtilityWeights()

# Recency half-life for utility scoring (30 days)
_UTILITY_TAU_DAYS = 30.0


# ---------------------------------------------------------------------------
# ForgetReport
# ---------------------------------------------------------------------------


@dataclass
class ForgetReport:
    """Summary of one forget_pass() run."""

    archived_count: int = 0
    decayed_count: int = 0
    lru_evicted_count: int = 0
    archived_ids: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"ForgetReport(archived={self.archived_count}, "
            f"decayed={self.decayed_count}, lru_evicted={self.lru_evicted_count})"
        )


# ---------------------------------------------------------------------------
# Utility scoring
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _days_since(ts: datetime, ref: datetime | None = None) -> float:
    ref = ref or _now()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (ref - ts).total_seconds()) / 86_400.0


def _recency_score(fragment: Fragment, ref: datetime | None = None) -> float:
    ts = fragment.last_accessed_at or fragment.created_at
    days = _days_since(ts, ref)
    return math.exp(-days / _UTILITY_TAU_DAYS)


def utility_score(
    fragment: Fragment,
    weights: UtilityWeights | None = None,
    ref: datetime | None = None,
) -> float:
    """Compute the utility score for a single fragment.

    Higher score = more valuable = less likely to be evicted.
    """
    w = weights or DEFAULT_UTILITY_WEIGHTS

    access = min(1.0, fragment.access_count / 50.0)  # saturates at 50 accesses
    recency = _recency_score(fragment, ref)
    confidence = fragment.confidence
    pin = 1.0 if fragment.pinned else 0.0
    age_days = _days_since(fragment.created_at, ref)

    return (
        w.w_access * access
        + w.w_recency * recency
        + w.w_confidence * confidence
        + w.w_pin * pin
        - w.w_age * min(1.0, age_days / 365.0)
    )


# ---------------------------------------------------------------------------
# ForgetPolicy
# ---------------------------------------------------------------------------


_T1_TIERS = {MemoryTier.T1_SESSION}
_T2T3_TIERS = {
    MemoryTier.T2_SEMANTIC,
    MemoryTier.T2_PROCEDURAL,
    MemoryTier.T3_USER,
    MemoryTier.T3_TEAM,
}


class ForgetPolicy:
    """Manages memory lifecycle for all non-working tiers.

    Parameters
    ----------
    t1_capacity:
        Maximum number of T1_SESSION fragments to keep active.
        Excess (oldest-accessed) are evicted via LRU.
    eviction_threshold:
        Utility score below which a T2/T3 fragment is archived.
    confidence_decay_per_day:
        Multiplicative daily decay applied to non-pinned confidence.
        Default 0.99 (≈ 50% after 69 days without access).
    weights:
        Utility scoring weights for T2/T3 eviction.
    now_fn:
        Injectable clock for deterministic tests.
    """

    def __init__(
        self,
        t1_capacity: int = 32,
        eviction_threshold: float = 0.15,
        confidence_decay_per_day: float = 0.99,
        weights: UtilityWeights | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._t1_capacity = t1_capacity
        self._eviction_threshold = eviction_threshold
        self._decay_per_day = confidence_decay_per_day
        self._weights = weights or DEFAULT_UTILITY_WEIGHTS
        self._now = now_fn or _now

    def forget_pass(self, fragments: list[Fragment]) -> ForgetReport:
        """Run one eviction pass over all fragments.

        Steps:
          1. Apply confidence decay to non-pinned T2/T3 fragments.
          2. Archive T2/T3 fragments below eviction_threshold.
          3. LRU-evict excess T1 fragments over capacity.
        """
        report = ForgetReport()
        ref = self._now()

        # ── Step 1: Confidence decay ────────────────────────────────────────
        for f in fragments:
            if f.tier not in _T2T3_TIERS:
                continue
            if f.pinned or not f.is_valid:
                continue
            days = _days_since(f.last_accessed_at or f.created_at, ref)
            if days > 0:
                factor = self._decay_per_day ** days
                f.confidence = max(0.0, f.confidence * factor)
                report.decayed_count += 1

        # ── Step 2: Utility-weighted archive for T2/T3 ─────────────────────
        for f in fragments:
            if f.tier not in _T2T3_TIERS:
                continue
            if f.pinned or not f.is_valid:
                continue
            u = utility_score(f, self._weights, ref)
            if u < self._eviction_threshold:
                self._archive(f, ref)
                report.archived_count += 1
                report.archived_ids.append(f.id)

        # ── Step 3: LRU eviction for T1 ────────────────────────────────────
        t1_active = [f for f in fragments if f.tier in _T1_TIERS and f.is_valid]
        if len(t1_active) > self._t1_capacity:
            # Sort by last_accessed_at ascending (oldest first)
            t1_active.sort(
                key=lambda f: (f.last_accessed_at or f.created_at)
            )
            excess = len(t1_active) - self._t1_capacity
            for f in t1_active[:excess]:
                self._archive(f, ref)
                report.lru_evicted_count += 1

        return report

    def soft_delete(self, fragment: Fragment) -> None:
        """User-explicit forget: archive with deletion marker.

        The fragment is hidden from default retrieval but the audit trail
        is preserved for historical queries.
        """
        fragment.structured["_deleted"] = True
        self._archive(fragment, self._now())

    def _archive(self, fragment: Fragment, at: datetime) -> None:
        """Set invalid_at to archive (soft-delete) a fragment."""
        fragment.invalid_at = at


__all__ = [
    "DEFAULT_UTILITY_WEIGHTS",
    "ForgetPolicy",
    "ForgetReport",
    "UtilityWeights",
    "utility_score",
]
