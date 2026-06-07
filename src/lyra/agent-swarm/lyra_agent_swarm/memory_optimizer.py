"""Memory Optimizer — token budget management and context compaction for swarms.

Implements memory optimization for agent swarm contexts:
  - Region-based token tracking
  - Utilization monitoring with warning thresholds
  - Optimization actions: compact, truncate, offload, evict
  - Automatic optimization when budget is exceeded
  - Memory statistics with per-region breakdown
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class OptimizationAction(StrEnum):
    """Actions the memory optimizer can recommend."""

    COMPACT = "compact"
    TRUNCATE = "truncate"
    OFFLOAD = "offload"
    EVICT = "evict"
    SUMMARIZE = "summarize"


@dataclass
class MemoryRegion:
    """A named region of token memory being tracked."""

    name: str
    token_count: int
    max_tokens: int
    last_updated: float = field(default_factory=time.monotonic)

    @property
    def utilization(self) -> float:
        return self.token_count / max(self.max_tokens, 1)

    @property
    def is_critical(self) -> bool:
        return self.utilization >= 0.85

    @property
    def available(self) -> int:
        return max(0, self.max_tokens - self.token_count)


@dataclass(frozen=True)
class OptimizationResult:
    """Result of a memory optimization action."""

    action: OptimizationAction
    region: str
    tokens_saved: int
    success: bool
    reason: str = ""


@dataclass
class MemoryStats:
    """Aggregate memory statistics across all regions."""

    total_used: int = 0
    total_max: int = 0
    region_count: int = 0
    regions_at_critical: int = 0

    @property
    def utilization(self) -> float:
        return self.total_used / max(self.total_max, 1)

    @property
    def is_critical(self) -> bool:
        return self.utilization >= 0.9


class MemoryOptimizer:
    """Optimizes token memory usage across swarm context regions.

    Tracks token usage per region, warns when approaching budget limits,
    and generates optimization actions to reclaim memory.

    Usage::

        opt = MemoryOptimizer(max_total_tokens=100_000)
        opt.register_region("conversation_history", token_count=30_000, max_tokens=50_000)
        opt.register_region("agent_contexts", token_count=20_000, max_tokens=50_000)

        if opt.is_warning:
            actions = opt.optimize()
            for result in actions:
                apply_optimization(result)
    """

    def __init__(
        self,
        max_total_tokens: int = 100_000,
        warning_threshold: float = 0.75,
    ) -> None:
        self.max_total_tokens = max_total_tokens
        self.warning_threshold = warning_threshold
        self._regions: dict[str, MemoryRegion] = {}
        self._action_history: list[OptimizationResult] = []

    # ── Properties ───────────────────────────────────────────────

    @property
    def total_used(self) -> int:
        return sum(r.token_count for r in self._regions.values())

    @property
    def region_count(self) -> int:
        return len(self._regions)

    @property
    def is_warning(self) -> bool:
        return self.get_utilization() >= self.warning_threshold

    # ── Region Management ────────────────────────────────────────

    def register_region(
        self,
        name: str,
        token_count: int,
        max_tokens: int,
    ) -> MemoryRegion:
        """Register a memory region for tracking."""
        if name in self._regions:
            raise ValueError(f"Region '{name}' already registered")
        region = MemoryRegion(
            name=name,
            token_count=token_count,
            max_tokens=max_tokens,
        )
        self._regions[name] = region
        return region

    def update_region(self, name: str, token_count: int) -> MemoryRegion:
        """Update the token count for a region."""
        region = self._regions.get(name)
        if region is None:
            raise ValueError(f"Region '{name}' not found")
        region.token_count = max(0, token_count)
        region.last_updated = time.monotonic()
        return region

    def get_region(self, name: str) -> MemoryRegion | None:
        """Get a region by name."""
        return self._regions.get(name)

    def unregister_region(self, name: str) -> None:
        """Remove a region from tracking."""
        self._regions.pop(name, None)

    # ── Utilization ──────────────────────────────────────────────

    def get_utilization(self) -> float:
        """Get overall memory utilization (0.0-1.0)."""
        return self.total_used / max(self.max_total_tokens, 1)

    def get_memory_stats(self) -> MemoryStats:
        """Get comprehensive memory statistics."""
        critical_count = sum(
            1 for r in self._regions.values() if r.is_critical
        )
        return MemoryStats(
            total_used=self.total_used,
            total_max=self.max_total_tokens,
            region_count=len(self._regions),
            regions_at_critical=critical_count,
        )

    # ── Optimization ─────────────────────────────────────────────

    def optimize(self) -> list[OptimizationResult]:
        """Generate optimization actions to reduce memory pressure.

        Returns a list of recommended actions sorted by impact.
        """
        if not self.is_warning:
            return []

        actions: list[OptimizationResult] = []
        regions = sorted(
            self._regions.values(),
            key=lambda r: r.utilization,
            reverse=True,
        )

        for region in regions:
            if region.utilization >= 0.85:
                # Highly utilized region — suggest compaction or truncation
                target = int(region.max_tokens * 0.7)
                savings = max(0, region.token_count - target)
                if savings > 0:
                    if region.name in ("history", "conversation", "log"):
                        actions.append(
                            OptimizationResult(
                                action=OptimizationAction.TRUNCATE,
                                region=region.name,
                                tokens_saved=savings,
                                success=True,
                                reason=f"Region '{region.name}' at {region.utilization:.0%}",
                            )
                        )
                    else:
                        actions.append(
                            OptimizationResult(
                                action=OptimizationAction.COMPACT,
                                region=region.name,
                                tokens_saved=savings,
                                success=True,
                                reason=f"Region '{region.name}' at {region.utilization:.0%}",
                            )
                        )
            elif region.utilization >= 0.5:
                # Moderately utilized — suggest offload
                savings = int(region.token_count * 0.3)
                if savings > 100:
                    actions.append(
                        OptimizationResult(
                            action=OptimizationAction.OFFLOAD,
                            region=region.name,
                            tokens_saved=savings,
                            success=True,
                            reason=f"Offload 30% of '{region.name}' ({savings} tokens)",
                        )
                    )

        self._action_history.extend(actions)
        return actions

    def get_action_history(self) -> list[OptimizationResult]:
        """Get history of performed optimization actions."""
        return list(self._action_history)

    def reset(self) -> None:
        """Reset all regions and history."""
        self._regions.clear()
        self._action_history.clear()
