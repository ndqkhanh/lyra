"""Context Profiling Engine — Real-time context window analysis and optimization.

Analyzes current context window utilization, token budget, element classification,
importance scoring, compression recommendations, and context health monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol

from .compaction import CompactionEngine
from .importance import ImportanceCalculator
from .optimizer import ContextOptimizer
from .strategies import CompactionStrategy, StrategyRegistry

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class ProfilerError(Exception):
    """Base exception for context profiler errors."""


class TokenBudgetExceededError(ProfilerError):
    """Raised when a context window exceeds its configured token budget."""


class ProfileAnalysisError(ProfilerError):
    """Raised when profile analysis fails."""


class InvalidContextElementError(ProfilerError):
    """Raised for malformed or invalid context elements."""


# ── Enums ───────────────────────────────────────────────────────────────────────


class ContextElementType(Enum):
    """Classification of context window elements."""

    CODE = auto()
    CONVERSATION = auto()
    DOCUMENTATION = auto()
    TOOL_OUTPUT = auto()
    SYSTEM_PROMPT = auto()
    MEMORY = auto()
    SKILL_REFERENCE = auto()
    PLAN = auto()
    DIAGNOSTIC = auto()
    UNKNOWN = auto()


class ContextHealth(Enum):
    """Overall context health status."""

    HEALTHY = auto()
    WARNING = auto()
    CRITICAL = auto()
    EXCEEDED = auto()


# ── Data Classes ────────────────────────────────────────────────────────────────


@dataclass
class ContextElement:
    """A single element within the context window."""

    id: str
    content: str
    element_type: ContextElementType
    token_count: int
    importance_score: float = 0.0
    recency: float = 0.0  # seconds since last access
    access_count: int = 0
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ContextElement):
            return NotImplemented
        return self.id == other.id


@dataclass
class TokenBudget:
    """Token budget allocation across context element types."""

    total_limit: int
    used: int = 0
    allocations: dict[ContextElementType, int] = field(default_factory=dict)
    reserved_for_system: int = 0
    reserved_for_tools: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total_limit - self.used)

    @property
    def utilization_pct(self) -> float:
        if self.total_limit == 0:
            return 0.0
        return self.used / self.total_limit * 100


@dataclass
class CompactionRecommendation:
    """Recommendation for context compaction action."""

    strategy: CompactionStrategy
    target_free_tokens: int
    estimated_quality_loss: float  # 0.0 (no loss) to 1.0 (total loss)
    elements_to_compact: list[str]
    elements_to_drop: list[str]
    rationale: str
    urgency: ContextHealth = ContextHealth.HEALTHY


@dataclass
class ContextDashboard:
    """Real-time context health dashboard snapshot."""

    total_tokens: int
    budget_remaining: int
    utilization_pct: float
    health: ContextHealth
    element_counts: dict[ContextElementType, int]
    top_elements_by_importance: list[tuple[str, float]]
    compression_ratio: float
    estimated_freeable_tokens: int
    recommendations: list[CompactionRecommendation]
    timestamp: float = field(default_factory=time.time)


# ── Protocols ───────────────────────────────────────────────────────────────────


class MetricsCollector(Protocol):
    """Protocol for metrics collection hooks."""

    def record_profile(
        self,
        dashboard: ContextDashboard,
        duration_ms: float,
    ) -> None: ...

    def record_compaction(
        self,
        strategy: CompactionStrategy,
        tokens_freed: int,
        quality_loss: float,
    ) -> None: ...


# ── Context Profiler ────────────────────────────────────────────────────────────


class ContextProfiler:
    """Real-time context window profiling and optimization engine.

    This is the main entry point for context analysis. It orchestrates
    importance scoring, compaction, and optimization to keep context
    windows healthy and efficient.

    Usage::

        profiler = ContextProfiler(token_budget=128_000)
        await profiler.add_element(element)
        dashboard = await profiler.analyze()

        if dashboard.health != ContextHealth.HEALTHY:
            result = await profiler.optimize()
    """

    def __init__(
        self,
        token_budget: int = 128_000,
        health_warning_pct: float = 75.0,
        health_critical_pct: float = 90.0,
        auto_optimize: bool = False,
        metrics: MetricsCollector | None = None,
    ):
        self._budget = TokenBudget(total_limit=token_budget)
        self._health_warning_pct = health_warning_pct
        self._health_critical_pct = health_critical_pct
        self._auto_optimize = auto_optimize
        self._metrics = metrics

        self._elements: dict[str, ContextElement] = {}
        self._elements_by_type: dict[ContextElementType, list[str]] = defaultdict(list)
        self._dependency_graph: dict[str, set[str]] = defaultdict(set)
        self._reverse_dependencies: dict[str, set[str]] = defaultdict(set)

        self._importance = ImportanceCalculator()
        self._compaction = CompactionEngine()
        self._optimizer = ContextOptimizer()
        self._strategy_registry = StrategyRegistry()

        self._history: list[ContextDashboard] = []
        self._error_count: int = 0
        self._last_dashboard: ContextDashboard | None = None

    # ── Element Management ──────────────────────────────────────────────────

    async def add_element(self, element: ContextElement) -> None:
        """Register a context element and update all indices."""
        if not element.id:
            raise InvalidContextElementError("Element must have a non-empty id")
        if not element.content:
            raise InvalidContextElementError(f"Element '{element.id}' has empty content")

        self._elements[element.id] = element
        self._elements_by_type[element.element_type].append(element.id)
        self._budget.used += element.token_count

        if self._auto_optimize and self._budget.utilization_pct > self._health_critical_pct:
            await self.optimize()

    async def remove_element(self, element_id: str) -> ContextElement | None:
        """Remove an element and clean up indices."""
        element = self._elements.pop(element_id, None)
        if element is None:
            return None

        self._elements_by_type[element.element_type].remove(element_id)
        self._budget.used = max(0, self._budget.used - element.token_count)

        # Clean up dependency graph
        self._dependency_graph.pop(element_id, None)
        self._reverse_dependencies.pop(element_id, None)
        for deps in self._dependency_graph.values():
            deps.discard(element_id)
        for rev_deps in self._reverse_dependencies.values():
            rev_deps.discard(element_id)

        return element

    async def update_element(self, element_id: str, **updates: Any) -> ContextElement:
        """Update element fields and recalculate derived metrics."""
        element = self._elements.get(element_id)
        if element is None:
            raise InvalidContextElementError(f"Element '{element_id}' not found")

        old_token_count = element.token_count
        for key, value in updates.items():
            if hasattr(element, key):
                setattr(element, key, value)

        if "token_count" in updates:
            self._budget.used += updates["token_count"] - old_token_count

        element.last_accessed_at = time.time()
        return element

    def get_element(self, element_id: str) -> ContextElement | None:
        """Retrieve an element by ID."""
        el = self._elements.get(element_id)
        if el:
            el.last_accessed_at = time.time()
            el.access_count += 1
        return el

    async def add_dependency(self, dependent_id: str, dependency_id: str) -> None:
        """Register a dependency between two context elements."""
        if dependent_id not in self._elements:
            raise InvalidContextElementError(f"Dependent '{dependent_id}' not found")
        if dependency_id not in self._elements:
            raise InvalidContextElementError(f"Dependency '{dependency_id}' not found")

        self._dependency_graph[dependent_id].add(dependency_id)
        self._reverse_dependencies[dependency_id].add(dependent_id)

    # ── Analysis ────────────────────────────────────────────────────────────

    async def analyze(self) -> ContextDashboard:
        """Run full context analysis and return a health dashboard.

        This is the main analysis entry point. It:
        1. Calculates importance scores for all elements
        2. Computes element-type breakdowns
        3. Assesses overall health
        4. Generates compaction recommendations
        """
        start = time.perf_counter()

        try:
            # Score all elements
            await self._score_all_elements()

            # Compute health
            health = self._assess_health()

            # Count by type
            element_counts = self._count_by_type()

            # Top elements
            top_elements = self._top_elements(limit=10)

            # Compression ratio
            compression_ratio = self._calculate_compression_ratio()

            # Freeable tokens estimate
            freeable = self._estimate_freeable_tokens()

            # Generate recommendations
            recommendations = self._generate_recommendations()

            dashboard = ContextDashboard(
                total_tokens=self._budget.used,
                budget_remaining=self._budget.remaining,
                utilization_pct=self._budget.utilization_pct,
                health=health,
                element_counts=element_counts,
                top_elements_by_importance=top_elements,
                compression_ratio=compression_ratio,
                estimated_freeable_tokens=freeable,
                recommendations=recommendations,
            )

            self._last_dashboard = dashboard
            self._history.append(dashboard)

            duration_ms = (time.perf_counter() - start) * 1000
            if self._metrics:
                self._metrics.record_profile(dashboard, duration_ms)

            logger.debug(
                "Context analysis complete: health=%s util=%.1f%% freeable=%d time=%.1fms",
                health.name,
                dashboard.utilization_pct,
                freeable,
                duration_ms,
            )

            return dashboard

        except Exception as exc:
            self._error_count += 1
            raise ProfileAnalysisError(f"Analysis failed: {exc}") from exc

    async def optimize(self) -> CompactionRecommendation:
        """Run the optimizer to free context space.

        Returns the best compaction recommendation and applies it.
        """
        if self._last_dashboard is None:
            await self.analyze()

        recommendation = await self._optimizer.optimize(
            elements=self._elements,
            dependency_graph=self._dependency_graph,
            reverse_dependencies=self._reverse_dependencies,
            budget=self._budget,
            strategy_registry=self._strategy_registry,
        )

        if recommendation and recommendation.elements_to_compact:
            await self._apply_recommendation(recommendation)

        if self._metrics:
            tokens_freed = recommendation.target_free_tokens if recommendation else 0
            quality_loss = recommendation.estimated_quality_loss if recommendation else 0.0
            self._metrics.record_compaction(
                strategy=(
                    recommendation.strategy if recommendation else CompactionStrategy.BALANCED
                ),
                tokens_freed=tokens_freed,
                quality_loss=quality_loss,
            )

        return recommendation

    async def stream_analysis(self) -> AsyncIterator[ContextDashboard]:
        """Stream context dashboards for real-time monitoring."""
        while True:
            dashboard = await self.analyze()
            yield dashboard
            await asyncio.sleep(1.0)

    # ── Internal Methods ─────────────────────────────────────────────────────

    async def _score_all_elements(self) -> None:
        """Recalculate importance scores for all elements."""
        elements_list = list(self._elements.values())
        scored = await self._importance.score_batch(elements_list)
        for element_id, score in scored.items():
            if element_id in self._elements:
                self._elements[element_id].importance_score = score

    def _assess_health(self) -> ContextHealth:
        utilization = self._budget.utilization_pct
        if utilization >= 100.0:
            return ContextHealth.EXCEEDED
        if utilization >= self._health_critical_pct:
            return ContextHealth.CRITICAL
        if utilization >= self._health_warning_pct:
            return ContextHealth.WARNING
        return ContextHealth.HEALTHY

    def _count_by_type(self) -> dict[ContextElementType, int]:
        return {ct: len(ids) for ct, ids in self._elements_by_type.items()}

    def _top_elements(self, limit: int = 10) -> list[tuple[str, float]]:
        sorted_els = sorted(
            self._elements.items(),
            key=lambda kv: kv[1].importance_score,
            reverse=True,
        )
        return [(eid, el.importance_score) for eid, el in sorted_els[:limit]]

    def _calculate_compression_ratio(self) -> float:
        """Estimate the overall compressibility of the context."""
        if not self._elements:
            return 1.0
        # Low-importance elements contribute to compressibility
        total_importance = sum(el.importance_score for el in self._elements.values())
        avg_importance = total_importance / len(self._elements)
        # High avg importance = low compressibility, low avg = high compressibility
        return 1.0 - avg_importance

    def _estimate_freeable_tokens(self) -> int:
        """Estimate how many tokens could be freed through compaction."""
        freeable = 0
        for element in self._elements.values():
            if element.importance_score < 0.3:
                freeable += element.token_count
            elif element.importance_score < 0.5:
                # Partial: could compact to ~30% of original
                freeable += int(element.token_count * 0.7)
        return freeable

    def _generate_recommendations(self) -> list[CompactionRecommendation]:
        health = self._assess_health()
        recommendations: list[CompactionRecommendation] = []

        if health in (ContextHealth.CRITICAL, ContextHealth.EXCEEDED):
            recommendations.append(
                self._make_recommendation(
                    CompactionStrategy.AGGRESSIVE,
                    urgency=health,
                )
            )
            recommendations.append(
                self._make_recommendation(
                    CompactionStrategy.BALANCED,
                    urgency=health,
                )
            )
        elif health == ContextHealth.WARNING:
            recommendations.append(
                self._make_recommendation(
                    CompactionStrategy.BALANCED,
                    urgency=health,
                )
            )
            recommendations.append(
                self._make_recommendation(
                    CompactionStrategy.CONSERVATIVE,
                    urgency=health,
                )
            )

        if self._budget.utilization_pct > 60.0:
            recommendations.append(
                self._make_recommendation(
                    CompactionStrategy.ADAPTIVE,
                    urgency=health,
                )
            )

        return recommendations

    def _make_recommendation(
        self,
        strategy: CompactionStrategy,
        urgency: ContextHealth,
    ) -> CompactionRecommendation:
        elements_to_drop = [
            eid
            for eid, el in self._elements.items()
            if el.importance_score < 0.15 and self._can_drop(eid)
        ]
        elements_to_compact = [
            eid
            for eid, el in self._elements.items()
            if 0.15 <= el.importance_score < 0.5 and self._can_compact(eid)
        ]

        total_freeable = sum(self._elements[eid].token_count for eid in elements_to_drop)
        total_freeable += sum(
            int(self._elements[eid].token_count * 0.6) for eid in elements_to_compact
        )

        if strategy == CompactionStrategy.AGGRESSIVE:
            quality_loss = 0.25
            rationale = "Aggressively free space for critical operations"
        elif strategy == CompactionStrategy.CONSERVATIVE:
            quality_loss = 0.05
            rationale = "Minimal compaction to preserve context fidelity"
        elif strategy == CompactionStrategy.BALANCED:
            quality_loss = 0.12
            rationale = "Balanced approach optimizing for task completion"
        else:
            quality_loss = 0.10
            rationale = "Adaptive strategy learned from prior compaction outcomes"

        return CompactionRecommendation(
            strategy=strategy,
            target_free_tokens=total_freeable,
            estimated_quality_loss=quality_loss,
            elements_to_compact=elements_to_compact,
            elements_to_drop=elements_to_drop,
            rationale=rationale,
            urgency=urgency,
        )

    async def _apply_recommendation(self, recommendation: CompactionRecommendation) -> None:
        """Execute a compaction recommendation."""
        # Drop elements first
        for element_id in recommendation.elements_to_drop:
            await self.remove_element(element_id)

        # Compact remaining elements
        if recommendation.elements_to_compact:
            await self._compaction.compact(
                elements={
                    eid: self._elements[eid]
                    for eid in recommendation.elements_to_compact
                    if eid in self._elements
                },
                strategy=recommendation.strategy,
                target_reduction=recommendation.target_free_tokens,
            )

    def _can_drop(self, element_id: str) -> bool:
        """Check if an element can be safely dropped."""
        # Don't drop elements that others depend on
        return not self._reverse_dependencies.get(element_id)

    def _can_compact(self, element_id: str) -> bool:
        """Check if an element can be safely compacted."""
        element = self._elements.get(element_id)
        if element is None:
            return False
        # Large elements with low importance are good compaction candidates
        return element.token_count > 100

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def element_count(self) -> int:
        return len(self._elements)

    @property
    def budget(self) -> TokenBudget:
        return self._budget

    @property
    def last_dashboard(self) -> ContextDashboard | None:
        return self._last_dashboard

    @property
    def error_count(self) -> int:
        return self._error_count


# ── Context Analyzer (standalone utility) ───────────────────────────────────────


class ContextAnalyzer:
    """Standalone utility for one-shot context analysis without state management.

    Useful for analyzing a snapshot of context without maintaining a profiler
    instance. Ideal for LLM pipeline integration points.
    """

    def __init__(self, model_context_limit: int = 128_000):
        self._model_context_limit = model_context_limit
        self._importance = ImportanceCalculator()

    async def analyze_snapshot(
        self,
        elements: list[ContextElement],
    ) -> ContextDashboard:
        """Analyze a snapshot of context elements without modifying state."""
        scored = await self._importance.score_batch(elements)
        for element in elements:
            element.importance_score = scored.get(element.id, 0.0)

        total_tokens = sum(el.token_count for el in elements)
        budget = TokenBudget(
            total_limit=self._model_context_limit,
            used=total_tokens,
        )

        health = ContextHealth.HEALTHY
        if budget.utilization_pct >= 100:
            health = ContextHealth.EXCEEDED
        elif budget.utilization_pct >= 90:
            health = ContextHealth.CRITICAL
        elif budget.utilization_pct >= 75:
            health = ContextHealth.WARNING

        type_counts: dict[ContextElementType, int] = defaultdict(int)
        for el in elements:
            type_counts[el.element_type] += 1

        top = sorted(
            [(el.id, el.importance_score) for el in elements],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        total_importance = sum(el.importance_score for el in elements)
        avg_importance = total_importance / max(len(elements), 1)
        compression_ratio = 1.0 - avg_importance

        freeable = sum(el.token_count for el in elements if el.importance_score < 0.3)

        return ContextDashboard(
            total_tokens=total_tokens,
            budget_remaining=budget.remaining,
            utilization_pct=budget.utilization_pct,
            health=health,
            element_counts=dict(type_counts),
            top_elements_by_importance=top,
            compression_ratio=compression_ratio,
            estimated_freeable_tokens=freeable,
            recommendations=[],
        )


# ── Profile Matcher ─────────────────────────────────────────────────────────────


@dataclass
class ContextProfile:
    """Snapshot of the task environment for skill matching."""

    task_type: str
    complexity: float
    tools_available: list[str]
    user_preferences: dict[str, float]
    environment_tags: list[str]
    codebase_stats: dict[str, Any] = field(default_factory=dict)


class ProfileMatcher:
    """Matches context profiles to optimal skill compositions.

    Uses pattern matching with weighted feature comparison to determine
    the best-matching task type for a given context profile.
    """

    def __init__(self):
        self._patterns: dict[str, dict[str, float]] = {}
        self._access_count: int = 0

    def register_pattern(self, task_type: str, profile_signature: dict[str, float]) -> None:
        """Register a known pattern signature for a task type."""
        if not task_type:
            raise ValueError("task_type must not be empty")
        self._patterns[task_type] = profile_signature
        logger.debug(
            "Registered pattern for task_type=%s with %d features",
            task_type,
            len(profile_signature),
        )

    def deregister_pattern(self, task_type: str) -> bool:
        """Remove a registered pattern. Returns True if it existed."""
        return self._patterns.pop(task_type, None) is not None

    def match(self, profile: ContextProfile) -> str:
        """Find the best-matching task type for a context profile."""
        self._access_count += 1
        if not self._patterns:
            return "general"

        best_type = "general"
        best_score = -float("inf")

        for task_type, signature in self._patterns.items():
            score = self._score_match(profile, signature)
            if score > best_score:
                best_score = score
                best_type = task_type

        logger.debug(
            "Matched profile to '%s' (score=%.3f, candidates=%d)",
            best_type,
            best_score,
            len(self._patterns),
        )
        return best_type

    def match_with_scores(self, profile: ContextProfile) -> list[tuple[str, float]]:
        """Return all matching task types with their scores, sorted descending."""
        self._access_count += 1
        results = [
            (task_type, self._score_match(profile, signature))
            for task_type, signature in self._patterns.items()
        ]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    @staticmethod
    def _score_match(profile: ContextProfile, signature: dict[str, float]) -> float:
        """Compute a match score between a profile and a pattern signature."""
        score = 0.0
        for key, expected_value in signature.items():
            profile_value = getattr(profile, key, 0.0)
            if isinstance(profile_value, (int, float)):
                # Numeric: closeness to expected value
                score += 1.0 - min(abs(expected_value - float(profile_value)), 1.0)
            elif isinstance(profile_value, list):
                # List: count overlapping elements
                if isinstance(expected_value, (list, tuple)):
                    expected_set = set(expected_value)
                else:
                    expected_set = {str(expected_value)}
                overlap = expected_set & {str(x) for x in profile_value}
                score += len(overlap) / max(len(expected_set), 1)
            elif isinstance(profile_value, dict):
                # Dict: key overlap
                expected_keys = (
                    set(expected_value)
                    if isinstance(expected_value, dict)
                    else {str(expected_value)}
                )
                score += len(expected_keys & set(profile_value)) / max(len(expected_keys), 1)
            elif isinstance(profile_value, str):
                # String: substring match
                if str(expected_value).lower() in profile_value.lower():
                    score += 0.5
        return score

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)

    @property
    def registered_types(self) -> list[str]:
        return sorted(self._patterns.keys())
