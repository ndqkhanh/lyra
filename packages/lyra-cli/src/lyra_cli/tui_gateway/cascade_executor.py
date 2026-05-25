"""4-tier model cascade executor — bridges routing decisions to provider calls.

Haiku → Sonnet → Opus → Gemini/OpenRouter with cost tracking.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from lyra_model_router import (
    Budget,
    IntelligentModelRouter,
    ModelSpec,
    RoutingDecision,
    RoutingStrategy,
)


@dataclass
class CascadeResult:
    """Result of a cascaded execution attempt."""

    model_used: str
    provider: str
    tier: str
    content: str
    attempts: int
    total_cost_usd: float
    total_latency_ms: float
    escalated: bool


@dataclass
class CostRecord:
    model: str
    provider: str
    call_count: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    last_used: float = 0.0


class ModelCascadeExecutor:
    """Executes model calls with 4-tier fallback cascade.

    Tier 1: Haiku (FAST/CHEAP) — first attempt, minimal cost
    Tier 2: Sonnet (STANDARD) — if Haiku response quality is low
    Tier 3: Opus (REASONING) — complex tasks, deep reasoning
    Tier 4: Gemini/OpenRouter — external fallback if Anthropic unavailable
    """

    def __init__(
        self,
        router: IntelligentModelRouter | None = None,
        strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMAL,
    ) -> None:
        self._router = router or IntelligentModelRouter()
        self._strategy = strategy
        self._lock = threading.Lock()
        self._costs: dict[str, CostRecord] = {}
        self._call_count: int = 0
        self._total_saved: float = 0.0

    @property
    def router(self) -> IntelligentModelRouter:
        return self._router

    @property
    def strategy(self) -> RoutingStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, s: RoutingStrategy) -> None:
        self._strategy = s

    def execute(
        self,
        prompt: str,
        *,
        exec_fn: Callable[[str, str], str],
        complexity: float = 0.3,
        is_reasoning: bool = False,
        budget: Budget | None = None,
        max_escalations: int = 2,
    ) -> CascadeResult:
        """Execute a prompt with automatic tier escalation.

        `exec_fn(model_name, prompt)` is the actual LLM call function.
        Returns the first successful result, escalating tiers if needed.
        """
        decision = self._router.route(
            prompt,
            strategy=self._strategy,
            budget=budget,
            complexity=complexity,
            is_reasoning=is_reasoning,
        )
        candidates = self._get_cascade_chain(decision)

        last_error: str | None = None
        for i, spec in enumerate(candidates[: 1 + max_escalations]):
            start = time.monotonic()
            try:
                content = exec_fn(spec.name, prompt)
                elapsed_ms = (time.monotonic() - start) * 1000
                cost = self._estimate_cost(spec, prompt)

                with self._lock:
                    self._track(spec, cost, elapsed_ms)

                return CascadeResult(
                    model_used=spec.name,
                    provider=spec.provider.value,
                    tier=spec.tier.value,
                    content=content,
                    attempts=i + 1,
                    total_cost_usd=round(cost, 6),
                    total_latency_ms=round(elapsed_ms, 1),
                    escalated=i > 0,
                )
            except Exception as exc:
                last_error = str(exc)
                continue

        raise RuntimeError(
            f"All {max_escalations + 1} cascade tiers failed. "
            f"Last error: {last_error}"
        )

    def _get_cascade_chain(self, decision: RoutingDecision) -> list[ModelSpec]:
        """Build cascade chain: primary → fallback models → tier escalation."""
        seen: set[str] = set()
        chain: list[ModelSpec] = []

        # Primary model first
        chain.append(decision.model)
        seen.add(decision.model.name)

        # Router-provided fallback models
        for fb in decision.fallback_models:
            if fb.name not in seen:
                chain.append(fb)
                seen.add(fb.name)

        # Fill remaining tiers via select_tier with descending reliability
        for reliability in (0.90, 0.80, 0.70, 0.50):
            try:
                alt = self._router.select_tier(
                    required_reliability=reliability,
                    is_reasoning=False,
                )
                if alt.name not in seen:
                    chain.append(alt)
                    seen.add(alt.name)
            except Exception:
                pass

        return chain

    def _estimate_cost(self, spec: ModelSpec, prompt: str) -> float:
        """Rough cost estimate based on token count approximation."""
        estimated_tokens = len(prompt) / 3.5
        return (estimated_tokens / 1000) * spec.cost_per_1k_tokens * 2

    def _track(self, spec: ModelSpec, cost: float, latency_ms: float) -> None:
        key = spec.name
        rec = self._costs.setdefault(
            key, CostRecord(model=spec.name, provider=spec.provider.value)
        )
        rec.call_count += 1
        rec.total_cost += cost
        rec.total_latency_ms += latency_ms
        rec.last_used = time.time()
        self._call_count += 1

    def cost_summary(self) -> dict[str, Any]:
        with self._lock:
            total = sum(r.total_cost for r in self._costs.values())
            return {
                "total_calls": self._call_count,
                "total_cost_usd": round(total, 6),
                "by_model": {
                    k: {
                        "calls": r.call_count,
                        "cost": round(r.total_cost, 6),
                        "avg_latency_ms": round(
                            r.total_latency_ms / max(r.call_count, 1), 1
                        ),
                    }
                    for k, r in self._costs.items()
                },
            }

    def snapshot(self) -> dict[str, Any]:
        return {
            "strategy": self._strategy.value,
            "router": self._router.snapshot(),
            "costs": self.cost_summary(),
        }
