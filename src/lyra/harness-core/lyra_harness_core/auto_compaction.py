"""Auto-Compaction with Quality Verification — P2-B7 (HIGH, MEDIUM).

Monitors context fill level, triggers compaction when >80% full,
selects the best strategy via a rule-based "slime-mold" decider,
and verifies quality with configurable spot-checks.

See: plan-phase5-master-plan.md §2.3, plan-phase2-memory.md §4.3
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Compaction Strategy
# ---------------------------------------------------------------------------


class CompactionStrategy(Enum):
    """Available compaction strategies."""

    SUMMARIZE = "summarize"        # Condense old messages into summaries
    OFFLOAD = "offload"            # Move content to external storage
    PRUNE = "prune"                # Remove low-value content entirely
    HIERARCHICAL = "hierarchical"  # Build summary tree, keep recent verbatim


# ---------------------------------------------------------------------------
# Fill Monitoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FillStatus:
    """Snapshot of current context fill level."""

    current_tokens: int
    max_tokens: int
    fill_ratio: float
    is_critical: bool  # True when fill_ratio >= threshold

    @classmethod
    def measure(cls, current_tokens: int, max_tokens: int, *, threshold: float = 0.8) -> FillStatus:
        ratio = current_tokens / max_tokens if max_tokens > 0 else 0.0
        return cls(
            current_tokens=current_tokens,
            max_tokens=max_tokens,
            fill_ratio=ratio,
            is_critical=ratio >= threshold,
        )


# ---------------------------------------------------------------------------
# Compaction Candidate
# ---------------------------------------------------------------------------


@dataclass
class CompactionCandidate:
    """A content segment considered for compaction."""

    segment_id: str
    content: str
    token_count: int
    age: float  # higher = older (e.g. insertion timestamp)
    priority: float = 0.5  # 0-1, 1 = most important to keep


# ---------------------------------------------------------------------------
# Compaction Decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactionDecision:
    """Result of the slime-mold decider."""

    strategy: CompactionStrategy
    candidates: list[CompactionCandidate] = field(default_factory=list)
    target_token_reduction: int = 0
    reason: str = ""


# ---------------------------------------------------------------------------
# Quality Verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QualitySpotCheck:
    """Result of a single spot-check on compacted content."""

    segment_id: str
    original_hash: str
    compacted_hash: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class CompactionVerification:
    """Aggregate quality verification across spot-checks."""

    spot_checks: list[QualitySpotCheck]
    total_checks: int
    passed_checks: int
    sample_rate: float  # e.g. 0.05 for 5%

    @property
    def all_passed(self) -> bool:
        return self.passed_checks == self.total_checks

    @property
    def pass_rate(self) -> float:
        return self.passed_checks / self.total_checks if self.total_checks else 1.0


# ---------------------------------------------------------------------------
# Compaction Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactionResult:
    """Complete result of an auto-compaction run."""

    strategy: CompactionStrategy
    tokens_before: int
    tokens_after: int
    segments_removed: int
    token_reduction: int
    verification: CompactionVerification | None
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Auto-Compactor
# ---------------------------------------------------------------------------


@dataclass
class AutoCompactor:
    """Monitors context fill and triggers compaction with quality verification.

    Usage::

        compactor = AutoCompactor(max_tokens=100_000)

        status = compactor.check_fill(current_tokens=85_000)
        if status.is_critical:
            candidates = [
                CompactionCandidate("s1", "...", 500, age=10.0, priority=0.2),
                CompactionCandidate("s2", "...", 300, age=2.0, priority=0.8),
            ]
            decision = compactor.select_strategy(candidates, status)
            # Compact based on decision.strategy...
    """

    max_tokens: int
    fill_threshold: float = 0.8
    spot_check_rate: float = 0.05
    min_spot_checks: int = 3

    # --- Fill Monitoring ------------------------------------------------------

    def check_fill(self, current_tokens: int) -> FillStatus:
        """Measure current fill level."""
        return FillStatus.measure(current_tokens, self.max_tokens, threshold=self.fill_threshold)

    def should_compact(self, current_tokens: int) -> bool:
        """Return True if compaction should be triggered."""
        return self.check_fill(current_tokens).is_critical

    # --- Strategy Selection ---------------------------------------------------

    def select_strategy(
        self,
        candidates: list[CompactionCandidate],
        fill_status: FillStatus,
        *,
        strategy_hint: CompactionStrategy | None = None,
    ) -> CompactionDecision:
        """Slime-mold decider: select the best compaction strategy.

        Rules:
        - fill >= 95% → PRUNE (aggressive removal of low-priority)
        - fill >= 90% → OFFLOAD (move large segments to external storage)
        - fill >= 80% → SUMMARIZE (condense old content)
        - HIERARCHICAL only when explicitly hinted
        """
        if strategy_hint is not None:
            strategy = strategy_hint
        elif fill_status.fill_ratio >= 0.95:
            strategy = CompactionStrategy.PRUNE
        elif fill_status.fill_ratio >= 0.90:
            strategy = CompactionStrategy.OFFLOAD
        else:
            strategy = CompactionStrategy.SUMMARIZE

        excess = fill_status.current_tokens - int(self.max_tokens * self.fill_threshold)
        target = max(excess, 1)

        return CompactionDecision(
            strategy=strategy,
            candidates=list(candidates),
            target_token_reduction=target,
            reason=f"fill={fill_status.fill_ratio:.1%}, strategy={strategy.value}",
        )

    # --- Quality Verification -------------------------------------------------

    def verify(
        self,
        original_segments: dict[str, str],
        compacted_segments: dict[str, str],
    ) -> CompactionVerification:
        """Spot-check compacted content quality.

        Samples ``spot_check_rate`` (default 5%) of segments and verifies
        key information is preserved using keyword-overlap heuristics.
        """
        if not original_segments:
            return CompactionVerification([], 0, 0, self.spot_check_rate)

        common_ids = sorted(set(original_segments) & set(compacted_segments))
        if not common_ids:
            return CompactionVerification([], 0, 0, self.spot_check_rate)

        sample_size = max(self.min_spot_checks, int(len(common_ids) * self.spot_check_rate))
        sample_size = min(sample_size, len(common_ids))
        sampled = common_ids[:sample_size]

        checks: list[QualitySpotCheck] = []
        for sid in sampled:
            orig = original_segments[sid]
            compacted = compacted_segments.get(sid, "")
            passed = self._check_segment(orig, compacted)
            checks.append(
                QualitySpotCheck(
                    segment_id=sid,
                    original_hash=hashlib.sha256(orig.encode()).hexdigest()[:12],
                    compacted_hash=hashlib.sha256(compacted.encode()).hexdigest()[:12],
                    passed=passed,
                    note="key terms preserved" if passed else "information loss detected",
                )
            )

        return CompactionVerification(
            spot_checks=checks,
            total_checks=len(checks),
            passed_checks=sum(1 for c in checks if c.passed),
            sample_rate=self.spot_check_rate,
        )

    @staticmethod
    def _check_segment(original: str, compacted: str) -> bool:
        """Check whether compacted text preserves key information.

        Uses keyword overlap: at least 50% of significant terms (>=4 chars,
        alphabetic) in the original must appear in the compacted version.
        """
        if not original.strip():
            return True

        key_terms = set(re.findall(r"\b[a-zA-Z]{4,}\b", original.lower()))
        if not key_terms:
            return len(compacted) > 0

        compacted_lower = compacted.lower()
        preserved = sum(1 for t in key_terms if t in compacted_lower)
        return preserved / len(key_terms) >= 0.5

    # --- Convenience ----------------------------------------------------------

    def build_result(
        self,
        strategy: CompactionStrategy,
        tokens_before: int,
        tokens_after: int,
        segments_removed: int,
        original_segments: dict[str, str],
        compacted_segments: dict[str, str],
    ) -> CompactionResult:
        """Build a full CompactionResult with timing and verification."""
        t0 = time.perf_counter()
        verification = self.verify(original_segments, compacted_segments)
        elapsed = (time.perf_counter() - t0) * 1000

        return CompactionResult(
            strategy=strategy,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            segments_removed=segments_removed,
            token_reduction=tokens_before - tokens_after,
            verification=verification,
            elapsed_ms=round(elapsed, 2),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def compute_fill_ratio(current: int, maximum: int) -> float:
    """Compute context fill ratio (0.0–1.0)."""
    return current / maximum if maximum > 0 else 0.0


__all__ = [
    "AutoCompactor",
    "CompactionCandidate",
    "CompactionDecision",
    "CompactionResult",
    "CompactionStrategy",
    "CompactionVerification",
    "FillStatus",
    "QualitySpotCheck",
    "compute_fill_ratio",
]
