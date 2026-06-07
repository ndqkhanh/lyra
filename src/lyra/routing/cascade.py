"""
Cost-sensitive cascade router that extends ``ModelRouter``.

Routes tasks from cheapest to most expensive model, escalating on failure
or low-confidence responses. Tracks per-model outcome statistics to
inform future routing decisions.

Enhancements in v8.1
--------------------
- ``ConfidenceEstimator``: Multi-signal confidence detection (length
  anomaly, refusal patterns, inconsistency heuristics).
- ``EscalationDecision``: Encapsulates the decision to escalate —
  which model was tried, why escalation occurred, which tier to try next.
- ``CascadeStats``: Per-model success rate, average cost, average
  latency aggregated across all recorded outcomes.
- ``auto_tune()``: Adjusts ``confidence_threshold`` per model based on
  accumulated outcome data.
"""

from __future__ import annotations

import re
import structlog
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from lyra.routing.difficulty import DifficultyEstimator
from lyra.routing.provider.config import RouterConfig
from lyra.routing.provider.router import ModelRouter, _MODEL_TIERS, _select_model_tier
from lyra.routing.provider.types import (
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    RouteContext,
    RouteDecision,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# CascadeConfig
# ---------------------------------------------------------------------------


@dataclass
class CascadeConfig:
    """Configuration for cost-sensitive cascade routing.

    Attributes:
        max_budget: Maximum total cost per request in USD. Candidates whose
            estimated cost exceeds this are skipped.
        confidence_threshold: Minimum confidence (0.0-1.0) to accept a
            response without escalation. Only used when
            ``escalation_policy`` is ``"confidence"``.
        escalation_policy: Controls when to escalate to the next tier.
            ``"always"`` — cascade unconditionally through all tiers in
            cost order. ``"confidence"`` — cascade only when the response
            is below ``confidence_threshold``. ``"difficulty"`` — route
            directly to the tier matched to the estimated difficulty,
            bypassing cheaper models for hard tasks.
        max_cascade_depth: Maximum number of models to try before raising
            ``RuntimeError``.
    """

    max_budget: float = 10.0
    confidence_threshold: float = 0.7
    escalation_policy: str = "always"
    max_cascade_depth: int = 3


# ---------------------------------------------------------------------------
# OutcomeStats
# ---------------------------------------------------------------------------


@dataclass
class OutcomeStats:
    """Per-model outcome statistics collected by the cascade router.

    Attributes:
        success_count: Number of successful completions.
        failure_count: Number of failed completions.
        total_latency_ms: Sum of all recorded latencies for this model.
    """

    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0

    @property
    def total_calls(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_count / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls


# ---------------------------------------------------------------------------
# ConfidenceEstimator
# ---------------------------------------------------------------------------


@dataclass
class ConfidenceEstimator:
    """Multi-signal confidence detector for LLM responses.

    Combines several heuristics:

    1. **Length anomaly**: Very short responses (< 5 tokens) suggest refusal.
    2. **Refusal patterns**: Responses containing phrases like "I cannot",
       "I'm unable", "I am not able", "I don't have" suggest low confidence.
    3. **Inconsistency signals**: Responses that contain self-contradictory
       patterns (e.g. "on one hand... on the other hand") may indicate
       uncertainty.

    The final confidence is the minimum of all signal scores (conservative).
    """

    # Phrases that signal a refusal / low-confidence response
    _REFUSAL_PATTERNS: tuple[str, ...] = (
        r"\bI cannot\b",
        r"\bI('m| am) unable\b",
        r"\bI am not able\b",
        r"\bI don'?t have\b",
        r"\bI('m| am) not sure\b",
        r"\bI('m| am) not certain\b",
        r"\bI apologize\b",
        r"\bsorry[,:]?\s+I",
    )

    # Phrases that suggest hedging / inconsistency
    _INCONSISTENCY_PATTERNS: tuple[str, ...] = (
        r"\bon the one hand\b",
        r"\bon the other hand\b",
        r"\bhowever[,:].*?however\b",
        r"\bits worth noting\b.*?\bbut\b",
    )

    # Minimum output length that avoids the "length anomaly" penalty
    min_expected_tokens: int = 10
    # Penalty applied when a refusal pattern is detected
    refusal_penalty: float = 0.4
    # Penalty applied when inconsistency is detected
    inconsistency_penalty: float = 0.25

    def estimate(self, response: CompletionResponse) -> float:
        """Return a confidence score in [0.0, 1.0].

        Args:
            response: The completion response to evaluate.

        Returns:
            Confidence estimate (0.0 = no confidence, 1.0 = full confidence).
        """
        scores: list[float] = []

        # 1. Length anomaly signal
        scores.append(self._score_length(response))

        # 2. Refusal pattern signal
        scores.append(self._score_refusal(response))

        # 3. Inconsistency signal
        scores.append(self._score_inconsistency(response))

        # Conservative: take the minimum of all signals
        return min(scores)

    def _score_length(self, response: CompletionResponse) -> float:
        """Score based on response length. Short -> low score."""
        output_tokens = response.usage.output_tokens if response.usage else (
            len(response.content) // 4
        )
        if output_tokens == 0:
            return 0.0
        if output_tokens < 5:
            return 0.3
        if output_tokens < self.min_expected_tokens:
            return 0.5
        return 1.0

    def _score_refusal(self, response: CompletionResponse) -> float:
        """Score based on refusal pattern detection."""
        content = response.content
        for pattern in self._REFUSAL_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return 1.0 - self.refusal_penalty
        return 1.0

    def _score_inconsistency(self, response: CompletionResponse) -> float:
        """Score based on inconsistency / hedging detection."""
        content = response.content
        for pattern in self._INCONSISTENCY_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return 1.0 - self.inconsistency_penalty
        return 1.0


# ---------------------------------------------------------------------------
# EscalationDecision
# ---------------------------------------------------------------------------


@dataclass
class EscalationDecision:
    """Encapsulates a cascade escalation decision.

    Attributes:
        model_tried:  The model identifier that was attempted.
        reason:       Why escalation occurred (e.g. "failure", "low_confidence").
        confidence:   Confidence score of the response (if applicable).
        next_tier:    Which tier to try next (e.g. "smart", "premium").
        next_model:   The model identifier at the next tier.
        estimated_next_cost: Estimated cost of the next tier attempt.
    """

    model_tried: str
    reason: str
    confidence: float | None = None
    next_tier: str | None = None
    next_model: str | None = None
    estimated_next_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_tried": self.model_tried,
            "reason": self.reason,
            "confidence": self.confidence,
            "next_tier": self.next_tier,
            "next_model": self.next_model,
            "estimated_next_cost": self.estimated_next_cost,
        }


# ---------------------------------------------------------------------------
# CascadeStats
# ---------------------------------------------------------------------------


@dataclass
class CascadeStats:
    """Aggregate cascade statistics across all models.

    Provides summary metrics useful for monitoring and auto-tuning.

    Attributes:
        total_requests:   Total number of routing requests.
        successful_routes: Number of requests that completed successfully.
        failed_routes:    Number of requests that exhausted all candidates.
        total_cost:       Cumulative cost across all requests in USD.
        total_latency_ms: Cumulative latency across all requests.
        per_model:        Per-model ``OutcomeStats`` dict.
    """

    total_requests: int = 0
    successful_routes: int = 0
    failed_routes: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    per_model: dict[str, OutcomeStats] = field(default_factory=dict)

    @property
    def overall_success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_routes / self.total_requests

    @property
    def avg_cost_per_request(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_cost / self.total_requests

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_routes": self.successful_routes,
            "failed_routes": self.failed_routes,
            "overall_success_rate": self.overall_success_rate,
            "total_cost": round(self.total_cost, 4),
            "avg_cost_per_request": round(self.avg_cost_per_request, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "per_model": {
                k: {
                    "success_count": v.success_count,
                    "failure_count": v.failure_count,
                    "success_rate": v.success_rate,
                    "avg_latency_ms": v.avg_latency_ms,
                }
                for k, v in self.per_model.items()
            },
        }


# ---------------------------------------------------------------------------
# Internal: cost-ordered candidate builder
# ---------------------------------------------------------------------------

_CASCADE_TIERS: tuple[str, str, str] = ("fast", "smart", "premium")


def _build_cascade_candidates(
    provider_registry: dict[str, Any],
    context: RouteContext | None,
) -> list[tuple[str, str, EffortLevel, float]]:
    """Build a list of ``(provider, model, effort, estimated_cost)`` sorted
    cheapest-first.

    Iterates over all registered providers and for each creates up to three
    tier entries (fast, smart, premium). Entries are sorted by estimated
    cost ascending.
    """
    candidates: list[tuple[str, str, EffortLevel, float]] = []
    provider_names = list(provider_registry.keys())

    for prov in provider_names:
        backend = provider_registry[prov]
        for tier_tag in _CASCADE_TIERS:
            model = _select_model_tier_for_cascade(prov, tier_tag)
            effort = _tier_to_effort(tier_tag)
            request_stub = CompletionRequest(
                messages=(),
                model=model,
                effort=effort,
            )
            estimate = backend.cost_estimate(request_stub)
            cost = estimate.total_max_cost
            candidates.append((prov, model, effort, cost))

    # Sort by cost — cheapest first; tie-break by registration order
    candidates.sort(key=lambda x: (x[3], provider_names.index(x[0])))
    return candidates


def _select_model_tier_for_cascade(provider_name: str, tier: str) -> str:
    """Look up the model name for a given provider and cascade tier."""
    tiers = _MODEL_TIERS.get(provider_name, _MODEL_TIERS.get("anthropic", {}))
    return tiers.get(tier, tiers.get("smart", "claude-sonnet-4-6"))


def _tier_to_effort(tier: str) -> EffortLevel:
    mapping = {
        "fast": EffortLevel.LOW,
        "smart": EffortLevel.MEDIUM,
        "premium": EffortLevel.HIGH,
    }
    return mapping.get(tier, EffortLevel.MEDIUM)


# ---------------------------------------------------------------------------
# CascadeRouter
# ---------------------------------------------------------------------------


class CascadeRouter(ModelRouter):
    """Cost-sensitive cascade router.

    Extends ``ModelRouter`` by adding cost-aware escalation: routes from
    cheapest to most expensive model, skipping cost-prohibitive candidates
    and tracking per-model outcome statistics.

    Usage::

        router = CascadeRouter(cascade_config=CascadeConfig(max_budget=5.0))
        router.register_provider("anthropic", adapter, models)
        response = await router.route_with_cost(request, budget=5.0)
    """

    def __init__(
        self,
        config: RouterConfig | None = None,
        cascade_config: CascadeConfig | None = None,
    ) -> None:
        super().__init__(config=config)
        self._cascade_config = cascade_config or CascadeConfig()
        self._difficulty_estimator = DifficultyEstimator()
        # model -> OutcomeStats  (keyed by ``"provider/model"``)
        self._outcomes: dict[str, OutcomeStats] = {}

        # --- v8.1 additions ---
        self._confidence_estimator = ConfidenceEstimator()
        self._cascade_stats = CascadeStats()
        # Per-model auto-tuned confidence thresholds
        self._auto_tuned_thresholds: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Cascade routing
    # ------------------------------------------------------------------

    async def route_with_cost(
        self,
        request: CompletionRequest,
        context: RouteContext | None = None,
        budget: float | None = None,
    ) -> CompletionResponse:
        """Execute a completion with cost-sensitive cascade escalation.

        The router builds a candidate list of provider/model combinations
        ordered by increasing estimated cost. It tries each candidate in
        order, escalating when:

        - The provider raises an exception (failure).
        - ``escalation_policy == "confidence"`` and the estimated
          confidence of the response is below the threshold.
        - ``escalation_policy == "always"`` (the default), which cascades
          unconditionally through ``max_cascade_depth`` tiers.

        Args:
            request: The completion request to execute.
            context: Optional routing context. If not provided, a default
                ``RouteContext`` with ``task_type="standard"`` is used.
            budget: Optional per-request budget override in USD. If unset,
                ``CascadeConfig.max_budget`` is used.

        Returns:
            A ``CompletionResponse`` from the first satisfying model.

        Raises:
            RuntimeError: If all cascade candidates fail or are skipped.
        """
        ctx = context or RouteContext()
        task_type = ctx.task_type
        max_budget = budget if budget is not None else self._cascade_config.max_budget

        candidates = _build_cascade_candidates(
            self._providers,
            ctx,
        )

        # Filter by budget
        affordable: list[tuple[str, str, EffortLevel, float]] = []
        for prov, model, effort, cost in candidates:
            if cost <= max_budget or max_budget <= 0.0:
                affordable.append((prov, model, effort, cost))

        if not affordable:
            raise RuntimeError(
                f"No affordable models found within budget ${max_budget:.2f}",
            )

        # When escalation_policy == "difficulty", jump to the appropriate
        # tier instead of always starting at the cheapest.
        if self._cascade_config.escalation_policy == "difficulty":
            difficulty_float = self.estimate_difficulty(
                task_type,
                request.messages,
            )
            start_index = _difficulty_to_start_index(difficulty_float, len(affordable))
            affordable = affordable[start_index:]

        # Clamp to max_cascade_depth
        depth = self._cascade_config.max_cascade_depth
        candidates_to_try = affordable[:depth]

        errors: list[str] = []
        total_request_cost: float = 0.0
        self._cascade_stats.total_requests += 1

        for idx, (prov, model, effort, cost) in enumerate(candidates_to_try):
            provider = self._providers.get(prov)
            if provider is None:
                errors.append(f"provider '{prov}' not registered")
                continue

            provider_request = CompletionRequest(
                messages=request.messages,
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                tools=request.tools,
                effort=effort,
            )

            try:
                response = await provider.complete(provider_request)

                # Track outcome
                latency = response.latency_ms
                model_key = f"{prov}/{model}"
                self.record_outcome(model_key, task_type, success=True, latency=latency)

                # Track session cost
                if response.usage:
                    estimate = provider.cost_estimate(provider_request)
                    self._session_cost += estimate.total_max_cost
                    total_request_cost += estimate.total_max_cost

                logger.info(
                    "cascade succeeded",
                    provider=prov,
                    model=model,
                    effort=effort.value,
                    latency_ms=latency,
                    estimated_cost=cost,
                    cascade_index=idx,
                )

                # For "confidence" policy, check if we need to escalate.
                # v8.1: use ConfidenceEstimator instead of _estimate_response_confidence.
                if self._cascade_config.escalation_policy == "confidence":
                    confidence = self._confidence_estimator.estimate(response)
                    # Use auto-tuned threshold if available, otherwise config default
                    effective_threshold = self._auto_tuned_thresholds.get(
                        model_key,
                        self._cascade_config.confidence_threshold,
                    )
                    if confidence < effective_threshold:
                        logger.info(
                            "cascading due to low response confidence",
                            provider=prov,
                            model=model,
                            confidence=round(confidence, 2),
                            threshold=effective_threshold,
                        )
                        errors.append(
                            f"{prov}/{model}: low confidence ({confidence:.2f})",
                        )
                        continue

                # Track CascadeStats on success
                self._cascade_stats.successful_routes += 1
                self._cascade_stats.total_cost += total_request_cost
                self._cascade_stats.total_latency_ms += latency

                return response

            except Exception as exc:
                error_msg = f"{prov}/{model}: {exc}"
                errors.append(error_msg)
                model_key = f"{prov}/{model}"
                self.record_outcome(model_key, task_type, success=False, latency=0.0)
                logger.warning(
                    "cascade candidate failed, escalating",
                    error=error_msg,
                    cascade_index=idx,
                )
                continue

        self._cascade_stats.failed_routes += 1
        raise RuntimeError(
            f"Cascade exhausted. Errors: {'; '.join(errors)}",
        )

    # ------------------------------------------------------------------
    # Difficulty estimation
    # ------------------------------------------------------------------

    def estimate_difficulty(
        self,
        task_type: str,
        messages: tuple[Message, ...] | None = None,
    ) -> float:
        """Estimate task difficulty as a 0.0 (simple) to 1.0 (very complex) score.

        Args:
            task_type: The task type identifier (e.g. ``"complex_reasoning"``).
            messages: Optional conversation messages for content-based heuristics.

        Returns:
            A float in [0.0, 1.0] representing estimated difficulty.
        """
        score = self._difficulty_estimator.estimate(task_type, messages)
        return self._difficulty_estimator.to_float(score)

    # ------------------------------------------------------------------
    # Outcome recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        model: str,
        task_type: str,
        success: bool,
        latency: float,
    ) -> None:
        """Record a model outcome for routing statistics.

        Args:
            model: Model identifier in the form ``"provider/model"``.
            task_type: The task type that was attempted.
            success: Whether the completion succeeded.
            latency: Latency of the completion in milliseconds.
        """
        stats = self._outcomes.setdefault(model, OutcomeStats())
        if success:
            stats.success_count += 1
        else:
            stats.failure_count += 1
        stats.total_latency_ms += latency

        # Sync CascadeStats per-model
        self._cascade_stats.per_model[model] = stats

        logger.debug(
            "outcome recorded",
            model=model,
            task_type=task_type,
            success=success,
            latency_ms=latency,
            success_rate=round(stats.success_rate, 2),
        )

    def get_model_stats(self) -> dict[str, OutcomeStats]:
        """Return per-model success rates and statistics.

        Returns:
            A dict mapping model identifier (``"provider/model"``) to
            ``OutcomeStats``.
        """
        return dict(self._outcomes)

    # ------------------------------------------------------------------
    # v8.1 — CascadeStats, auto-tuning
    # ------------------------------------------------------------------

    def get_cascade_stats(self) -> CascadeStats:
        """Return aggregate cascade routing statistics.

        Returns:
            A :class:`CascadeStats` instance with summary metrics.
        """
        return self._cascade_stats

    def auto_tune(self) -> dict[str, float]:
        """Auto-tune confidence thresholds per model based on outcome data.

        For each model with sufficient outcome data:
        - If the model has a high success rate, the threshold is loosened
          (lowered) so more responses are accepted.
        - If the model has a low success rate, the threshold is tightened
          (raised) so only high-confidence responses pass.

        Returns:
            Dict of ``model_key -> tuned_threshold`` for models that
            were updated.
        """
        tuned: dict[str, float] = {}
        base_threshold = self._cascade_config.confidence_threshold

        for model_key, stats in self._outcomes.items():
            if stats.total_calls < 5:
                continue  # not enough data to tune

            sr = stats.success_rate
            if sr >= 0.9:
                # Very reliable model: loosen threshold (accept more)
                new_threshold = max(0.3, base_threshold - 0.15)
            elif sr >= 0.7:
                # Moderately reliable: nudge slightly
                new_threshold = max(0.3, base_threshold - 0.05)
            elif sr >= 0.5:
                new_threshold = min(0.95, base_threshold + 0.1)
            else:
                # Unreliable model: tighten threshold
                new_threshold = min(0.95, base_threshold + 0.2)

            self._auto_tuned_thresholds[model_key] = new_threshold
            tuned[model_key] = new_threshold

        return tuned

    def get_effective_threshold(self, model_key: str) -> float:
        """Return the effective confidence threshold for a model.

        Returns the auto-tuned threshold if one exists, otherwise
        the config default.

        Args:
            model_key: Model identifier (``"provider/model"``).

        Returns:
            Confidence threshold in [0.0, 1.0].
        """
        return self._auto_tuned_thresholds.get(
            model_key,
            self._cascade_config.confidence_threshold,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _estimate_response_confidence(response: CompletionResponse) -> float:
    """Heuristic confidence estimate for a response (0.0-1.0).

    Uses a simple token-based heuristic: a very short response may indicate
    low confidence. Real implementations could use logprobs or semantic
    analysis.
    """
    output_tokens = response.usage.output_tokens if response.usage else 0
    if output_tokens == 0:
        return 0.0
    # Responses under 5 tokens suggest refusal / uncertainty
    if output_tokens < 5:
        return 0.3
    if output_tokens < 20:
        return 0.5
    return 0.85


def _difficulty_to_start_index(difficulty: float, num_candidates: int) -> int:
    """Map a difficulty float to a start index into the ordered candidate list.

    Simple tasks (0.0-0.2) start at index 0 (cheapest).
    Moderate tasks (0.2-0.5) start at index 1 (skip the very cheapest).
    Complex tasks (0.5-0.8) start at index 2.
    Very complex tasks (0.8-1.0) start at index 3, or the last affordable.
    """
    if difficulty >= 0.8:
        return min(3, num_candidates - 1) if num_candidates > 0 else 0
    if difficulty >= 0.5:
        return min(2, num_candidates - 1)
    if difficulty >= 0.2:
        return min(1, num_candidates - 1)
    return 0


__all__ = [
    "CascadeConfig",
    "CascadeRouter",
    "CascadeStats",
    "ConfidenceEstimator",
    "EscalationDecision",
    "OutcomeStats",
]
