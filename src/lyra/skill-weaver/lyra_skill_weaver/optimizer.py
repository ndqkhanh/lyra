"""Composition optimization: profiling, bottleneck identification, alternative exploration, caching.

Optimizes skill compositions for cost, latency, and quality tradeoffs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .skill_weaver import (
    CompositionPattern,
    CompositionPlan,
    SkillRegistry,
)

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class OptimizationObjective(Enum):
    """Objectives for composition optimization."""

    MIN_COST = auto()
    MIN_LATENCY = auto()
    MAX_QUALITY = auto()
    BALANCED = auto()  # Weighted combination
    COST_QUALITY_RATIO = auto()


@dataclass
class ProfilingResult:
    """Performance profiling data for a composition.

    Attributes:
        plan_id: The composition plan profiled.
        execution_time_ms: Actual execution time.
        skill_timings: Per-skill timing breakdown.
        bottlenecks: Identified bottleneck skills.
        cost: Actual cost incurred.
        success: Whether execution succeeded.
        error_message: Error if execution failed.
    """

    plan_id: str
    execution_time_ms: float = 0.0
    skill_timings: dict[str, float] = field(default_factory=dict)
    bottlenecks: list[str] = field(default_factory=list)
    cost: float = 0.0
    success: bool = True
    error_message: str = ""


@dataclass
class OptimizationResult:
    """Result of optimizing a composition.

    Attributes:
        original_plan: The original composition plan.
        optimized_plan: The optimized plan (may be same if no improvement).
        improvement_metrics: Quantified improvements.
        alternatives: Alternative plans explored.
        optimization_time_ms: Time spent optimizing.
    """

    original_plan: CompositionPlan
    optimized_plan: CompositionPlan
    improvement_metrics: dict[str, float] = field(default_factory=dict)
    alternatives: list[CompositionPlan] = field(default_factory=list)
    optimization_time_ms: float = 0.0

    @property
    def cost_reduction(self) -> float:
        """Fractional cost reduction."""
        orig = self.original_plan.estimated_cost
        opt = self.optimized_plan.estimated_cost
        if orig > 0:
            return (orig - opt) / orig
        return 0.0

    @property
    def latency_reduction(self) -> float:
        """Fractional latency reduction."""
        orig = self.original_plan.estimated_latency_ms
        opt = self.optimized_plan.estimated_latency_ms
        if orig > 0:
            return (orig - opt) / orig
        return 0.0

    @property
    def quality_improvement(self) -> float:
        """Absolute quality improvement."""
        return self.optimized_plan.quality_score - self.original_plan.quality_score


# ── Composition Profiler ───────────────────────────────────────────────


class CompositionProfiler:
    """Profiles composition executions to identify bottlenecks.

    Collects timing and cost data for individual skills within compositions
    to enable data-driven optimization.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry
        self._profiles: dict[str, ProfilingResult] = {}
        self._skill_stats: dict[str, deque[float]] = {}  # skill_id -> recent latencies

    def record_execution(
        self,
        plan_id: str,
        skill_timings: dict[str, float],
        cost: float = 0.0,
        success: bool = True,
        error: str = "",
    ) -> ProfilingResult:
        """Record execution data for a composition.

        Args:
            plan_id: The composition plan ID.
            skill_timings: Dict of skill_id -> execution_time_ms.
            cost: Total cost incurred.
            success: Whether execution succeeded.
            error: Error message if failed.

        Returns:
            The profiling result.
        """
        total_time = sum(skill_timings.values())

        # Identify bottlenecks: skills taking >2x the median time
        if skill_timings:
            median_time = sorted(skill_timings.values())[len(skill_timings) // 2]
            bottlenecks = [
                sid for sid, t in skill_timings.items() if t > 2.0 * max(median_time, 1.0)
            ]
        else:
            bottlenecks = []

        # Update per-skill stats
        for sid, t in skill_timings.items():
            if sid not in self._skill_stats:
                self._skill_stats[sid] = deque(maxlen=100)
            self._skill_stats[sid].append(t)

        result = ProfilingResult(
            plan_id=plan_id,
            execution_time_ms=total_time,
            skill_timings=skill_timings,
            bottlenecks=bottlenecks,
            cost=cost,
            success=success,
            error_message=error,
        )
        self._profiles[plan_id] = result
        return result

    def get_profile(self, plan_id: str) -> ProfilingResult | None:
        """Get profiling data for a plan."""
        return self._profiles.get(plan_id)

    def get_skill_stats(self, skill_id: str) -> dict[str, float]:
        """Get aggregate statistics for a skill's performance."""
        timings = self._skill_stats.get(skill_id, deque())
        if not timings:
            return {}
        timings_list = list(timings)
        timings_sorted = sorted(timings_list)
        return {
            "count": len(timings_list),
            "mean_ms": sum(timings_list) / len(timings_list),
            "median_ms": timings_sorted[len(timings_sorted) // 2],
            "p95_ms": timings_sorted[int(len(timings_sorted) * 0.95)],
            "min_ms": min(timings_list),
            "max_ms": max(timings_list),
        }

    def identify_bottlenecks(self, plan: CompositionPlan) -> list[str]:
        """Identify bottleneck skills in a composition.

        Returns:
            List of skill IDs that are likely bottlenecks.
        """
        bottlenecks: list[str] = []
        for sid in plan.modules:
            stats = self.get_skill_stats(sid)
            if stats.get("p95_ms", 0) > 1000:  # >1 second p95
                bottlenecks.append(sid)
        return bottlenecks

    @property
    def summary(self) -> dict[str, Any]:
        """Get profiler summary."""
        return {
            "profiled_plans": len(self._profiles),
            "tracked_skills": len(self._skill_stats),
            "skill_stats": {
                sid: self.get_skill_stats(sid) for sid in list(self._skill_stats.keys())[:10]
            },
        }


# ── Plan Cache ─────────────────────────────────────────────────────────


@dataclass
class CachedPlan:
    """A cached composition plan with metadata.

    Attributes:
        plan: The cached plan.
        cache_key: Lookup key.
        created_at: When the plan was cached.
        hit_count: Number of cache hits.
        last_accessed: Last access timestamp.
    """

    plan: CompositionPlan
    cache_key: str
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class PlanCache:
    """Caches composition plans for reuse to avoid recomputation.

    Plans are keyed by (required_outputs, pattern, context_hash) so that
    similar requests can reuse previously computed plans.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: float = 3600.0) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CachedPlan] = {}
        self._access_order: deque[str] = deque(maxlen=max_size)

    @staticmethod
    def compute_key(
        required_outputs: list[str],
        pattern: CompositionPattern,
        context: dict[str, float] | None = None,
    ) -> str:
        """Compute a cache key from composition parameters.

        Args:
            required_outputs: List of required output names.
            pattern: Composition pattern.
            context: Optional context dict.

        Returns:
            A stable hash string.
        """
        key_parts = [
            ",".join(sorted(required_outputs)),
            pattern.name,
        ]
        if context:
            # Normalize context for stable hashing
            ctx_str = ",".join(f"{k}:{v:.3f}" for k, v in sorted(context.items()))
            key_parts.append(ctx_str)

        raw_key = "|".join(key_parts)
        return hashlib.sha256(raw_key.encode()).hexdigest()[:16]

    def get(self, cache_key: str) -> CompositionPlan | None:
        """Retrieve a cached plan.

        Args:
            cache_key: The cache key.

        Returns:
            Cached plan or None if not found or expired.
        """
        cached = self._cache.get(cache_key)
        if cached is None:
            return None

        # Check TTL
        if time.time() - cached.created_at > self.ttl_seconds:
            del self._cache[cache_key]
            return None

        cached.hit_count += 1
        cached.last_accessed = time.time()
        return cached.plan

    def put(self, cache_key: str, plan: CompositionPlan) -> None:
        """Cache a composition plan.

        Args:
            cache_key: The cache key.
            plan: The plan to cache.
        """
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest = self._find_oldest()
            if oldest:
                del self._cache[oldest]

        self._cache[cache_key] = CachedPlan(plan=plan, cache_key=cache_key)

    def _find_oldest(self) -> str | None:
        """Find the cache key with the oldest last access time."""
        if not self._cache:
            return None
        return min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)

    def invalidate(self, cache_key: str) -> bool:
        """Remove a specific entry from the cache."""
        if cache_key in self._cache:
            del self._cache[cache_key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached plans."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Number of cached plans."""
        return len(self._cache)

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(c.hit_count for c in self._cache.values())
        return {
            "size": self.size,
            "max_size": self.max_size,
            "total_hits": total_hits,
            "avg_hits": total_hits / max(self.size, 1),
        }


# ── Composition Optimizer ──────────────────────────────────────────────


class CompositionOptimizer:
    """Optimizes skill compositions for different objectives.

    Explores alternative skill combinations, identifies bottlenecks
    via profiling data, and produces optimized plans with quantified
    improvements over the original.
    """

    def __init__(
        self,
        registry: SkillRegistry,
        profiler: CompositionProfiler | None = None,
        cache: PlanCache | None = None,
        max_alternatives: int = 20,
    ) -> None:
        self.registry = registry
        self.profiler = profiler or CompositionProfiler(registry)
        self.cache = cache or PlanCache()
        self.max_alternatives = max_alternatives

    async def optimize(
        self,
        plan: CompositionPlan,
        objective: OptimizationObjective = OptimizationObjective.BALANCED,
        context: dict[str, float] | None = None,
    ) -> OptimizationResult:
        """Optimize a composition plan.

        Args:
            plan: The plan to optimize.
            objective: What to optimize for.
            context: Context for skill selection.

        Returns:
            OptimizationResult with optimized plan and metrics.
        """
        start_time = time.time()
        alternatives = await self._generate_alternatives(plan, context)
        alternatives.append(plan)  # Include original as an option

        # Score alternatives based on objective
        scored = [(alt, self._score(alt, objective)) for alt in alternatives]
        scored.sort(key=lambda x: -x[1])  # Higher is better

        best_plan = scored[0][0] if scored else plan
        optimization_time = (time.time() - start_time) * 1000.0

        return OptimizationResult(
            original_plan=plan,
            optimized_plan=best_plan,
            improvement_metrics={
                "cost_reduction": (
                    (plan.estimated_cost - best_plan.estimated_cost)
                    / max(plan.estimated_cost, 1e-10)
                ),
                "latency_reduction": (
                    (plan.estimated_latency_ms - best_plan.estimated_latency_ms)
                    / max(plan.estimated_latency_ms, 1e-10)
                ),
                "quality_improvement": best_plan.quality_score - plan.quality_score,
            },
            alternatives=[a for a, _ in scored[:5]],
            optimization_time_ms=optimization_time,
        )

    async def _generate_alternatives(
        self,
        plan: CompositionPlan,
        context: dict[str, float] | None = None,
    ) -> list[CompositionPlan]:
        """Generate alternative compositions by swapping skills.

        For each skill in the plan, find alternative skills that produce
        the same outputs and create variant plans.
        """
        alternatives: list[CompositionPlan] = []
        context = context or {}

        for i, sid in enumerate(plan.modules):
            skill = self.registry.get(sid)
            if skill is None:
                continue

            # Find skills producing similar outputs
            for out in skill.outputs:
                candidates = self.registry.find_by_output(out.name)
                for candidate in candidates:
                    if candidate.skill_id == sid:
                        continue
                    if candidate.metadata.status.name not in ("ACTIVE", "REGISTERED"):
                        continue

                    # Create alternative plan with swapped skill
                    new_modules = list(plan.modules)
                    new_modules[i] = candidate.skill_id
                    alt_plan = CompositionPlan(
                        plan_id=f"{plan.plan_id}_alt_{candidate.skill_id[:8]}",
                        modules=new_modules,
                        expected_outputs=plan.expected_outputs,
                        estimated_cost=plan.estimated_cost
                        - skill.estimated_cost
                        + candidate.estimated_cost,
                        estimated_latency_ms=plan.estimated_latency_ms
                        - skill.avg_latency_ms
                        + candidate.avg_latency_ms,
                        pattern=plan.pattern,
                        quality_score=plan.quality_score,  # Recompute below
                    )
                    # Recompute quality
                    alt_plan.quality_score = sum(
                        self.registry.get(s).quality_score
                        for s in new_modules
                        if self.registry.get(s)
                    ) / max(len(new_modules), 1)

                    alternatives.append(alt_plan)

                    if len(alternatives) >= self.max_alternatives:
                        return alternatives

        return alternatives

    def _score(self, plan: CompositionPlan, objective: OptimizationObjective) -> float:
        """Score a plan based on the optimization objective.

        Args:
            plan: The plan to score.
            objective: What to optimize for.

        Returns:
            Score (higher is better).
        """
        # Normalize components to [0, 1]
        max_cost = 10.0  # Reference max
        max_latency = 30000.0  # Reference max (30 seconds)

        cost_norm = min(plan.estimated_cost / max_cost, 1.0)
        latency_norm = min(plan.estimated_latency_ms / max_latency, 1.0)
        quality = plan.quality_score

        if objective == OptimizationObjective.MIN_COST:
            return 1.0 - cost_norm
        elif objective == OptimizationObjective.MIN_LATENCY:
            return 1.0 - latency_norm
        elif objective == OptimizationObjective.MAX_QUALITY:
            return quality
        elif objective == OptimizationObjective.COST_QUALITY_RATIO:
            return quality / max(cost_norm, 0.01)
        else:  # BALANCED
            return quality * 0.4 + (1.0 - cost_norm) * 0.3 + (1.0 - latency_norm) * 0.3

    async def optimize_with_profiling(
        self,
        plan: CompositionPlan,
        objective: OptimizationObjective = OptimizationObjective.MIN_LATENCY,
        context: dict[str, float] | None = None,
    ) -> OptimizationResult:
        """Optimize using profiling data for more accurate estimates.

        Replaces estimated latency/cost with measured values from the profiler
        before running the optimization.
        """
        # Update plan estimates with profiling data
        updated_plan = CompositionPlan(
            plan_id=plan.plan_id,
            modules=plan.modules,
            expected_outputs=plan.expected_outputs,
            estimated_cost=plan.estimated_cost,
            estimated_latency_ms=plan.estimated_latency_ms,
            pattern=plan.pattern,
            quality_score=plan.quality_score,
            metadata=plan.metadata,
        )

        for sid in plan.modules:
            stats = self.profiler.get_skill_stats(sid)
            if stats:
                # Use p95 latency from profiling
                p95 = stats.get("p95_ms", 0)
                if p95 > 0:
                    updated_plan.estimated_latency_ms = (
                        updated_plan.estimated_latency_ms
                        - self.registry.get(sid).avg_latency_ms
                        + p95
                    )

        return await self.optimize(updated_plan, objective, context)

    # ── Bottleneck analysis ────────────────────────────────────────────

    def find_bottlenecks(self, plan: CompositionPlan) -> list[dict[str, Any]]:
        """Identify bottlenecks in a composition using profiling data.

        Returns a list of bottleneck details sorted by severity.
        """
        bottlenecks: list[dict[str, Any]] = []
        total_time = sum(
            self.profiler.get_skill_stats(sid).get("p95_ms", 0) for sid in plan.modules
        )

        for sid in plan.modules:
            stats = self.profiler.get_skill_stats(sid)
            if not stats:
                continue
            p95 = stats.get("p95_ms", 0)
            fraction = p95 / max(total_time, 1.0)
            if fraction > 0.3:  # Contributes >30% of total time
                bottlenecks.append(
                    {
                        "skill_id": sid,
                        "p95_latency_ms": p95,
                        "fraction_of_total": fraction,
                        "mean_latency_ms": stats.get("mean_ms", 0),
                    }
                )

        bottlenecks.sort(key=lambda b: -b["fraction_of_total"])
        return bottlenecks

    @property
    def summary(self) -> dict[str, Any]:
        """Get optimizer summary."""
        return {
            "cache": self.cache.stats,
            "profiler": self.profiler.summary,
        }
