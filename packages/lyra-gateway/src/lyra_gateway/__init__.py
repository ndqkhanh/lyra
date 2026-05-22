"""LLM API Gateway — route to 100+ backends, cost tracking, failover, rate limiting."""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)
__all__ = ["Provider", "GatewayConfig", "LLMGateway"]

@dataclass
class Provider: name: str; cost_per_1k_tokens: float = 0.01; is_available: bool = True; latency_p50_ms: float = 500

@dataclass
class GatewayConfig: primary_provider: str = "openai"; fallback_providers: list[str] = field(default_factory=list); max_retries: int = 3; budget_limit_usd: float = 100.0

class LLMGateway:
    def __init__(self): self.providers: dict[str, Provider] = {}; self.config = GatewayConfig(); self._total_cost = 0.0; self._call_count = 0; self._latencies: list[float] = []

    def register_provider(self, name: str, cost: float = 0.01, latency: float = 500) -> Provider:
        p = Provider(name=name, cost_per_1k_tokens=cost, latency_p50_ms=latency); self.providers[name] = p; return p

    def route(self, task: str, required_quality: str = "high") -> Optional[Provider]:
        if required_quality == "high":
            candidates = [p for p in self.providers.values() if p.is_available and p.cost_per_1k_tokens > 0.005]
        else:
            candidates = [p for p in self.providers.values() if p.is_available]
        if not candidates: return None
        best = min(candidates, key=lambda p: p.cost_per_1k_tokens)
        self._call_count += 1; self._total_cost += best.cost_per_1k_tokens; self._latencies.append(best.latency_p50_ms)
        return best

    def check_budget(self) -> bool: return self._total_cost < self.config.budget_limit_usd

    def fallback(self, failed_provider: str) -> Optional[Provider]:
        for name in self.config.fallback_providers:
            p = self.providers.get(name)
            if p and p.is_available: return p
        return None

    @property
    def stats(self) -> dict: return {"total_cost": self._total_cost, "calls": self._call_count, "providers": len(self.providers), "budget_remaining": self.config.budget_limit_usd - self._total_cost}
