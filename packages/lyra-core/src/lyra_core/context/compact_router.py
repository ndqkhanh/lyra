"""Compaction model router (Phase CE.3, P2-2).

Lyra's :func:`compact_messages` is model-agnostic — the caller injects
an ``llm`` callable. When a session is humming along on simple tool
chatter, the cheap summariser is enough; when the compact window
carries many invariants (failing-test names, deny reasons, file
anchors), the smart summariser is worth its cost.

This module gives callers a deterministic ``"cheap" | "smart"`` decision
based on the same signals the relevance scorer already computes — no
new LLM call required.

Inputs:

* ``invariant_count``    — total file anchors + test names + deny
                           reasons in the compact window.
* ``relevance_variance`` — population variance of per-message
                           relevance scores. High variance means a
                           heterogeneous window where the summariser
                           has to make judgment calls.
* ``window_tokens``      — rough token count of the compact window.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from .compact_validate import extract_default_invariants
from .compactor import _tok_estimate
from .relevance import RelevanceBreakdown, score_message

ROUTE_CHEAP = "cheap"
ROUTE_SMART = "smart"


@dataclass(frozen=True)
class RouterDecision:
    """Outcome of :func:`route_compaction`."""

    route: str  # ROUTE_CHEAP | ROUTE_SMART
    reasons: tuple[str, ...]
    invariant_count: int
    relevance_variance: float
    window_tokens: int


# Thresholds — tuned to the same scale the relevance scorer uses.
# Past these, the smart summariser is preferred. Each is OR-ed; one
# trigger is enough to upgrade.
INVARIANT_TRIGGER = 6
VARIANCE_TRIGGER = 0.05  # variance of relevance scores in [0, 1]
TOKEN_TRIGGER = 4000


def route_compaction(
    compact_window: list[dict],
    *,
    task: str,
) -> RouterDecision:
    """Score the compact window and pick a summariser route.

    Args:
        compact_window: The messages that *will* be summarised — pass
            the slice already excluding the system head and the
            keep-last tail so the decision matches what the
            summariser will actually see.
        task: Current task description for relevance scoring.

    Returns:
        A :class:`RouterDecision` carrying both the route and the
        evidence trail. The evidence trail is for metrics and for
        explainability in a debug log.
    """
    invariants = extract_default_invariants(compact_window)
    invariant_count = len(invariants)

    scores: list[float] = []
    for i, msg in enumerate(compact_window):
        breakdown: RelevanceBreakdown = score_message(
            msg,
            task=task,
            later_messages=compact_window[i + 1 :],
        )
        scores.append(breakdown.score)

    variance = (
        statistics.pvariance(scores) if len(scores) > 1 else 0.0
    )

    window_tokens = 0
    for msg in compact_window:
        content = msg.get("content")
        if isinstance(content, str) and content:
            window_tokens += _tok_estimate(content)

    reasons: list[str] = []
    if invariant_count >= INVARIANT_TRIGGER:
        reasons.append(
            f"invariant_count {invariant_count} >= {INVARIANT_TRIGGER}"
        )
    if variance >= VARIANCE_TRIGGER:
        reasons.append(
            f"relevance_variance {variance:.3f} >= {VARIANCE_TRIGGER:.3f}"
        )
    if window_tokens >= TOKEN_TRIGGER:
        reasons.append(f"window_tokens {window_tokens} >= {TOKEN_TRIGGER}")

    route = ROUTE_SMART if reasons else ROUTE_CHEAP
    if not reasons:
        reasons = [
            f"invariant_count {invariant_count}; "
            f"variance {variance:.3f}; tokens {window_tokens}"
        ]

    return RouterDecision(
        route=route,
        reasons=tuple(reasons),
        invariant_count=invariant_count,
        relevance_variance=variance,
        window_tokens=window_tokens,
    )


__all__ = [
    "INVARIANT_TRIGGER",
    "ROUTE_CHEAP",
    "ROUTE_SMART",
    "RouterDecision",
    "TOKEN_TRIGGER",
    "VARIANCE_TRIGGER",
    "route_compaction",
]
