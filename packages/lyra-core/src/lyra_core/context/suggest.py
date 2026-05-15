"""Strategic-compaction suggestion hook (Phase CE.2, P1-5).

Lyra's automatic compaction already fires at ``autocompact_pct``. This
module adds *suggestions* — soft hints surfaced earlier so an operator
(or the agent itself, via the Compact tool) can compact *before* the
hard threshold is hit. ECC's experience says earlier compactions
produce higher-quality summaries.

Three signals drive the advice:

* **fill_ratio**         — ``tokens_used / max_tokens``.
* **tool_call_density**  — fraction of the last ``window`` messages
                           that are tool results.
* **observation_size_p95** — 95th-percentile byte length of recent
                           tool results.

The advice is *non-blocking*: it returns a dataclass; the caller
decides whether to surface it or fold it into a metric.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Callable

from .clear import _is_tool_message, _looks_already_cleared
from .compactor import _tok_estimate
from .profile import STANDARD, ContextProfile


@dataclass(frozen=True)
class CompactionSignals:
    """Snapshot of the inputs to :func:`suggest_compaction`."""

    tokens_used: int
    max_tokens: int
    tool_call_density: float  # 0..1
    observation_size_p95: int  # bytes
    recent_failure_count: int = 0

    @property
    def fill_ratio(self) -> float:
        if self.max_tokens <= 0:
            return 0.0
        return min(1.0, self.tokens_used / self.max_tokens)


URGENCY_NONE = "none"
URGENCY_SOFT = "soft"
URGENCY_HARD = "hard"


@dataclass(frozen=True)
class CompactionAdvice:
    """Output of :func:`suggest_compaction`."""

    suggested: bool
    urgency: str  # URGENCY_NONE | URGENCY_SOFT | URGENCY_HARD
    reasons: tuple[str, ...] = ()
    signals: CompactionSignals = field(
        default_factory=lambda: CompactionSignals(0, 1, 0.0, 0)
    )

    def to_metric_dict(self) -> dict[str, float | int | str]:
        """Flat dict for emission via an observability sink."""
        return {
            "context.compaction.advice.suggested": int(self.suggested),
            "context.compaction.advice.urgency": self.urgency,
            "context.compaction.advice.fill_ratio": self.signals.fill_ratio,
            "context.compaction.advice.tool_density": self.signals.tool_call_density,
            "context.compaction.advice.observation_p95_bytes": (
                self.signals.observation_size_p95
            ),
            "context.compaction.advice.reasons_count": len(self.reasons),
        }


# Soft offset from the hard threshold — fire a suggestion ~15 points
# before the autocompact actually trips.
SOFT_FILL_OFFSET = 0.15
# Above this fraction of the recent window being tool results, the
# context is tool-heavy enough that summarising pays off even without
# a full token-fill signal.
TOOL_DENSITY_TRIGGER = 0.6
# Recent tool result p95 above this multiple of reduction_cap_kb means
# the reducer hasn't been able to keep up.
OBSERVATION_P95_MULTIPLE = 2.0


def compute_signals(
    messages: list[dict],
    *,
    max_tokens: int,
    window: int = 10,
    failure_keywords: tuple[str, ...] = ("FAIL", "error:", "denied", "regression"),
) -> CompactionSignals:
    """Aggregate transcript-level signals over the last ``window`` msgs.

    The token-used number is a ``_tok_estimate`` rollup over the
    whole transcript — same heuristic the compactor uses internally,
    so the two stay aligned.
    """
    if max_tokens <= 0:
        raise ValueError(f"max_tokens must be > 0, got {max_tokens}")
    if window <= 0:
        raise ValueError(f"window must be > 0, got {window}")

    def _content_tokens(msg: dict) -> int:
        content = msg.get("content")
        if not isinstance(content, str) or not content:
            return 0
        return _tok_estimate(content)

    total_tokens = sum(_content_tokens(m) for m in messages)

    recent = messages[-window:]
    if not recent:
        return CompactionSignals(
            tokens_used=total_tokens,
            max_tokens=max_tokens,
            tool_call_density=0.0,
            observation_size_p95=0,
        )

    tool_msgs = [m for m in recent if _is_tool_message(m)]
    density = len(tool_msgs) / len(recent)

    tool_sizes = [
        len(m["content"])
        for m in tool_msgs
        if isinstance(m.get("content"), str)
        and not _looks_already_cleared(m)
    ]
    p95 = _percentile(tool_sizes, 0.95) if tool_sizes else 0

    failures = 0
    for m in recent:
        text = m.get("content")
        if not isinstance(text, str):
            continue
        if any(kw in text for kw in failure_keywords):
            failures += 1

    return CompactionSignals(
        tokens_used=total_tokens,
        max_tokens=max_tokens,
        tool_call_density=density,
        observation_size_p95=p95,
        recent_failure_count=failures,
    )


def _percentile(values: list[int], q: float) -> int:
    """Nearest-rank percentile; ``q`` in [0, 1]."""
    if not values:
        return 0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    if q <= 0:
        return ordered[0]
    if q >= 1:
        return ordered[-1]
    # Nearest-rank: ceil(q * N)
    import math

    idx = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def suggest_compaction(
    signals: CompactionSignals,
    *,
    profile: ContextProfile = STANDARD,
) -> CompactionAdvice:
    """Decide whether to suggest compaction based on the signals."""
    reasons: list[str] = []
    urgency = URGENCY_NONE

    fill = signals.fill_ratio
    hard = profile.autocompact_pct
    soft = max(0.0, hard - SOFT_FILL_OFFSET)

    if fill >= hard:
        reasons.append(f"fill_ratio {fill:.2f} >= hard threshold {hard:.2f}")
        urgency = URGENCY_HARD
    elif fill >= soft:
        reasons.append(f"fill_ratio {fill:.2f} >= soft threshold {soft:.2f}")
        urgency = URGENCY_SOFT

    if signals.tool_call_density >= TOOL_DENSITY_TRIGGER:
        reasons.append(
            f"tool_call_density {signals.tool_call_density:.2f} "
            f">= {TOOL_DENSITY_TRIGGER:.2f}"
        )
        if urgency == URGENCY_NONE:
            urgency = URGENCY_SOFT

    p95_cap = profile.reduction_cap_kb * 1024 * OBSERVATION_P95_MULTIPLE
    if signals.observation_size_p95 >= p95_cap:
        reasons.append(
            f"observation_size_p95 {signals.observation_size_p95} bytes "
            f">= {int(p95_cap)} bytes (reduction cap × {OBSERVATION_P95_MULTIPLE})"
        )
        if urgency == URGENCY_NONE:
            urgency = URGENCY_SOFT

    return CompactionAdvice(
        suggested=urgency != URGENCY_NONE,
        urgency=urgency,
        reasons=tuple(reasons),
        signals=signals,
    )


def stdev_of_recent_failures(signals: CompactionSignals) -> float:
    """Diagnostic: stdev of failure counts isn't computed from signals
    alone; this helper exists so callers can plug observability sinks
    without us re-importing :mod:`statistics` at every call site.
    """
    return float(statistics.pvariance([signals.recent_failure_count])) ** 0.5


def emit_advice_metrics(
    advice: CompactionAdvice, *, on_metric: Callable[[str, object], None]
) -> None:
    """Push every key from :meth:`CompactionAdvice.to_metric_dict` through
    ``on_metric``."""
    for name, value in advice.to_metric_dict().items():
        on_metric(name, value)


__all__ = [
    "CompactionAdvice",
    "CompactionSignals",
    "OBSERVATION_P95_MULTIPLE",
    "SOFT_FILL_OFFSET",
    "TOOL_DENSITY_TRIGGER",
    "URGENCY_HARD",
    "URGENCY_NONE",
    "URGENCY_SOFT",
    "compute_signals",
    "emit_advice_metrics",
    "stdev_of_recent_failures",
    "suggest_compaction",
]
