"""SLO tracker — Phase A of the Lyra 322-326 evolution plan.

Defines per-turn Service Level Objectives and detects breaches in
real-time from AgentExecutionRecords.  Breach events are emitted to
the in-process event bus so the TUI cockpit can surface alerts.

Grounded in:
- Doc 322 §8.3 — Agent Cockpit SLOs
- Doc 323 §8.5 — Router observability and SLOs
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from .aer import AgentExecutionRecord


__all__ = [
    "SLODefinition",
    "SLOBreach",
    "SLOTracker",
    "DEFAULT_SLOS",
]

SLOName = Literal[
    "cost_budget",
    "context_safety",
    "latency",
    "quality",
    "safety",
    "resource_hygiene",
    "human_control",
]

BreachHandler = Callable[["SLOBreach"], None]


@dataclass(frozen=True)
class SLODefinition:
    """One SLO: a name, threshold, and a check function."""

    name: SLOName
    description: str
    threshold_label: str          # human-readable e.g. "$0.10/turn"
    check: Callable[[AgentExecutionRecord, "SLOState"], bool]
    # True = SLO is passing; False = breach


@dataclass
class SLOState:
    """Mutable per-session accumulator fed to SLO check functions."""

    session_cost_usd: float = 0.0
    last_turn_latency_ms: int = 0
    pending_approval_since: Optional[float] = None   # epoch seconds
    max_pending_approval_seconds: float = 600.0      # 10 min default


@dataclass(frozen=True)
class SLOBreach:
    """One breach event, emitted when an SLO check returns False."""

    slo_name: SLOName
    session_id: str
    turn_index: int
    ts: float
    detail: str


# ------------------------------------------------------------------ #
# Default SLO set (matches Doc 322 §8.3 table)                        #
# ------------------------------------------------------------------ #

def _cost_check(rec: AgentExecutionRecord, state: SLOState) -> bool:
    state.session_cost_usd += rec.tool_cost_usd
    return rec.tool_cost_usd <= 0.10


def _context_check(rec: AgentExecutionRecord, _state: SLOState) -> bool:
    return rec.context_window_pct <= 85.0


def _latency_check(_rec: AgentExecutionRecord, state: SLOState) -> bool:
    return state.last_turn_latency_ms <= 5000


def _quality_check(rec: AgentExecutionRecord, _state: SLOState) -> bool:
    if not rec.verifier_verdict:
        return True
    verdict = rec.verifier_verdict.lower()
    return "fail" not in verdict and "reject" not in verdict


def _safety_check(rec: AgentExecutionRecord, _state: SLOState) -> bool:
    return not rec.policy_gate or "block" not in rec.policy_gate.lower()


def _resource_check(_rec: AgentExecutionRecord, _state: SLOState) -> bool:
    # Wire to process scanner in Phase D
    return True


def _human_control_check(rec: AgentExecutionRecord, state: SLOState) -> bool:
    if rec.permission_decision and state.pending_approval_since is None:
        state.pending_approval_since = rec.ts
    if state.pending_approval_since is not None:
        elapsed = time.time() - state.pending_approval_since
        if elapsed > state.max_pending_approval_seconds:
            return False
        if not rec.permission_decision:
            state.pending_approval_since = None  # resolved
    return True


DEFAULT_SLOS: list[SLODefinition] = [
    SLODefinition(
        name="cost_budget",
        description="Per-turn tool cost must not exceed $0.10",
        threshold_label="$0.10/turn",
        check=_cost_check,
    ),
    SLODefinition(
        name="context_safety",
        description="Context window must stay below 85%",
        threshold_label="85% context",
        check=_context_check,
    ),
    SLODefinition(
        name="latency",
        description="Turn latency must stay below 5 s",
        threshold_label="5 000 ms",
        check=_latency_check,
    ),
    SLODefinition(
        name="quality",
        description="Verifier verdict must not be failure/rejection",
        threshold_label="no fail/reject verdict",
        check=_quality_check,
    ),
    SLODefinition(
        name="safety",
        description="No policy-gate blocks",
        threshold_label="0 blocks",
        check=_safety_check,
    ),
    SLODefinition(
        name="resource_hygiene",
        description="No orphaned OS resources",
        threshold_label="0 orphans",
        check=_resource_check,
    ),
    SLODefinition(
        name="human_control",
        description="Pending approvals must not exceed 10 min",
        threshold_label="600 s",
        check=_human_control_check,
    ),
]


class SLOTracker:
    """Check AERs against a list of SLOs; emit breach events.

    Usage::

        tracker = SLOTracker(on_breach=print)
        tracker.check(aer_record)
    """

    def __init__(
        self,
        slos: list[SLODefinition] | None = None,
        on_breach: BreachHandler | None = None,
    ) -> None:
        self._slos = slos if slos is not None else DEFAULT_SLOS
        self._on_breach = on_breach or (lambda b: None)
        # Per-session state
        self._states: dict[str, SLOState] = {}
        # Running breach log
        self.breaches: list[SLOBreach] = []

    # ---------------------------------------------------------------- #

    def check(self, rec: AgentExecutionRecord) -> list[SLOBreach]:
        """Evaluate all SLOs against *rec*. Returns any new breaches."""
        state = self._states.setdefault(rec.session_id, SLOState())
        new_breaches: list[SLOBreach] = []
        for slo in self._slos:
            passing = slo.check(rec, state)
            if not passing:
                breach = SLOBreach(
                    slo_name=slo.name,
                    session_id=rec.session_id,
                    turn_index=rec.turn_index,
                    ts=rec.ts,
                    detail=f"SLO '{slo.name}' breached (threshold: {slo.threshold_label})",
                )
                new_breaches.append(breach)
                self.breaches.append(breach)
                self._on_breach(breach)
        return new_breaches

    def summary(self, session_id: str) -> dict:
        """Return a summary dict suitable for the TUI status bar."""
        session_breaches = [b for b in self.breaches if b.session_id == session_id]
        breach_names = {b.slo_name for b in session_breaches}
        state = self._states.get(session_id, SLOState())
        return {
            "session_id": session_id,
            "total_breaches": len(session_breaches),
            "breached_slos": sorted(breach_names),
            "session_cost_usd": round(state.session_cost_usd, 6),
            "all_ok": len(session_breaches) == 0,
        }

    def reset_session(self, session_id: str) -> None:
        """Clear state for a finished session."""
        self._states.pop(session_id, None)
        self.breaches = [b for b in self.breaches if b.session_id != session_id]
