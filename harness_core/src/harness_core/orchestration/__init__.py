"""harness_core.orchestration — pure-function agents + replay primitives.

Per [docs/202-multi-agent-multi-hop-reckoning-2026.md](../../../../../../research/harness-engineering/docs/202-multi-agent-multi-hop-reckoning-2026.md) §4
(Yenugula et al.) and [docs/211-cross-project-power-up-plan-with-tradeoffs.md]
(../../../../../../research/harness-engineering/docs/211-cross-project-power-up-plan-with-tradeoffs.md) §4 — every
agent decision is a pure function of (input, context, tool_results); side-effecting tools
go through a gated, logged API; trajectories are replayable.
"""
from __future__ import annotations

from .pure_function import (
    AgentDecision,
    PureFunctionAgent,
    SideEffectLog,
    SideEffectRecord,
    TrajectoryReplay,
    decision_fingerprint,
)

__all__ = [
    "AgentDecision",
    "PureFunctionAgent",
    "SideEffectLog",
    "SideEffectRecord",
    "TrajectoryReplay",
    "decision_fingerprint",
]
