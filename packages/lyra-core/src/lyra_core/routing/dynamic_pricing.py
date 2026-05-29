"""Dynamic multi-provider pricing engine.

Computes real-time cost estimates across providers (AWS Bedrock, Google
Vertex AI, Anthropic API, OpenRouter) factoring in:
  - Token pricing (input/output)
  - Current provider load / availability
  - Latency SLA tiers
  - Budget pressure multiplier

Integrates with the RL router to provide cost signals for action selection.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class PricingTier(Enum):
    BUDGET = "budget"  # cheapest available
    STANDARD = "standard"  # balanced cost/perf
    PREMIUM = "premium"  # best quality, highest cost


# Approximate pricing per 1M tokens (USD) — snapshot, updated via config
_DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "deepseek-v4-pro": {"input": 0.50, "output": 2.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

_TIER_MAPPING: dict[str, PricingTier] = {
    "fast": PricingTier.BUDGET,
    "reasoning": PricingTier.STANDARD,
    "advisor": PricingTier.PREMIUM,
}


@dataclass(frozen=True)
class ProviderQuote:
    """Cost estimate for a single provider."""

    provider_id: str
    tier: PricingTier
    input_cost_per_1m: float
    output_cost_per_1m: float
    estimated_total_usd: float
    est_input_tokens: int
    est_output_tokens: int
    load_factor: float  # 0 = idle, 1 = saturated
    latency_estimate_ms: float
    timestamp: float


@dataclass(frozen=True)
class PricingSnapshot:
    """Aggregated pricing across all configured providers."""

    quotes: tuple[ProviderQuote, ...]
    cheapest: ProviderQuote | None
    recommended: ProviderQuote | None
    budget_pressure: float
    timestamp: float


@dataclass
class DynamicPricingEngine:
    """Real-time pricing calculator for multi-provider routing.

    Usage::

        engine = DynamicPricingEngine()
        quote = engine.estimate("claude-sonnet-4-6", input_tokens=500, output_tokens=200)
        snapshot = engine.snapshot(input_tokens=1000, output_tokens=500)
    """

    pricing_table: dict[str, dict[str, float]] = field(
        default_factory=lambda: dict(_DEFAULT_PRICING)
    )
    load_factors: dict[str, float] = field(default_factory=dict)
    latency_profiles: dict[str, float] = field(
        default_factory=lambda: {
            "claude-haiku-4-5": 200.0,
            "claude-sonnet-4-6": 800.0,
            "claude-opus-4-7": 2500.0,
            "deepseek-v4-pro": 600.0,
            "gpt-4o": 1200.0,
            "gpt-4o-mini": 300.0,
        }
    )
    budget_pressure: float = 0.0

    def estimate(
        self,
        provider_id: str,
        *,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ) -> ProviderQuote | None:
        """Get a cost quote for a specific provider."""
        pricing = self.pricing_table.get(provider_id)
        if not pricing:
            return None

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total = input_cost + output_cost

        load = self.load_factors.get(provider_id, 0.5)
        base_latency = self.latency_profiles.get(provider_id, 1000.0)
        latency = base_latency * (1.0 + load * 0.5 + self.budget_pressure * 0.3)

        # Determine tier from pricing
        if pricing["input"] <= 1.0:
            tier = PricingTier.BUDGET
        elif pricing["input"] <= 5.0:
            tier = PricingTier.STANDARD
        else:
            tier = PricingTier.PREMIUM

        return ProviderQuote(
            provider_id=provider_id,
            tier=tier,
            input_cost_per_1m=pricing["input"],
            output_cost_per_1m=pricing["output"],
            estimated_total_usd=round(total, 6),
            est_input_tokens=input_tokens,
            est_output_tokens=output_tokens,
            load_factor=load,
            latency_estimate_ms=round(latency, 1),
            timestamp=time.time(),
        )

    def snapshot(
        self,
        *,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ) -> PricingSnapshot:
        """Get pricing quotes from all configured providers."""
        quotes: list[ProviderQuote] = []
        for provider_id in self.pricing_table:
            quote = self.estimate(
                provider_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            if quote:
                quotes.append(quote)

        quotes.sort(key=lambda q: q.estimated_total_usd)

        cheapest = quotes[0] if quotes else None

        # Recommend standard-tier provider unless budget is tight
        if self.budget_pressure > 0.8:
            recommended = cheapest
        else:
            standard = [q for q in quotes if q.tier == PricingTier.STANDARD]
            recommended = standard[0] if standard else cheapest

        return PricingSnapshot(
            quotes=tuple(quotes),
            cheapest=cheapest,
            recommended=recommended,
            budget_pressure=self.budget_pressure,
            timestamp=time.time(),
        )

    def update_load(self, provider_id: str, load: float) -> None:
        self.load_factors[provider_id] = max(0.0, min(1.0, load))

    def update_pricing(self, provider_id: str, input_price: float, output_price: float) -> None:
        self.pricing_table[provider_id] = {"input": input_price, "output": output_price}

    def set_budget_pressure(self, pressure: float) -> None:
        self.budget_pressure = max(0.0, min(1.0, pressure))

    def cost_for_tier(self, tier: str, input_tokens: int = 1000, output_tokens: int = 500) -> float:
        """Estimate cost for a routing tier (fast/reasoning/advisor)."""
        pricing_tier = _TIER_MAPPING.get(tier, PricingTier.STANDARD)
        candidates = [
            pid
            for pid, p in self.pricing_table.items()
            if (
                (pricing_tier == PricingTier.BUDGET and p["input"] <= 1.0)
                or (pricing_tier == PricingTier.STANDARD and 1.0 < p["input"] <= 5.0)
                or (pricing_tier == PricingTier.PREMIUM and p["input"] > 5.0)
            )
        ]
        if not candidates:
            candidates = list(self.pricing_table.keys())

        costs = []
        for pid in candidates:
            q = self.estimate(pid, input_tokens=input_tokens, output_tokens=output_tokens)
            if q:
                costs.append(q.estimated_total_usd)

        return min(costs) if costs else 0.0

    @property
    def providers(self) -> tuple[str, ...]:
        return tuple(self.pricing_table.keys())


__all__ = [
    "DynamicPricingEngine",
    "PricingSnapshot",
    "PricingTier",
    "ProviderQuote",
]
