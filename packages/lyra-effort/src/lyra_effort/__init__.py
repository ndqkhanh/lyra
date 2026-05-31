"""
Lyra Effort Scale — six-item reasoning-budget control for any provider.

Provides the :class:`EffortLevel` enum (low/medium/high/xhigh/max/ultracode),
the :class:`EffortManager` for per-provider effort mapping, and calibration
utilities for dynamic effort-to-budget mapping.

Ultracode = ``xhigh`` reasoning + orchestration toggle — NOT a 6th API budget tier.
This design makes it portable to providers that only expose a couple of effort levels.

Usage::

    from lyra_effort import EffortLevel, EffortManager

    mgr = EffortManager()
    mapping = mgr.map_effort(EffortLevel.XHIGH, provider="anthropic")
    print(mapping.budget_tokens)  # 16384

    # Ultracode: same API budget as xhigh, plus orchestration flag
    ultra = mgr.map_effort(EffortLevel.ULTRACODE, provider="anthropic")
    print(ultra.budget_tokens)        # 16384
    print(ultra.orchestration_enabled)  # True
"""

from __future__ import annotations

from .manager import EffortManager
from .models import (
    EffortConfig,
    EffortLevel,
    EffortMapping,
    OrchestrationConfig,
    ProviderEffortCapability,
)

__all__ = [
    "EffortConfig",
    "EffortLevel",
    "EffortManager",
    "EffortMapping",
    "OrchestrationConfig",
    "ProviderEffortCapability",
]
