"""Context Window Optimizer — Dynamic window management and prediction.

Provides dynamic window size recommendation, pre-fetching prediction,
LRU-style eviction with importance override, element clustering for
batch loading, and cache warming strategies.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .strategies import CompactionStrategy, StrategyRegistry

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class OptimizerError(Exception):
    """Base exception for optimizer errors."""


class NoOptimizationNeededError(OptimizerError):
    """Raised when the context is already in an optimal state."""


class EvictionError(OptimizerError):
    """Raised when eviction or cache operations fail."""


# ── Enums & Types ───────────────────────────────────────────────────────────────


class EvictionPolicy(Enum):
    """Eviction strategies for context elements."""

    LRU = auto()                    # Least Recently Used
    LFU = auto()                    # Least Frequently Used
    IMPORTANCE_WEIGHTED = auto()    # Weighted by importance score
    HYBRID = auto()                 # Combines LRU + importance


@dataclass
class EvictionCandidate:
    """An element considered for eviction."""

    element_id: str
    lru_score: float       # 0.0 (least recent) to 1.0 (most recent)
    importance_score: float  # 0.0 (least important) to 1.0 (most important)
    size_tokens: int
    combined_score: float   # Lower = more evictable
    eviction_priority: float = 0.0


@dataclass
class ClusterConfig:
    """Configuration for element clustering."""

    max_cluster_size_tokens: int = 4000
    similarity_threshold: float = 0.6
    merge_related: bool = True
    preserve_order: bool = True


@dataclass
class CacheWarmingStrategy:
    """Strategy for preemptive context loading."""

    name: str
    description: str
    preload_threshold: float  # Utilization % that triggers preloading
    max_preload_tokens: int
    priority_bias: dict[str, float] = field(default_factory=dict)  # type -> weight


@dataclass
class OptimizationResult:
    """Result of an optimization pass."""

    tokens_before: int
    tokens_after: int
    tokens_freed: int
    elements_evicted: list[str]
    strategy_used: CompactionStrategy
    eviction_policy: EvictionPolicy
    duration_ms: float
    clustering_applied: bool = False
    preload_recommendations: list[str] = field(default_factory=list)


@dataclass
class WindowSizeRecommendation:
    """Recommendation for dynamic context window sizing."""

    current_utilization_pct: float
    recommended_limit: int
    reason: str
    urgency: str  # "low", "medium", "high", "critical"
    estimated_cost_savings_pct: float = 0.0


# ── Context Optimizer ───────────────────────────────────────────────────────────


class ContextOptimizer:
    """Context window optimizer with prediction and eviction.

    Manages context window efficiency through:
    - Dynamic window sizing recommendations
    - Pre-fetching prediction of future context needs
    - Configurable eviction policies with importance override
    - Element clustering for batch context loading
    - Cache warming strategies

    Usage::

        optimizer = ContextOptimizer()
        result = await optimizer.optimize(
            elements=context_elements,
            dependency_graph=deps,
            reverse_dependencies=rev_deps,
            budget=token_budget,
            strategy_registry=registry,
        )
    """

    def __init__(
        self,
        default_eviction_policy: EvictionPolicy = EvictionPolicy.HYBRID,
        max_cluster_size: int = 4000,
    ):
        self._eviction_policy = default_eviction_policy
        self._max_cluster_size = max_cluster_size
        self._access_timestamps: OrderedDict[str, float] = OrderedDict()
        self._prefetch_cache: dict[str, float] = {}
        self._optimization_history: list[OptimizationResult] = []

        # Built-in cache warming strategies
        self._warming_strategies: list[CacheWarmingStrategy] = [
            CacheWarmingStrategy(
                name="aggressive_preload",
                description="Preload related elements when utilization exceeds 60%",
                preload_threshold=0.60,
                max_preload_tokens=8000,
                priority_bias={"CODE": 0.8, "DOCUMENTATION": 0.6, "MEMORY": 0.5},
            ),
            CacheWarmingStrategy(
                name="conservative_preload",
                description="Preload only high-importance elements at 80% utilization",
                preload_threshold=0.80,
                max_preload_tokens=4000,
                priority_bias={"CODE": 0.9, "SYSTEM_PROMPT": 0.7},
            ),
            CacheWarmingStrategy(
                name="predictive_preload",
                description="Predict future needs based on access patterns",
                preload_threshold=0.70,
                max_preload_tokens=6000,
            ),
        ]

    async def optimize(
        self,
        elements: dict[str, Any],
        dependency_graph: dict[str, set[str]],
        reverse_dependencies: dict[str, set[str]],
        budget: Any,
        strategy_registry: StrategyRegistry,
    ) -> Any | None:
        """Run the optimization pipeline.

        Returns a CompactionRecommendation or None if no optimization is needed.
        """
        from .profiler import CompactionRecommendation, ContextHealth

        start = time.perf_counter()

        # 1. Assess current state
        utilization_pct = budget.utilization_pct
        if utilization_pct < 50.0:
            logger.debug("Context utilization at %.1f%%, no optimization needed", utilization_pct)
            return None

        # 2. Select eviction strategy
        eviction_policy = self._select_eviction_policy(utilization_pct)

        # 3. Compute eviction scores
        candidates = self._rank_eviction_candidates(
            elements=elements,
            dependency_graph=dependency_graph,
            reverse_dependencies=reverse_dependencies,
            policy=eviction_policy,
        )

        # 4. Determine what to compact/drop
        strategy = self._select_compaction_strategy(utilization_pct, strategy_registry)

        elements_to_drop: list[str] = []
        elements_to_compact: list[str] = []

        target_free = int(budget.total_limit * 0.30)  # Aim for 30% free

        cumulative_freed = 0
        for candidate in candidates:
            if cumulative_freed >= target_free:
                break

            if candidate.combined_score < 0.2:
                elements_to_drop.append(candidate.element_id)
                cumulative_freed += candidate.size_tokens
            elif candidate.combined_score < 0.5:
                elements_to_compact.append(candidate.element_id)
                cumulative_freed += int(candidate.size_tokens * 0.6)

        # 5. Determine urgency
        if utilization_pct >= 95:
            urgency = ContextHealth.EXCEEDED
        elif utilization_pct >= 85:
            urgency = ContextHealth.CRITICAL
        elif utilization_pct >= 70:
            urgency = ContextHealth.WARNING
        else:
            urgency = ContextHealth.HEALTHY

        quality_loss = len(elements_to_drop) * 0.05 + len(elements_to_compact) * 0.10
        quality_loss = min(quality_loss / max(len(elements), 1), 1.0)

        # 6. Update access timestamps
        now = time.time()
        for eid in elements:
            if eid not in self._access_timestamps:
                self._access_timestamps[eid] = now

        # 7. Record optimization
        result = OptimizationResult(
            tokens_before=budget.used,
            tokens_after=max(0, budget.used - cumulative_freed),
            tokens_freed=cumulative_freed,
            elements_evicted=elements_to_drop,
            strategy_used=strategy,
            eviction_policy=eviction_policy,
            duration_ms=(time.perf_counter() - start) * 1000,
        )
        self._optimization_history.append(result)

        CompactionRecommendation = __import__(
            "lyra_context_profiler.profiler", fromlist=["CompactionRecommendation"]
        ).CompactionRecommendation

        return CompactionRecommendation(
            strategy=strategy,
            target_free_tokens=cumulative_freed,
            estimated_quality_loss=quality_loss,
            elements_to_compact=elements_to_compact,
            elements_to_drop=elements_to_drop,
            rationale=f"Optimized via {eviction_policy.name} eviction with {strategy.name} strategy",
            urgency=urgency,
        )

    async def predict_future_context(
        self,
        elements: dict[str, Any],
        access_history: list[dict[str, Any]] | None = None,
        look_ahead: int = 5,
    ) -> list[str]:
        """Predict which elements will be needed next based on access patterns.

        Uses a simple Markov-like prediction: elements accessed together tend
        to be needed together.
        """
        if not access_history or len(access_history) < 2:
            return []

        # Build co-access matrix
        co_access: dict[str, dict[str, int]] = {}
        for i in range(len(access_history) - 1):
            current_set = set(access_history[i].get("accessed_ids", []))
            next_set = set(access_history[i + 1].get("accessed_ids", []))

            for eid in current_set:
                if eid not in co_access:
                    co_access[eid] = {}
                for next_id in next_set:
                    co_access[eid][next_id] = co_access[eid].get(next_id, 0) + 1

        # Predict based on most recent access
        if not access_history:
            return []

        recent = set(access_history[-1].get("accessed_ids", []))
        predictions: dict[str, float] = {}
        for eid in recent:
            if eid in co_access:
                for next_id, count in co_access[eid].items():
                    if next_id in elements:
                        predictions[next_id] = predictions.get(next_id, 0) + count

        sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        return [pid for pid, _ in sorted_preds[:look_ahead]]

    async def cluster_elements(
        self,
        elements: dict[str, Any],
        config: ClusterConfig | None = None,
    ) -> list[list[str]]:
        """Group context elements into clusters for batch loading.

        Similar elements are grouped together to minimize context switching.
        """
        if config is None:
            config = ClusterConfig()

        if not elements:
            return []

        clusters: list[list[str]] = []
        current_cluster: list[str] = []
        current_size = 0

        # Sort by type for natural grouping, then by importance
        sorted_elements = sorted(
            elements.items(),
            key=lambda kv: (
                str(getattr(kv[1], "element_type", "unknown")),
                -getattr(kv[1], "importance_score", 0.0),
            ),
        )

        for eid, element in sorted_elements:
            token_count = getattr(element, "token_count", 0)
            element_type = str(getattr(element, "element_type", "unknown"))

            if current_size + token_count > config.max_cluster_size_tokens:
                if current_cluster:
                    clusters.append(current_cluster)
                current_cluster = [eid]
                current_size = token_count
            else:
                # Check similarity with existing cluster members
                if config.merge_related and current_cluster:
                    if self._can_merge(element_type, current_cluster, elements):
                        current_cluster.append(eid)
                        current_size += token_count
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [eid]
                        current_size = token_count
                else:
                    current_cluster.append(eid)
                    current_size += token_count

        if current_cluster:
            clusters.append(current_cluster)

        return clusters

    async def recommend_window_size(
        self,
        current_utilization: float,
        token_budget: int,
        cost_per_1k_tokens: float = 0.003,
    ) -> WindowSizeRecommendation:
        """Recommend an optimal context window size.

        Based on utilization patterns and cost considerations.
        """
        if current_utilization > 95:
            return WindowSizeRecommendation(
                current_utilization_pct=current_utilization,
                recommended_limit=int(token_budget * 1.3),
                reason="CRITICAL: near capacity, risk of context loss",
                urgency="critical",
                estimated_cost_savings_pct=0,
            )
        elif current_utilization > 80:
            return WindowSizeRecommendation(
                current_utilization_pct=current_utilization,
                recommended_limit=token_budget,
                reason="HIGH: approaching capacity, consider compaction first",
                urgency="high",
                estimated_cost_savings_pct=5.0,
            )
        elif current_utilization > 60:
            return WindowSizeRecommendation(
                current_utilization_pct=current_utilization,
                recommended_limit=token_budget,
                reason="MODERATE: healthy utilization",
                urgency="medium",
                estimated_cost_savings_pct=10.0,
            )
        else:
            return WindowSizeRecommendation(
                current_utilization_pct=current_utilization,
                recommended_limit=int(token_budget * 0.8),
                reason="LOW: under-utilized, could reduce costs",
                urgency="low",
                estimated_cost_savings_pct=20.0,
            )

    async def warm_cache(
        self,
        elements: dict[str, Any],
        strategy_name: str = "predictive_preload",
    ) -> list[str]:
        """Preemptively load context elements based on a warming strategy."""
        strategy = next(
            (s for s in self._warming_strategies if s.name == strategy_name),
            self._warming_strategies[-1],  # Default to predictive
        )

        preload: list[str] = []
        token_budget_used = 0

        # Sort elements by predicted need
        sorted_elements = sorted(
            elements.items(),
            key=lambda kv: self._prefetch_cache.get(kv[0], 0.0),
            reverse=True,
        )

        for eid, element in sorted_elements:
            if token_budget_used >= strategy.max_preload_tokens:
                break

            element_type = str(getattr(element, "element_type", ""))
            priority_bias = strategy.priority_bias.get(element_type, 0.3)

            if self._prefetch_cache.get(eid, 0) + priority_bias > 0.5:
                preload.append(eid)
                token_budget_used += getattr(element, "token_count", 0)

        logger.info(
            "Cache warming (%s): preloaded %d elements, %d tokens",
            strategy_name, len(preload), token_budget_used,
        )
        return preload

    def record_access(self, element_id: str) -> None:
        """Record that an element was accessed (for LRU tracking)."""
        self._access_timestamps[element_id] = time.time()
        # Update prefetch cache
        self._prefetch_cache[element_id] = self._prefetch_cache.get(element_id, 0) + 1

    # ── Internal Methods ─────────────────────────────────────────────────────

    def _select_eviction_policy(self, utilization_pct: float) -> EvictionPolicy:
        """Choose the best eviction policy for current utilization."""
        if utilization_pct > 90:
            return EvictionPolicy.HYBRID  # Best balance at high pressure
        elif utilization_pct > 70:
            return EvictionPolicy.IMPORTANCE_WEIGHTED  # Preserve important content
        else:
            return EvictionPolicy.LRU  # Simple LRU at low pressure

    @staticmethod
    def _select_compaction_strategy(
        utilization_pct: float,
        registry: StrategyRegistry,
    ) -> CompactionStrategy:
        """Select compaction strategy based on urgency."""
        if utilization_pct > 90:
            return CompactionStrategy.AGGRESSIVE
        elif utilization_pct > 75:
            return CompactionStrategy.BALANCED
        elif utilization_pct > 60:
            return CompactionStrategy.CONSERVATIVE
        else:
            return CompactionStrategy.ADAPTIVE

    def _rank_eviction_candidates(
        self,
        elements: dict[str, Any],
        dependency_graph: dict[str, set[str]],
        reverse_dependencies: dict[str, set[str]],
        policy: EvictionPolicy,
    ) -> list[EvictionCandidate]:
        """Rank all elements by evictability."""
        now = time.time()
        max_age = max(
            (now - self._access_timestamps.get(eid, now)) for eid in elements
        ) or 1.0

        candidates: list[EvictionCandidate] = []
        for eid, element in elements.items():
            importance = getattr(element, "importance_score", 0.5)
            token_count = getattr(element, "token_count", 0)
            age = now - self._access_timestamps.get(eid, now)
            lru_score = 1.0 - (age / max_age)

            # Elements with dependencies should be harder to evict
            dep_penalty = len(reverse_dependencies.get(eid, set())) * 0.1

            if policy == EvictionPolicy.LRU:
                combined = 1.0 - lru_score  # Lower LRU = higher eviction priority
            elif policy == EvictionPolicy.LFU:
                access_count = getattr(element, "access_count", 0)
                combined = 1.0 - min(access_count / 10.0, 1.0)
            elif policy == EvictionPolicy.IMPORTANCE_WEIGHTED:
                combined = 1.0 - importance + dep_penalty
            else:  # HYBRID
                combined = (
                    0.4 * (1.0 - lru_score)
                    + 0.4 * (1.0 - importance)
                    + 0.2 * dep_penalty
                )

            candidates.append(EvictionCandidate(
                element_id=eid,
                lru_score=lru_score,
                importance_score=importance,
                size_tokens=token_count,
                combined_score=1.0 - combined,  # Higher = more evictable
                eviction_priority=combined,
            ))

        candidates.sort(key=lambda c: c.eviction_priority, reverse=True)
        return candidates

    @staticmethod
    def _can_merge(
        element_type: str,
        cluster: list[str],
        elements: dict[str, Any],
    ) -> bool:
        """Determine if an element can be merged into an existing cluster."""
        if not cluster:
            return True
        # Same type elements should cluster together
        cluster_types = {
            str(getattr(elements[eid], "element_type", "unknown"))
            for eid in cluster if eid in elements
        }
        return element_type in cluster_types

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def eviction_policy(self) -> EvictionPolicy:
        return self._eviction_policy

    @eviction_policy.setter
    def eviction_policy(self, policy: EvictionPolicy) -> None:
        self._eviction_policy = policy

    @property
    def optimization_count(self) -> int:
        return len(self._optimization_history)

    @property
    def prefetch_scores(self) -> dict[str, float]:
        return dict(self._prefetch_cache)
