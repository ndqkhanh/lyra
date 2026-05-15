"""harness_core.evals — eval discipline for honest agent comparisons.

Per [docs/202-multi-agent-multi-hop-reckoning-2026.md](../../../../../../research/harness-engineering/docs/202-multi-agent-multi-hop-reckoning-2026.md) §3
(Tran & Kiela equal-budget critique) and [docs/199-multi-hop-reasoning-techniques-arc.md]
(../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md) (test-time-compute
plateau-or-decline on noisy retrieval), every multi-hop / multi-agent comparison
must control thinking-token budget, plot the TTC curve, and (for MoE) account
for active parameters separately from total parameters.

Three modules:
    - equal_budget — fair single-vs-multi-agent token-budget enforcer.
    - ttc_curve — accuracy vs thinking-token-budget plotter; finds inflection.
    - active_params — MoE-aware cost normaliser per Steele & Katz arXiv:2601.04254.
"""
from __future__ import annotations

from .active_params import ActiveParamAccount, ActiveParamReading
from .equal_budget import BudgetController, BudgetExhausted
from .ttc_curve import TTCCurve, TTCPoint

__all__ = [
    "ActiveParamAccount",
    "ActiveParamReading",
    "BudgetController",
    "BudgetExhausted",
    "TTCCurve",
    "TTCPoint",
]
