"""Confidence-thresholded escalation with provider fallback chains.

Plan 10 Layer 3-5 integration: When a routing decision falls below the
confidence threshold (default 0.75), automatically escalates through
the fallback chain: same-tier alternatives → next tier up → cross-provider
fallback → ultimate default.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from .models_v2 import ModelProvider, ModelSpec, ModelTier, RoutingDecision, RoutingStrategy


class EscalationReason(Enum):
    """Why escalation was triggered."""

    LOW_CONFIDENCE = "low_confidence"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    COST_EXCEEDED = "cost_exceeded"
    PERFORMANCE_DEGRADED = "performance_degraded"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class EscalationStep:
    """A single step in an escalation chain.

    Attributes:
        model: The model attempted.
        reason: Why this step was reached.
        confidence: Confidence at this step.
        outcome: What happened (accepted / escalated / failed).
        latency_ms: Time spent at this step.
    """

    model: ModelSpec
    reason: EscalationReason
    confidence: float
    outcome: str
    latency_ms: float = 0.0


@dataclass(frozen=True)
class EscalationResult:
    """Final result of an escalation chain.

    Attributes:
        final_decision: The accepted routing decision, or None if all failed.
        steps: Ordered list of escalation steps taken.
        total_latency_ms: Cumulative latency across all steps.
        escalated: Whether escalation occurred (vs first pick accepted).
    """

    final_decision: RoutingDecision | None
    steps: tuple[EscalationStep, ...]
    total_latency_ms: float
    escalated: bool


@dataclass
class ProviderHealth:
    """Tracked health state for a model provider.

    Attributes:
        provider: Provider identifier.
        consecutive_failures: Recent failure count.
        last_failure: Timestamp of last failure.
        is_degraded: Whether the provider is in degraded mode.
        degraded_since: When degradation started.
        success_rate: Rolling success rate 0.0-1.0.
    """

    provider: ModelProvider
    consecutive_failures: int = 0
    last_failure: float = 0.0
    is_degraded: bool = False
    degraded_since: float = 0.0
    success_rate: float = 1.0

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.is_degraded = False
        self.success_rate = min(1.0, self.success_rate + 0.02)

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure = time.time()
        self.success_rate = max(0.0, self.success_rate - 0.05)
        if self.consecutive_failures >= 3:
            self.is_degraded = True
            self.degraded_since = time.time()


# Tier escalation order — cheaper tier first, then upward
_TIER_ESCALATION: tuple[ModelTier, ...] = (
    ModelTier.CHEAP,
    ModelTier.FAST,
    ModelTier.STANDARD,
    ModelTier.REASONING,
)

# Cross-provider fallback priority per provider
_CROSS_PROVIDER_FALLBACK: dict[ModelProvider, tuple[ModelProvider, ...]] = {
    ModelProvider.ANTHROPIC: (ModelProvider.LITELLM, ModelProvider.OPENAI, ModelProvider.GOOGLE),
    ModelProvider.OPENAI: (ModelProvider.ANTHROPIC, ModelProvider.LITELLM, ModelProvider.GOOGLE),
    ModelProvider.GOOGLE: (ModelProvider.ANTHROPIC, ModelProvider.OPENAI, ModelProvider.LITELLM),
    ModelProvider.LITELLM: (ModelProvider.ANTHROPIC, ModelProvider.OPENAI, ModelProvider.GOOGLE),
    ModelProvider.BEDROCK: (ModelProvider.ANTHROPIC, ModelProvider.LITELLM, ModelProvider.OPENAI),
    ModelProvider.OPENROUTER: (
        ModelProvider.ANTHROPIC,
        ModelProvider.LITELLM,
        ModelProvider.OPENAI,
    ),
}


class ConfidenceEscalator:
    """Manages confidence-thresholded escalation across model tiers and providers.

    When a routing decision falls below the confidence threshold:
    1. Try same-tier alternatives from different providers
    2. Escalate to next tier up
    3. Cross-provider fallback
    4. Ultimate fallback to default model
    """

    def __init__(
        self,
        confidence_threshold: float = 0.75,
        max_escalation_steps: int = 5,
        degrade_after_failures: int = 3,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.max_escalation_steps = max_escalation_steps
        self.degrade_after_failures = degrade_after_failures
        self._provider_health: dict[ModelProvider, ProviderHealth] = {}

    def should_escalate(self, decision: RoutingDecision) -> bool:
        """Check if a routing decision should be escalated."""
        if decision.confidence < self.confidence_threshold:
            return True
        provider_health = self._get_health(decision.model.provider)
        return provider_health.is_degraded

    def escalate(
        self,
        original_decision: RoutingDecision,
        available_models: list[ModelSpec],
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ) -> EscalationResult:
        """Execute the escalation chain starting from original_decision.

        Returns the first acceptable alternative or the original if none found.
        """
        steps: list[EscalationStep] = []
        t0 = time.time()

        # Step 0: Check if original is acceptable
        if not self.should_escalate(original_decision):
            return EscalationResult(
                final_decision=original_decision,
                steps=(),
                total_latency_ms=0.0,
                escalated=False,
            )

        # Record that we needed to escalate
        steps.append(
            EscalationStep(
                model=original_decision.model,
                reason=EscalationReason.LOW_CONFIDENCE,
                confidence=original_decision.confidence,
                outcome="escalated",
            )
        )

        # Step 1: Same-tier, different provider
        same_tier_alt = self._find_same_tier_alternatives(original_decision.model, available_models)
        for alt in same_tier_alt[:3]:
            if len(steps) >= self.max_escalation_steps:
                break
            alt_decision = self._evaluate_alternative(alt, original_decision, strategy)
            if alt_decision.confidence >= self.confidence_threshold:
                steps.append(
                    EscalationStep(
                        model=alt,
                        reason=EscalationReason.LOW_CONFIDENCE,
                        confidence=alt_decision.confidence,
                        outcome="accepted",
                    )
                )
                return EscalationResult(
                    final_decision=alt_decision,
                    steps=tuple(steps),
                    total_latency_ms=(time.time() - t0) * 1000,
                    escalated=True,
                )
            steps.append(
                EscalationStep(
                    model=alt,
                    reason=EscalationReason.LOW_CONFIDENCE,
                    confidence=alt_decision.confidence,
                    outcome="escalated",
                )
            )

        # Step 2: Escalate to next tier up
        tier_idx = _TIER_ESCALATION.index(original_decision.model.tier)
        for next_tier_idx in range(tier_idx + 1, len(_TIER_ESCALATION)):
            if len(steps) >= self.max_escalation_steps:
                break
            next_tier = _TIER_ESCALATION[next_tier_idx]
            tier_models = [m for m in available_models if m.tier == next_tier]
            tier_models.sort(key=lambda m: m.cost_per_1k_tokens)

            for model in tier_models[:2]:
                alt_decision = self._evaluate_alternative(model, original_decision, strategy)
                if alt_decision.confidence >= self.confidence_threshold:
                    steps.append(
                        EscalationStep(
                            model=model,
                            reason=EscalationReason.LOW_CONFIDENCE,
                            confidence=alt_decision.confidence,
                            outcome="accepted",
                        )
                    )
                    return EscalationResult(
                        final_decision=alt_decision,
                        steps=tuple(steps),
                        total_latency_ms=(time.time() - t0) * 1000,
                        escalated=True,
                    )
                steps.append(
                    EscalationStep(
                        model=model,
                        reason=EscalationReason.LOW_CONFIDENCE,
                        confidence=alt_decision.confidence,
                        outcome="escalated",
                    )
                )

        # Step 3: Cross-provider fallback
        fallback_providers = _CROSS_PROVIDER_FALLBACK.get(original_decision.model.provider, ())
        for provider in fallback_providers:
            if len(steps) >= self.max_escalation_steps:
                break
            provider_models = [
                m
                for m in available_models
                if m.provider == provider and m.tier in (ModelTier.STANDARD, ModelTier.REASONING)
            ]
            provider_models.sort(key=lambda m: m.cost_per_1k_tokens)
            for model in provider_models[:1]:
                alt_decision = self._evaluate_alternative(model, original_decision, strategy)
                if alt_decision.confidence >= self.confidence_threshold - 0.1:
                    steps.append(
                        EscalationStep(
                            model=model,
                            reason=EscalationReason.PERFORMANCE_DEGRADED,
                            confidence=alt_decision.confidence,
                            outcome="accepted",
                        )
                    )
                    return EscalationResult(
                        final_decision=alt_decision,
                        steps=tuple(steps),
                        total_latency_ms=(time.time() - t0) * 1000,
                        escalated=True,
                    )

        # Step 4: Ultimate fallback — accept the original
        total_ms = (time.time() - t0) * 1000
        return EscalationResult(
            final_decision=original_decision,
            steps=tuple(steps),
            total_latency_ms=total_ms,
            escalated=True,
        )

    def record_success(self, provider: ModelProvider) -> None:
        """Record a successful call for provider health tracking."""
        self._get_health(provider).record_success()

    def record_failure(self, provider: ModelProvider) -> None:
        """Record a failed call for provider health tracking."""
        health = self._get_health(provider)
        health.record_failure()
        if health.consecutive_failures >= self.degrade_after_failures:
            health.is_degraded = True
            health.degraded_since = time.time()

    def is_provider_healthy(self, provider: ModelProvider) -> bool:
        """Check if a provider is currently considered healthy."""
        return not self._get_health(provider).is_degraded

    def get_provider_health(self) -> dict[ModelProvider, ProviderHealth]:
        """Get health status for all tracked providers."""
        return dict(self._provider_health)

    def _get_health(self, provider: ModelProvider) -> ProviderHealth:
        if provider not in self._provider_health:
            self._provider_health[provider] = ProviderHealth(provider=provider)
        return self._provider_health[provider]

    @staticmethod
    def _find_same_tier_alternatives(
        original: ModelSpec, available: list[ModelSpec]
    ) -> list[ModelSpec]:
        """Find models in the same tier but from different providers."""
        return [m for m in available if m.tier == original.tier and m.provider != original.provider]

    @staticmethod
    def _evaluate_alternative(
        model: ModelSpec,
        original: RoutingDecision,
        strategy: RoutingStrategy,
    ) -> RoutingDecision:
        """Create a routing decision for an alternative model."""
        confidence = model.accuracy_estimate
        if strategy == RoutingStrategy.COST_OPTIMAL:
            # Slightly penalize more expensive alternatives in cost-optimal mode
            if model.cost_per_1k_tokens > original.model.cost_per_1k_tokens:
                confidence -= 0.05
        return RoutingDecision(
            model=model,
            confidence=round(confidence, 4),
            estimated_cost=model.cost_per_1k_tokens * 0.5,
            fallback_models=(),
            strategy=strategy,
            reasoning=f"Escalation alternative to {model.name} (tier={model.tier.value})",
        )
