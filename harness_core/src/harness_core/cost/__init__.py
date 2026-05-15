"""harness_core.cost — per-call cost recording + aggregated reports.

Composes :mod:`harness_core.evals.equal_budget` (per-call budget control) +
:mod:`harness_core.evals.active_params` (MoE-aware accounting) into a
production-grade spend tracker.

Records every (operation, project, user, tokens, ...) tuple as a typed
:class:`CostEntry`; aggregates into :class:`CostReport`s grouped by
project / user / operation / period; surfaces threshold alerts when
projected spend exceeds a cap.

Used by every project that ships to production:
    - Polaris ([docs/172] §"cost-aware leaderboards") — per-research-task spend.
    - Mentat-Learn ([docs/210]) — per-user-per-channel monthly bills.
    - Aegis-Ops, Orion-Code — cost gates inside the verifier composer.
    - Atlas-Research, Helix-Bio, Lyra — per-project cost-per-grade reports.
"""
from __future__ import annotations

from .tracker import CostTracker
from .types import (
    BillingPeriod,
    CostEntry,
    CostReport,
    CostThresholdAlert,
    PricingTable,
)

__all__ = [
    "BillingPeriod",
    "CostEntry",
    "CostReport",
    "CostThresholdAlert",
    "CostTracker",
    "PricingTable",
]
