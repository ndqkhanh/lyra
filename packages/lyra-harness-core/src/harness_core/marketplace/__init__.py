"""harness_core.marketplace — consumer-side adapter for the argus hub service.

Per [docs/209-argus-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/209-argus-multi-hop-collaborative-apply-plan.md)
and [docs/211-cross-project-power-up-plan-with-tradeoffs.md](../../../../../../research/harness-engineering/docs/211-cross-project-power-up-plan-with-tradeoffs.md) §4.

Every in-tree project consumes argus through these Protocols:
    - :class:`MarketplaceHost` — list_marketplace / install_mcp / get_trust_verdict
    - :class:`CuratorHost` — submit_trajectory / list_promoted_skills

Production wires :class:`argus.HostAdapter`; tests use :class:`InMemoryMarketplaceHost`
+ :class:`InMemoryCuratorHost` deterministic stubs.

The Protocol-typed split (MarketplaceHost vs CuratorHost) reflects argus's
two distinct service surfaces — marketplace + trust gating, and skill
auto-creation + curation. A consumer that only needs one can wire just one.
"""
from __future__ import annotations

from .protocols import CuratorHost, MarketplaceHost
from .stub_adapter import InMemoryCuratorHost, InMemoryMarketplaceHost
from .types import (
    InstallResult,
    MCPServer,
    PromotedSkill,
    SubmitResult,
    TrajectoryRecord,
    TrustTier,
    TrustVerdict,
)

__all__ = [
    "CuratorHost",
    "InMemoryCuratorHost",
    "InMemoryMarketplaceHost",
    "InstallResult",
    "MCPServer",
    "MarketplaceHost",
    "PromotedSkill",
    "SubmitResult",
    "TrajectoryRecord",
    "TrustTier",
    "TrustVerdict",
]
