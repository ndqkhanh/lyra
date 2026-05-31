"""
Main ModelRouter for Lyra V4 — 3-tier intelligent model routing.

Coordinates the rule -> semantic -> neural cascade with budget-aware
decision refinement. Records outcomes for feedback-driven improvement.

Architecture:
    Tier 1 (Rule)  → catches 50-60% with keyword/pattern rules
    Tier 2 (Semantic) → catches 20-30% with embedding/TF-IDF similarity
    Tier 3 (Neural) → catches remainder with MLP classifier + online RL

Budget-aware routing (BATS pattern) injects cost constraints into
each decision, with a $5/session circuit breaker.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from lyra_effort import EffortLevel, EffortManager

from .budget import BudgetTracker
from .models import (
    ModelAssignment,
    ModelTier,
    RoutingDecision,
    TaskComplexity,
    get_cost_estimate,
)
from .providers import ProviderRegistry
from .tiers import NeuralTier, RuleTier, SemanticTier, TierResult

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    3-Tier Intelligent Model Router for Lyra AGI V4.

    Routes tasks to optimal models using a cascading decision pipeline
    with budget awareness and online learning.

    Usage::

        router = ModelRouter()
        decision = router.route("implement a JWT auth middleware")
        print(decision.model, decision.tier, decision.confidence)

        # Record the outcome for feedback
        router.record_outcome(decision, success=True, latency_ms=150, cost=0.002)
    """

    # Minimum confidence required to accept a tier result (skips to
    # next tier when confidence is below this threshold).
    _TIER1_MIN_CONFIDENCE = 0.50
    _TIER2_MIN_CONFIDENCE = 0.40

    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        budget_tracker: BudgetTracker | None = None,
        session_budget_usd: float = 5.0,
        exploration_ratio: float = 0.1,
        effort_manager: EffortManager | None = None,
    ) -> None:
        """
        Args:
            provider_registry: Pre-configured provider registry. Creates default if None.
            budget_tracker: Pre-configured budget tracker. Creates default if None.
            session_budget_usd: Total USD budget for the session.
            exploration_ratio: NeuralUCB exploration coefficient (0 = pure exploitation).
            effort_manager: Pre-configured effort manager. Creates default (HIGH effort) if None.
        """
        self.providers = provider_registry or ProviderRegistry()
        self.budget = budget_tracker or BudgetTracker(
            session_budget_usd=session_budget_usd,
            name=f"session-{uuid.uuid4().hex[:8]}",
        )

        self._exploration_ratio = exploration_ratio
        self._effort = effort_manager or EffortManager()

        # Initialize tiers
        self._tier1 = RuleTier()
        self._tier2 = SemanticTier()
        self._tier3 = NeuralTier(exploration_bonus=exploration_ratio)

        # Routing statistics
        self._route_count: int = 0
        self._tier_hits: dict[int, int] = {1: 0, 2: 0, 3: 0}
        self._total_latency_ms: float = 0.0
        self._total_cost: float = 0.0

    # ── Public API ─────────────────────────────────────────────────

    def route(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        force_tier: int | None = None,
        effort_level: str | None = None,
    ) -> RoutingDecision:
        """
        Route a task through the 3-tier cascade and return a model decision.

        Args:
            task: Natural language task description.
            context: Optional context (conversation history, user preferences, tags).
            force_tier: If set, skip to this tier (1, 2, or 3).
            effort_level: Override the session effort level for this decision.
                One of ``low``, ``medium``, ``high``, ``xhigh``, ``max``, ``ultracode``.

        Returns:
            A RoutingDecision with the selected model, tier, confidence, reasoning,
            and effort parameters (budget_tokens, thinking_instruction, reasoning_effort).

        Raises:
            RuntimeError: If the circuit breaker has tripped.
        """
        context = context or {}
        start_time = time.perf_counter()

        # Resolve effort level for this routing decision
        if effort_level:
            try:
                level = EffortLevel(effort_level)
            except ValueError:
                level = self._effort.current_level
        else:
            level = self._effort.current_level

        # Check circuit breaker
        if self.budget.is_tripped:
            raise RuntimeError(
                f"Circuit breaker tripped: ${self.budget.total_spent:.2f} spent "
                f"of ${self.budget.session_budget_usd:.2f} budget. "
                f"Reset the tracker or increase the budget to continue."
            )

        tier_result: TierResult | None = None

        # ---- Tier 1: Rule layer ----
        if force_tier is None or force_tier == 1:
            tier_result = self._tier1.route(task, context)
            if tier_result and tier_result.confidence >= self._TIER1_MIN_CONFIDENCE:
                self._tier_hits[1] += 1
                decision = self._build_decision(tier_result, tier_used=1, effort_level=level)
                elapsed = (time.perf_counter() - start_time) * 1000
                self._record_stats(decision, elapsed)
                logger.debug("Tier 1 (rule) matched: %s", tier_result.reasoning)
                return decision

        # ---- Tier 2: Semantic layer ----
        if force_tier is None or force_tier == 2:
            tier_result = self._tier2.route(task, context)
            if tier_result and tier_result.confidence >= self._TIER2_MIN_CONFIDENCE:
                self._tier_hits[2] += 1
                decision = self._build_decision(tier_result, tier_used=2, effort_level=level)
                elapsed = (time.perf_counter() - start_time) * 1000
                self._record_stats(decision, elapsed)
                logger.debug("Tier 2 (semantic) matched: %s", tier_result.reasoning)
                return decision

        # ---- Tier 3: Neural layer ----
        tier_result = self._tier3.route(task, context)
        if tier_result is None:
            # Ultimate fallback — use moderate complexity
            tier_result = TierResult(
                complexity=TaskComplexity.MODERATE,
                model_tier=ModelTier.STANDARD,
                confidence=0.30,
                reasoning="All tiers exhausted — defaulting to moderate",
                matched_rule="fallback:default",
            )

        self._tier_hits[3] += 1
        decision = self._build_decision(tier_result, tier_used=3, effort_level=level)
        elapsed = (time.perf_counter() - start_time) * 1000
        self._record_stats(decision, elapsed)
        return decision

    def set_effort(self, level: str | EffortLevel) -> None:
        """
        Set the session effort level.

        Args:
            level: Effort level name or enum value.
                ``ultracode`` automatically enables auto-orchestration.
        """
        if isinstance(level, str):
            level = EffortLevel(level)
        self._effort.set_level(level)

    @property
    def effort(self) -> EffortManager:
        """Return the session's effort manager."""
        return self._effort

    def record_outcome(
        self,
        decision: RoutingDecision,
        success: bool,
        latency_ms: float,
        cost: float,
        task: str | None = None,
    ) -> bool:
        """
        Record the outcome of a routing decision for feedback and learning.

        Args:
            decision: The RoutingDecision that was used.
            success: Whether the task completed successfully.
            latency_ms: Actual task latency in milliseconds.
            cost: Actual USD cost of the task.
            task: Original task description (used for NeuralUCB feature extraction).
                Falls back to a synthetic description from the decision if not provided.

        Returns:
            True if recording succeeded, False if circuit breaker tripped.
        """
        # Record to budget tracker
        within_budget = self.budget.record(
            cost_usd=cost,
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            task_summary=f"[{decision.complexity.value}] {decision.model}",
            complexity=decision.complexity,
            model_used=decision.model,
            latency_ms=latency_ms,
            success=success,
        )

        # Train neural tier with outcome (NeuralUCB online learning)
        task_str = task or f"[{decision.complexity.value}] routed to {decision.model}"
        self._tier3.update_with_outcome(
            task=task_str,
            model_id=decision.tier.value,
            success=success,
            latency_ms=latency_ms,
            cost=cost,
        )

        if not within_budget:
            logger.warning(
                "Circuit breaker tripped after task: %s | total_spent=%.4f",
                decision.model,
                self.budget.total_spent,
            )

        return within_budget

    def add_domain_rule(self, keyword: str, tier: ModelTier) -> None:
        """Add a custom domain routing rule to Tier 1."""
        self._tier1.add_rule(keyword, tier)

    def add_training_example(self, task: str, complexity: TaskComplexity, tier: ModelTier) -> None:
        """Add a training example to both Tier 2 and Tier 3."""
        self._tier2.add_example(task, complexity, tier)
        self._tier3.train(task, complexity)

    def fit_neural_model(self) -> bool:
        """Explicitly fit the neural model on accumulated data."""
        return self._tier3.fit()

    # ── Statistics ─────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        """Return current router statistics."""
        avg_latency = self._total_latency_ms / self._route_count if self._route_count > 0 else 0.0
        return {
            "route_count": self._route_count,
            "tier_hits": dict(self._tier_hits),
            "avg_latency_ms": round(avg_latency, 2),
            "total_cost_usd": round(self._total_cost, 6),
            "budget": self.budget.get_summary(),
            "providers": self.providers.get_stats(),
        }

    def get_router_stats(self) -> dict:
        """Return detailed router statistics including NeuralUCB model stats.

        Extends :attr:`stats` with per-model performance metrics from
        the NeuralUCB contextual bandit (pulls, mean rewards, UCB values).

        Returns:
            Dict with all ``stats`` keys plus ``neural_ucb`` containing
            per-model performance data.
        """
        base = dict(self.stats)
        base["neural_ucb"] = self._tier3.get_stats()
        base["exploration_ratio"] = self._exploration_ratio
        return base

    # ── Internal ───────────────────────────────────────────────────

    def _build_decision(
        self, tier_result: TierResult, tier_used: int, effort_level: EffortLevel | None = None
    ) -> RoutingDecision:
        """Build a RoutingDecision from a tier result, applying budget constraints and effort."""

        complexity = tier_result.complexity
        target_tier = tier_result.model_tier
        level = effort_level or self._effort.current_level

        # Budget-aware tier downgrade
        if self.budget.should_downgrade_tier(target_tier):
            original_tier = target_tier
            fallback = self.providers.get_fallback_model(target_tier, self.budget.regime.value)
            if fallback:
                target_tier = fallback.tier
                logger.info(
                    "Budget downgrade: %s -> %s (regime=%s)",
                    original_tier.value,
                    target_tier.value,
                    self.budget.regime.value,
                )
                tier_result = TierResult(
                    complexity=complexity,
                    model_tier=target_tier,
                    confidence=tier_result.confidence * 0.9,
                    reasoning=(
                        f"{tier_result.reasoning} (downgraded from {original_tier.value}"
                        f" for budget)"
                    ),
                    matched_rule=tier_result.matched_rule,
                )

        # Select the best model at the target tier
        model = self.providers.get_best_model_for_tier(target_tier)
        if model is None:
            # No model available at this tier — try fallback
            model = self.providers.get_fallback_model(target_tier)
        if model is None:
            # Ultimate fallback: pick any available model
            model = self._pick_any_model()

        cost_estimate = get_cost_estimate(complexity)

        # ── Attach effort mapping ─────────────────────────────
        effort_mapping = self._effort.map_effort(level, provider=model.provider)

        return RoutingDecision(
            model=model.model_name,
            tier=target_tier,
            complexity=complexity,
            confidence=tier_result.confidence,
            reasoning=tier_result.reasoning,
            cost_estimate_usd=cost_estimate,
            tier_used=tier_used,
            budget_regime=self.budget.regime,
            effort_level=level.value,
            effort_budget_tokens=effort_mapping.budget_tokens,
            effort_instruction=effort_mapping.thinking_instruction,
            effort_reasoning=effort_mapping.reasoning_effort,
        )

    def _pick_any_model(self) -> ModelAssignment:
        """Pick any available model as a last-resort fallback."""
        for tier in ModelTier:
            model = self.providers.get_best_model_for_tier(tier, require_key=False)
            if model:
                return model
        # Should never happen — providers are pre-configured
        return ModelAssignment(
            model_name="claude-haiku-4-20250514",
            provider="anthropic",
            cost_per_1m_tokens=1.0,
            tier=ModelTier.HAIKU,
        )

    def _record_stats(self, decision: RoutingDecision, latency_ms: float) -> None:
        """Update internal statistics after a routing decision."""
        self._route_count += 1
        self._total_latency_ms += latency_ms
        self._total_cost += decision.cost_estimate_usd
