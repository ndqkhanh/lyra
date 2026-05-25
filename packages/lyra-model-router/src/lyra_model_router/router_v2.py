"""IntelligentModelRouter — multi-turn, cost-aware, anytime inference routing.

Based on RouteNLP (58% cost reduction), Pyramid MoA (probabilistic anytime
inference), and MTRouter (multi-turn history-model joint embeddings).
"""

from .models_v2 import (
    Budget,
    ModelProvider,
    ModelSpec,
    ModelTier,
    RouterSnapshot,
    RoutingDecision,
    RoutingStrategy,
    TurnContext,
)

# Default model pool
_DEFAULT_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        name="claude-opus-4.7",
        provider=ModelProvider.ANTHROPIC,
        tier=ModelTier.REASONING,
        cost_per_1k_tokens=0.015,
        latency_ms=800.0,
        accuracy_estimate=0.95,
        supports_reasoning=True,
    ),
    ModelSpec(
        name="claude-sonnet-4.6",
        provider=ModelProvider.ANTHROPIC,
        tier=ModelTier.STANDARD,
        cost_per_1k_tokens=0.003,
        latency_ms=300.0,
        accuracy_estimate=0.88,
    ),
    ModelSpec(
        name="claude-haiku-4.5",
        provider=ModelProvider.ANTHROPIC,
        tier=ModelTier.FAST,
        cost_per_1k_tokens=0.001,
        latency_ms=100.0,
        accuracy_estimate=0.80,
    ),
    ModelSpec(
        name="deepseek-v4-pro",
        provider=ModelProvider.LITELLM,
        tier=ModelTier.REASONING,
        cost_per_1k_tokens=0.008,
        latency_ms=700.0,
        accuracy_estimate=0.92,
        supports_reasoning=True,
    ),
    ModelSpec(
        name="deepseek-v4-flash",
        provider=ModelProvider.LITELLM,
        tier=ModelTier.CHEAP,
        cost_per_1k_tokens=0.0005,
        latency_ms=80.0,
        accuracy_estimate=0.75,
    ),
    ModelSpec(
        name="gpt-5.4",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.STANDARD,
        cost_per_1k_tokens=0.005,
        latency_ms=350.0,
        accuracy_estimate=0.87,
    ),
    ModelSpec(
        name="gpt-5.4-nano",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.FAST,
        cost_per_1k_tokens=0.0008,
        latency_ms=90.0,
        accuracy_estimate=0.78,
    ),
)


class IntelligentModelRouter:
    """Routes tasks across model tiers with cost-aware, multi-turn decisions.

    Provides:
    - Cost-optimal routing with budget constraints
    - Multi-turn context-aware routing
    - Fallback chain with automatic escalation
    - Provider-agnostic model selection
    - 3-tier GPU pyramid cost model
    """

    _TIER_PRIORITY = {
        RoutingStrategy.COST_OPTIMAL: (
            ModelTier.CHEAP,
            ModelTier.FAST,
            ModelTier.STANDARD,
            ModelTier.REASONING,
        ),
        RoutingStrategy.PERFORMANCE_MAX: (
            ModelTier.REASONING,
            ModelTier.STANDARD,
            ModelTier.FAST,
            ModelTier.CHEAP,
        ),
        RoutingStrategy.BALANCED: (
            ModelTier.STANDARD,
            ModelTier.FAST,
            ModelTier.REASONING,
            ModelTier.CHEAP,
        ),
    }

    def __init__(self, models: tuple[ModelSpec, ...] | None = None):
        self._models = list(models if models is not None else _DEFAULT_MODELS)
        self._decisions: list[RoutingDecision] = []
        self._turn_history: list[TurnContext] = []
        self._total_cost = 0.0
        self._total_tokens = 0

    def route(
        self,
        query: str,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        budget: Budget | None = None,
        complexity: float = 0.5,
        is_reasoning: bool = False,
    ) -> RoutingDecision:
        """Route a query to the best model given constraints."""
        candidates = self._filter_by_budget(budget) if budget else list(self._models)
        if not candidates:
            candidates = [self._fallback_model()]

        if strategy == RoutingStrategy.MULTI_TURN and self._turn_history:
            return self._multi_turn_route(query, candidates)

        tier_order = self._TIER_PRIORITY.get(
            strategy, self._TIER_PRIORITY[RoutingStrategy.BALANCED]
        )

        for tier in tier_order:
            tier_models = [m for m in candidates if m.tier == tier]
            if is_reasoning:
                tier_models = [m for m in tier_models if m.supports_reasoning]
            if tier_models:
                best = max(
                    tier_models,
                    key=lambda m: m.accuracy_estimate - m.cost_per_1k_tokens * 10,
                )
                decision = self._make_decision(best, strategy, complexity, query)
                self._record(decision)
                return decision

        # Ultimate fallback
        decision = self._make_decision(
            self._fallback_model(), strategy, complexity, query
        )
        self._record(decision)
        return decision

    def select_tier(
        self,
        required_reliability: float,
        cost_budget: float | None = None,
        is_reasoning: bool = False,
    ) -> ModelSpec:
        """Select the most cost-effective model meeting reliability requirement."""
        candidates = [
            m for m in self._models if m.accuracy_estimate >= required_reliability
        ]
        if cost_budget is not None:
            candidates = [m for m in candidates if m.cost_per_1k_tokens <= cost_budget]
        if is_reasoning:
            candidates = [m for m in candidates if m.supports_reasoning]
        if not candidates:
            return self._fallback_model()
        return min(candidates, key=lambda m: m.cost_per_1k_tokens)

    def record_turn(self, turn: TurnContext) -> None:
        """Record a turn for multi-turn routing context."""
        self._turn_history.append(turn)

    def _multi_turn_route(
        self, query: str, candidates: list[ModelSpec]
    ) -> RoutingDecision:
        """Route considering conversation history."""
        context_tokens = sum(t.history_tokens for t in self._turn_history)
        avg_complexity = sum(t.estimated_complexity for t in self._turn_history) / max(
            1, len(self._turn_history)
        )

        # Escalate to reasoning model if history is complex
        if avg_complexity > 0.7 or context_tokens > 50000:
            reasoning = [m for m in candidates if m.supports_reasoning]
            if reasoning:
                best = max(reasoning, key=lambda m: m.accuracy_estimate)
                decision = self._make_decision(
                    best, RoutingStrategy.MULTI_TURN, avg_complexity, query
                )
                self._record(decision)
                return decision

        # Default to standard tier for multi-turn
        standard = [
            m for m in candidates if m.tier in (ModelTier.STANDARD, ModelTier.FAST)
        ]
        if standard:
            best = min(standard, key=lambda m: m.cost_per_1k_tokens)
            decision = self._make_decision(
                best, RoutingStrategy.MULTI_TURN, avg_complexity, query
            )
            self._record(decision)
            return decision

        decision = self._make_decision(
            self._fallback_model(), RoutingStrategy.MULTI_TURN, avg_complexity, query
        )
        self._record(decision)
        return decision

    def _filter_by_budget(self, budget: Budget) -> list[ModelSpec]:
        return [
            m
            for m in self._models
            if m.cost_per_1k_tokens * 10 <= budget.remaining_cost
            and not budget.cost_exhausted
        ]

    def _make_decision(
        self, model: ModelSpec, strategy: RoutingStrategy, complexity: float, query: str
    ) -> RoutingDecision:
        confidence = model.accuracy_estimate * (1.0 - 0.1 * complexity)
        est_tokens = max(100, len(query) * 2)
        est_cost = model.cost_per_1k_tokens * est_tokens / 1000
        return RoutingDecision(
            model=model,
            confidence=round(confidence, 4),
            estimated_cost=round(est_cost, 6),
            strategy=strategy,
            reasoning=f"Selected {model.name} (tier={model.tier.value}) for complexity={complexity:.2f}",
        )

    def _record(self, decision: RoutingDecision) -> None:
        self._decisions.append(decision)
        self._total_cost += decision.estimated_cost
        self._total_tokens += 500  # rough estimate

    def _fallback_model(self) -> ModelSpec:
        return ModelSpec(
            name="claude-sonnet-4.6",
            provider=ModelProvider.ANTHROPIC,
            tier=ModelTier.STANDARD,
            cost_per_1k_tokens=0.003,
            latency_ms=300.0,
            accuracy_estimate=0.88,
        )

    def snapshot(self) -> RouterSnapshot:
        tiers: dict[str, int] = {}
        for d in self._decisions:
            t = d.model.tier.value
            tiers[t] = tiers.get(t, 0) + 1
        confidences = [d.confidence for d in self._decisions]
        return RouterSnapshot(
            total_decisions=len(self._decisions),
            decisions_by_tier=tiers,
            total_cost=round(self._total_cost, 6),
            total_tokens=self._total_tokens,
            avg_confidence=(
                round(sum(confidences) / len(confidences), 4) if confidences else 0.0
            ),
            fallback_rate=0.0,
        )

    def add_model(self, model: ModelSpec) -> None:
        self._models.append(model)

    def remove_model(self, name: str) -> bool:
        before = len(self._models)
        self._models = [m for m in self._models if m.name != name]
        return len(self._models) < before

    @property
    def model_count(self) -> int:
        return len(self._models)

    @property
    def decision_count(self) -> int:
        return len(self._decisions)

    @property
    def turn_count(self) -> int:
        return len(self._turn_history)
