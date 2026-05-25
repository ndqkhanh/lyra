"""
Memory Store definitions — 4-tier store architecture with cost metrics.

Source: Cost-Sensitive Store Routing (iGRGjdhl9r), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryStore:
    """A memory store with cost and performance metrics.

    Attributes:
        name: Human-readable store name
        cost_per_query: Average tokens consumed per query
        coverage: Fraction of query types this store can answer (0-1)
        exact_match_rate: Fraction of retrievals where top-1 is correct (0-1)
        waste_rate: Fraction of retrieved context not used (0-1)
        latency_ms: Average retrieval latency in milliseconds
    """

    name: str
    cost_per_query: int = 200
    coverage: float = 0.5
    exact_match_rate: float = 0.7
    waste_rate: float = 0.3
    latency_ms: float = 50.0

    @property
    def efficiency_score(self) -> float:
        """Composite efficiency: accuracy per token cost."""
        if self.cost_per_query <= 0:
            return 0.0
        return self.exact_match_rate / self.cost_per_query

    @property
    def net_utility(self) -> float:
        """Accuracy minus waste penalty."""
        return self.exact_match_rate * (1.0 - self.waste_rate)


@dataclass
class MultiStoreRegistry:
    """4-store architecture with cost-sensitive routing.

    Default stores mirror the paper's configuration:
    - STM: Fast, low-cost, limited coverage (recent context)
    - SUMMARY: Medium cost, moderate coverage (compressed history)
    - LTM: High cost, high coverage (full long-term memory)
    - EPISODIC: Max cost, max coverage (raw traces)
    """

    stores: dict[str, MemoryStore] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stores:
            self.stores = {
                "STM": MemoryStore(
                    name="Short-Term Memory",
                    cost_per_query=200,
                    coverage=0.3,
                    exact_match_rate=0.9,
                    waste_rate=0.1,
                    latency_ms=5.0,
                ),
                "SUMMARY": MemoryStore(
                    name="Summary Store",
                    cost_per_query=150,
                    coverage=0.6,
                    exact_match_rate=0.7,
                    waste_rate=0.2,
                    latency_ms=15.0,
                ),
                "LTM": MemoryStore(
                    name="Long-Term Memory (Full)",
                    cost_per_query=800,
                    coverage=0.95,
                    exact_match_rate=0.85,
                    waste_rate=0.5,
                    latency_ms=100.0,
                ),
                "EPISODIC": MemoryStore(
                    name="Episodic Memory (Raw Traces)",
                    cost_per_query=2000,
                    coverage=0.99,
                    exact_match_rate=0.95,
                    waste_rate=0.7,
                    latency_ms=200.0,
                ),
            }

    def get_store(self, name: str) -> MemoryStore | None:
        return self.stores.get(name)

    def within_budget(self, name: str, budget_tokens: int) -> bool:
        store = self.stores.get(name)
        return store is not None and store.cost_per_query <= budget_tokens

    def stores_within_budget(self, budget_tokens: int) -> list[str]:
        return [n for n, s in self.stores.items() if s.cost_per_query <= budget_tokens]

    @property
    def store_names(self) -> list[str]:
        return list(self.stores.keys())
