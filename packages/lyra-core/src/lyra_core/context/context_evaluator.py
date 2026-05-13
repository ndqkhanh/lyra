"""Context optimisation evaluation, cost tracking, and trend detection.

Provides the 5-axis metric snapshot that closes the feedback loop for all
prior context-optimisation phases (1–6).

Research grounding: §11 ("Telemetry first"), Bottom Line #1–8,
alexgreensh/token-optimizer (log per-turn cache tokens, hit ratio; alert
when hit ratio drops — that's almost always a bug, not a content change).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Token pricing — Anthropic claude-sonnet-4 approximate, per 1 K tokens
# ---------------------------------------------------------------------------
_CACHE_READ_RATE = 0.000_3    # $0.30 / 1 M
_INPUT_RATE = 0.003            # $3.00 / 1 M
_OUTPUT_RATE = 0.015           # $15.00 / 1 M


# ---------------------------------------------------------------------------
# ContextMetrics — the 5-axis snapshot
# ---------------------------------------------------------------------------


@dataclass
class ContextMetrics:
    """One 5-axis evaluation snapshot."""

    cache_hit_ratio: float          # 0.0–1.0
    tokens_saved_by_compression: int
    decisions_preserved: float      # 0.0–1.0  cross-compaction recall %
    compaction_count: int
    estimated_cost_usd: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ContextMetrics":
        return cls(**d)


# ---------------------------------------------------------------------------
# ContextOptEvaluator — computes all 5 axes from raw counters
# ---------------------------------------------------------------------------


class ContextOptEvaluator:
    """Compute the 5-axis context optimisation metrics.

    All inputs are raw counters produced by the existing phase modules;
    this class just assembles them into one consistent snapshot.

    Usage::
        evaluator = ContextOptEvaluator()
        metrics = evaluator.evaluate(
            cache_hit_ratio=0.85,
            tokens_saved=1200,
            total_decisions=10,
            recalled_decisions=9,
            compaction_count=2,
            input_tokens=5000,
            output_tokens=800,
            cached_tokens=4000,
        )
    """

    def evaluate(
        self,
        *,
        cache_hit_ratio: float = 0.0,
        tokens_saved: int = 0,
        total_decisions: int = 0,
        recalled_decisions: int = 0,
        compaction_count: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
    ) -> ContextMetrics:
        """Compute all 5 axes and return a ContextMetrics snapshot."""
        decisions_preserved = (
            recalled_decisions / total_decisions if total_decisions > 0 else 1.0
        )
        non_cached = max(0, input_tokens - cached_tokens)
        cost = (
            (non_cached / 1000) * _INPUT_RATE
            + (cached_tokens / 1000) * _CACHE_READ_RATE
            + (output_tokens / 1000) * _OUTPUT_RATE
        )
        return ContextMetrics(
            cache_hit_ratio=max(0.0, min(1.0, cache_hit_ratio)),
            tokens_saved_by_compression=tokens_saved,
            decisions_preserved=max(0.0, min(1.0, decisions_preserved)),
            compaction_count=compaction_count,
            estimated_cost_usd=round(cost, 6),
        )


# ---------------------------------------------------------------------------
# SessionCostTracker — per-section cost breakdown
# ---------------------------------------------------------------------------

_SECTIONS = ("stable_prefix", "recall_memory", "repo_map", "recent_turns", "tool_outputs")


@dataclass
class SectionCost:
    """Token and cost breakdown for one named context section."""

    section: str
    tokens: int
    cost_usd: float


@dataclass
class SessionSnapshot:
    """Full per-section breakdown for one session."""

    total_tokens: int
    total_cost_usd: float
    sections: list[SectionCost]
    metrics: ContextMetrics | None = None


class SessionCostTracker:
    """Running cumulative cost with per-section breakdown.

    Sections map to the 5-layer context pipeline:
    - **stable_prefix**   — system prompt + injected essentials (cached ≈ cheap)
    - **recall_memory**   — pinned decisions + temporal facts
    - **repo_map**        — symbol map (stable between turns)
    - **recent_turns**    — last N assistant + user turns
    - **tool_outputs**    — tool messages (most volatile)

    Usage::
        tracker = SessionCostTracker()
        tracker.record_section("stable_prefix", tokens=800, is_cached=True)
        snapshot = tracker.snapshot()
    """

    def __init__(self) -> None:
        self._sections: dict[str, dict[str, float]] = {
            s: {"tokens": 0.0, "cost_usd": 0.0} for s in _SECTIONS
        }
        self._output_tokens: int = 0

    def record_section(
        self,
        section: str,
        *,
        tokens: int,
        is_cached: bool = False,
    ) -> None:
        """Accumulate *tokens* for *section* at the appropriate rate."""
        if section not in self._sections:
            return
        rate = _CACHE_READ_RATE if is_cached else _INPUT_RATE
        self._sections[section]["tokens"] += tokens
        self._sections[section]["cost_usd"] += (tokens / 1000) * rate

    def record_output(self, tokens: int) -> None:
        """Accumulate output tokens (billed at the output rate)."""
        self._output_tokens += tokens

    def snapshot(self, metrics: ContextMetrics | None = None) -> SessionSnapshot:
        """Return the current totals as a :class:`SessionSnapshot`."""
        output_cost = (self._output_tokens / 1000) * _OUTPUT_RATE
        total_cost = (
            sum(float(v["cost_usd"]) for v in self._sections.values()) + output_cost
        )
        total_tokens = (
            sum(int(v["tokens"]) for v in self._sections.values()) + self._output_tokens
        )
        sections = [
            SectionCost(
                section=s,
                tokens=int(self._sections[s]["tokens"]),
                cost_usd=float(self._sections[s]["cost_usd"]),
            )
            for s in _SECTIONS
        ]
        return SessionSnapshot(
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            sections=sections,
            metrics=metrics,
        )

    def reset(self) -> None:
        for s in _SECTIONS:
            self._sections[s] = {"tokens": 0.0, "cost_usd": 0.0}
        self._output_tokens = 0


# ---------------------------------------------------------------------------
# OptimisationTrendTracker — JSON-persisted cross-session regression detection
# ---------------------------------------------------------------------------

_REGRESSION_THRESHOLDS: dict[str, float] = {
    "cache_hit_ratio": -0.05,            # >5 pp drop
    "tokens_saved_by_compression": -100, # 100 fewer tokens saved
    "decisions_preserved": -0.05,        # >5 pp recall drop
}


@dataclass
class RegressionAlert:
    """One regressed axis detected by :class:`OptimisationTrendTracker`."""

    axis: str
    previous: float
    current: float
    delta: float


class OptimisationTrendTracker:
    """JSON-persisted per-session metrics with regression detection.

    A *regression* is defined per axis in ``_REGRESSION_THRESHOLDS``.
    Detecting regressions early (before the session ends) lets the agent
    roll back a tuning change rather than shipping degraded context handling.

    Usage::
        tracker = OptimisationTrendTracker(Path(".lyra/opt_trend.json"))
        tracker.record(metrics)
        alerts = tracker.check_regression(new_metrics)
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self._store_path = store_path
        if store_path and store_path.exists():
            self._load(store_path)

    def record(self, metrics: ContextMetrics) -> None:
        """Append *metrics* to the trend history and persist if configured."""
        self._records.append(metrics.to_dict())
        if self._store_path:
            self._save(self._store_path)

    def latest(self) -> ContextMetrics | None:
        """Return the most recently recorded metrics, or None."""
        return ContextMetrics.from_dict(self._records[-1]) if self._records else None

    def previous(self) -> ContextMetrics | None:
        """Return the second-most-recent record, or None."""
        return (
            ContextMetrics.from_dict(self._records[-2])
            if len(self._records) >= 2
            else None
        )

    def check_regression(self, current: ContextMetrics) -> list[RegressionAlert]:
        """Compare *current* to the most recent persisted record.

        Returns one :class:`RegressionAlert` per axis that regressed beyond
        its threshold.  Returns [] when there is no prior baseline.
        """
        prev = self.latest()
        if prev is None:
            return []
        alerts: list[RegressionAlert] = []
        for axis, threshold in _REGRESSION_THRESHOLDS.items():
            prev_val = float(getattr(prev, axis))
            curr_val = float(getattr(current, axis))
            delta = curr_val - prev_val
            if delta < threshold:
                alerts.append(
                    RegressionAlert(axis=axis, previous=prev_val, current=curr_val, delta=delta)
                )
        return alerts

    def all_records(self) -> list[ContextMetrics]:
        return [ContextMetrics.from_dict(d) for d in self._records]

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._records, indent=2))

    def _load(self, path: Path) -> None:
        try:
            self._records = json.loads(path.read_text())
        except (json.JSONDecodeError, TypeError):
            self._records = []


__all__ = [
    "ContextMetrics",
    "ContextOptEvaluator",
    "SectionCost",
    "SessionCostTracker",
    "SessionSnapshot",
    "RegressionAlert",
    "OptimisationTrendTracker",
]
