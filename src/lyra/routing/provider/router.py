"""
Model router — routes tasks to the appropriate provider/model combination.

The router uses a simple task-type-to-effort-level mapping (v1).
A multi-head learned router is planned for Phase 2.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import Any

from lyra.routing.provider.base import ProviderBackend
from lyra.routing.provider.config import RouterConfig
from lyra.routing.provider.types import (
    Capability,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    ModelInfo,
    RouteContext,
    RouteDecision,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Task type → effort level mapping
# ---------------------------------------------------------------------------
_TASK_EFFORT_MAP: dict[str, EffortLevel] = {
    "simple_lookup": EffortLevel.LOW,
    "standard": EffortLevel.MEDIUM,
    "complex_reasoning": EffortLevel.HIGH,
    "research": EffortLevel.XHIGH,
    "code_generation": EffortLevel.MEDIUM,
    "code_review": EffortLevel.HIGH,
    "security_scan": EffortLevel.HIGH,
    "debugging": EffortLevel.HIGH,
    "agentic": EffortLevel.XHIGH,
}

# ---------------------------------------------------------------------------
# Model tiers — name patterns looked up per provider
# ---------------------------------------------------------------------------
_MODEL_TIERS: dict[str, dict[str, str]] = {
    "anthropic": {
        "fast": "claude-sonnet-4-6",  # LOW effort
        "smart": "claude-sonnet-4-6",  # MEDIUM effort
        "premium": "claude-opus-4-5",  # HIGH/XHIGH effort
    },
    "deepseek": {
        "fast": "deepseek-chat",
        "smart": "deepseek-chat",
        "premium": "deepseek-reasoner",
    },
    "openai": {
        "fast": "gpt-4o-mini",
        "smart": "gpt-4o",
        "premium": "o3",
    },
    "google": {
        "fast": "gemini-2-0-flash",
        "smart": "gemini-2-5-flash",
        "premium": "gemini-2-5-pro",
    },
}


def _resolve_effort(task_type: str, context: RouteContext | None) -> EffortLevel:
    """Map a task type to its effort level."""
    if context and context.estimated_complexity:
        complexity_map = {
            "low": EffortLevel.LOW,
            "medium": EffortLevel.MEDIUM,
            "high": EffortLevel.HIGH,
            "research": EffortLevel.XHIGH,
        }
        return complexity_map.get(context.estimated_complexity, EffortLevel.MEDIUM)
    return _TASK_EFFORT_MAP.get(task_type, EffortLevel.MEDIUM)


def _select_model_tier(
    effort: EffortLevel,
    provider_name: str,
) -> str:
    """Select the model name for *provider_name* at the given effort level."""
    tiers = _MODEL_TIERS.get(provider_name, _MODEL_TIERS.get("anthropic", {}))
    if effort in (EffortLevel.XHIGH, EffortLevel.MAX, EffortLevel.HIGH):
        return tiers.get("premium", tiers.get("smart", "claude-sonnet-4-6"))
    elif effort == EffortLevel.LOW:
        return tiers.get("fast", tiers.get("smart", "claude-sonnet-4-6"))
    return tiers.get("smart", "claude-sonnet-4-6")


def _build_fallback_chain(
    primary: RouteDecision,
    provider_registry: dict[str, tuple[ProviderBackend, list[ModelInfo]]],
    context: RouteContext | None,
    ordered_providers: tuple[str, ...] = ("anthropic", "deepseek", "openai", "google"),
) -> tuple[RouteDecision, ...]:
    """Build an ordered fallback chain starting from *primary*.

    Falls back through other registered providers in *ordered_providers* order,
    skipping the primary provider and any unregistered providers.

    Same-provider lower-effort fallbacks are not included — if the primary
    provider fails at HIGH effort it will likely fail at LOW effort too
    (same API, same endpoint). Crossing provider boundaries gives genuine
    independence.
    """
    chain: list[RouteDecision] = []

    # Walk the ordered list, skipping the primary and unregistered providers
    for prov in ordered_providers:
        if prov == primary.provider_name:
            continue
        if prov not in provider_registry:
            continue
        effort = primary.effort
        model = _select_model_tier(effort, prov)
        chain.append(
            RouteDecision(
                provider_name=prov,
                model=model,
                effort=effort,
                estimated_cost=CostEstimate(),
            ),
        )

    return tuple(chain)


class ModelRouter:
    """Routes tasks to the appropriate provider/model combination.

    Usage::

        router = ModelRouter()
        router.register_provider("anthropic", anthropic_adapter, model_infos)
        decision = router.route("complex_reasoning")
        response = await router.complete_with_fallback(request, context)
    """

    def __init__(self, config: RouterConfig | None = None) -> None:
        """Initialize the router.

        Args:
            config: Router configuration. Loaded from ``.lyra/settings.json``
                if not provided.
        """
        self._config = config or RouterConfig.from_settings()
        self._providers: dict[str, ProviderBackend] = {}
        self._models: dict[str, list[ModelInfo]] = {}
        self._session_cost: float = 0.0

    def register_provider(
        self,
        name: str,
        provider: ProviderBackend,
        models: list[ModelInfo],
    ) -> None:
        """Register a provider with the router.

        Args:
            name: Provider identifier (e.g. ``"anthropic"``).
            provider: The provider backend instance.
            models: List of ``ModelInfo`` for the models this provider offers.
        """
        self._providers[name] = provider
        self._models[name] = models
        logger.info("provider registered", name=name, model_count=len(models))

    def route(
        self,
        task_type: str,
        context: RouteContext | None = None,
    ) -> RouteDecision:
        """Route a task to a provider/model combination.

        Args:
            task_type: The type of task (e.g. ``"simple_lookup"``,
                ``"standard"``, ``"complex_reasoning"``, ``"research"``).
            context: Optional routing context for additional constraints.

        Returns:
            A ``RouteDecision`` with the selected provider, model, effort,
            and fallback chain.

        Raises:
            ValueError: If no providers are registered.
        """
        if not self._providers:
            raise ValueError("No providers registered with the router")

        effort = _resolve_effort(task_type, context)

        # Pick the best provider
        primary_provider = self._config.default_provider
        if primary_provider not in self._providers:
            # Fall back to the first registered provider
            primary_provider = next(iter(self._providers))

        model = _select_model_tier(effort, primary_provider)

        # Check capabilities
        if context:
            provider = self._providers[primary_provider]
            if context.requires_vision and not provider.supports(Capability.VISION):
                # Find a provider that supports vision
                for name, p in self._providers.items():
                    if p.supports(Capability.VISION):
                        primary_provider = name
                        model = _select_model_tier(effort, name)
                        break
            if context.requires_json_mode and not provider.supports(Capability.JSON_MODE):
                for name, p in self._providers.items():
                    if p.supports(Capability.JSON_MODE):
                        primary_provider = name
                        model = _select_model_tier(effort, name)
                        break

        provider = self._providers[primary_provider]
        cost = provider.cost_estimate(
            CompletionRequest(
                messages=(),
                model=model,
                effort=effort,
            ),
        )

        primary = RouteDecision(
            provider_name=primary_provider,
            model=model,
            effort=effort,
            estimated_cost=cost,
        )

        fallback_chain = _build_fallback_chain(primary, self._providers, context)

        return RouteDecision(
            provider_name=primary_provider,
            model=model,
            effort=effort,
            fallback_chain=fallback_chain,
            estimated_cost=cost,
        )

    async def complete_with_fallback(
        self,
        request: CompletionRequest,
        context: RouteContext | None = None,
    ) -> CompletionResponse:
        """Execute a completion request with automatic fallback.

        Args:
            request: The completion request to execute.
            context: Optional routing context.

        Returns:
            A ``CompletionResponse`` from the first successful provider/model.

        Raises:
            RuntimeError: If all providers in the chain fail.
        """
        # Determine the task type from context
        task_type = context.task_type if context else "standard"
        decision = self.route(task_type, context)

        # Build the ordered list of (provider_name, model, effort) to try
        candidates: list[tuple[str, str, EffortLevel]] = [
            (decision.provider_name, decision.model, decision.effort),
        ]
        for fallback in decision.fallback_chain:
            candidates.append(
                (fallback.provider_name, fallback.model, fallback.effort),
            )

        errors: list[str] = []
        for provider_name, model, effort in candidates:
            provider = self._providers.get(provider_name)
            if provider is None:
                errors.append(f"provider '{provider_name}' not registered")
                continue

            # Cost check — skip if over budget
            if context and context.budget_remaining > 0:
                estimate = provider.cost_estimate(request)
                if estimate.total_max_cost > context.budget_remaining:
                    logger.warning(
                        "skipping provider — cost exceeds budget",
                        provider=provider_name,
                        cost=estimate.total_max_cost,
                        budget=context.budget_remaining,
                    )
                    continue

            # Build the actual request for this provider/model
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
                # Track session cost
                if response.usage:
                    estimate = provider.cost_estimate(provider_request)
                    self._session_cost += estimate.total_max_cost
                logger.info(
                    "completion succeeded",
                    provider=provider_name,
                    model=model,
                    latency_ms=response.latency_ms,
                )
                return response
            except Exception as exc:
                error_msg = f"{provider_name}/{model}: {exc}"
                errors.append(error_msg)
                logger.warning("completion failed, trying fallback", error=error_msg)
                continue

        raise RuntimeError(
            f"All providers failed. Errors: {'; '.join(errors)}",
        )

    @property
    def session_cost(self) -> float:
        """Total accumulated cost for the current session in USD."""
        return self._session_cost

    def reset_session_cost(self) -> None:
        """Reset the session cost counter."""
        self._session_cost = 0.0

    @property
    def registered_providers(self) -> list[str]:
        """List of registered provider names."""
        return list(self._providers.keys())
