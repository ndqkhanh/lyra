"""harness_core.routing — query/task type routers.

Per [docs/202-multi-agent-multi-hop-reckoning-2026.md](../../../../../../research/harness-engineering/docs/202-multi-agent-multi-hop-reckoning-2026.md)
§1 (BELLE bi-level multi-agent reasoning), [docs/203-polaris-multi-hop-reasoning-apply-plan.md]
(../../../../../../research/harness-engineering/docs/203-polaris-multi-hop-reasoning-apply-plan.md) §3.3,
[docs/208-lyra-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/208-lyra-multi-hop-collaborative-apply-plan.md) §3.3,
[docs/220-orion-code-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/220-orion-code-multi-hop-collaborative-apply-plan.md) §3.3.

The BELLE routing pattern (without the bi-level debate) — types incoming
queries into operator-shaped buckets so the right reasoning method fires per
question type. Most of BELLE's empirical gain comes from the routing decision,
not the debate; per Tran & Kiela ([docs/202] §3) the debate doesn't survive
equal-budget control.
"""
from __future__ import annotations

from .bell_router import (
    BELLERouter,
    QueryType,
    RouteDecision,
    RuleBasedClassifier,
)

__all__ = [
    "BELLERouter",
    "QueryType",
    "RouteDecision",
    "RuleBasedClassifier",
]
