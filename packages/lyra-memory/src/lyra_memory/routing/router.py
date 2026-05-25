"""
Cost-Sensitive Router — selects optimal memory store(s) per query
balancing accuracy gain against token cost and waste penalty.

Source: Cost-Sensitive Store Routing (iGRGjdhl9r), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class QueryProfile:
    """Profile of a query for routing decisions.

    Attributes:
        query: The original query text
        match_difficulty: How hard to find the right match (0=easy, 1=hard)
        required_coverage: Minimum coverage needed to answer this query
        urgency: How time-sensitive the query is (0=background, 1=critical)
        domain: The knowledge domain of the query
    """

    query: str
    match_difficulty: float = 0.5
    required_coverage: float = 0.5
    urgency: float = 0.5
    domain: str = "general"

    @property
    def complexity_score(self) -> float:
        """Composite complexity score for routing decisions."""
        return (
            0.4 * self.match_difficulty
            + 0.3 * self.required_coverage
            + 0.3 * self.urgency
        )


@dataclass
class RouteResult:
    """Result of store selection for a query."""

    query: str
    selected_stores: list[str]
    total_cost: int
    expected_accuracy: float
    reason: str = ""


@dataclass
class CostSensitiveRouter:
    """Routes queries to optimal memory store(s) based on cost-benefit analysis.

    Uses utility-based scoring with accuracy, cost, and waste dimensions.
    Supports budget-constrained knapsack-style store selection.
    """

    stores: object  # MultiStoreRegistry
    llm: LLMClient

    async def route(
        self, query: str, budget_tokens: int = 500,
    ) -> RouteResult:
        """Select optimal store combination within token budget.

        Steps:
        1. Profile the query (match difficulty, coverage needs, urgency)
        2. Compute expected utility for each store
        3. Select optimal combination via utility-ranked selection
        """
        profile = await self._profile_query(query)
        return self._select_stores(query, profile, budget_tokens)

    def route_sync(
        self, query: str, profile: QueryProfile, budget_tokens: int = 500,
    ) -> RouteResult:
        """Synchronous routing with a pre-computed profile."""
        return self._select_stores(query, profile, budget_tokens)

    async def _profile_query(self, query: str) -> QueryProfile:
        """Classify query type and estimate required information."""
        prompt = f"""Analyze this query and estimate its retrieval profile:

Query: {query[:500]}

Output JSON only:
{{
    "match_difficulty": <float 0.0-1.0, how hard to find exact match>,
    "required_coverage": <float 0.0-1.0, breadth of knowledge needed>,
    "urgency": <float 0.0-1.0, time sensitivity>,
    "domain": "<short domain label>"
}}"""

        response = await self.llm.complete(prompt)
        return self._parse_profile(response, query)

    def _select_stores(
        self, query: str, profile: QueryProfile, budget_tokens: int,
    ) -> RouteResult:
        """Select stores using utility-ranked selection within budget."""
        from lyra_memory.routing.store import MultiStoreRegistry

        registry: MultiStoreRegistry = self.stores  # type: ignore[assignment]
        remaining = budget_tokens
        selected: list[tuple[str, float]] = []

        for name, store in registry.stores.items():
            if store.cost_per_query > budget_tokens:
                continue
            utility = self._compute_utility(store, profile)
            selected.append((name, utility))

        selected.sort(key=lambda x: x[1], reverse=True)

        chosen: list[str] = []
        total_cost = 0
        for name, _ in selected:
            store = registry.stores[name]
            if total_cost + store.cost_per_query <= budget_tokens:
                chosen.append(name)
                total_cost += store.cost_per_query

        if not chosen:
            cheapest = min(
                registry.stores.items(),
                key=lambda kv: kv[1].cost_per_query,
            )
            chosen = [cheapest[0]]
            total_cost = cheapest[1].cost_per_query

        expected_accuracy = self._estimate_accuracy(chosen, profile, registry)
        return RouteResult(
            query=query,
            selected_stores=chosen,
            total_cost=total_cost,
            expected_accuracy=expected_accuracy,
            reason=f"Selected {len(chosen)} store(s) within {budget_tokens} token budget",
        )

    @staticmethod
    def _compute_utility(store: object, profile: QueryProfile) -> float:
        """Expected utility = accuracy gain - cost penalty - waste penalty."""
        from lyra_memory.routing.store import MemoryStore

        s: MemoryStore = store  # type: ignore[assignment]

        accuracy_weight = 0.5
        cost_weight = 0.3
        waste_weight = 0.2

        accuracy = s.exact_match_rate * (1.0 - profile.match_difficulty * 0.5)
        cost_penalty = s.cost_per_query / 2000.0
        waste_penalty = s.waste_rate

        return (
            accuracy_weight * accuracy
            - cost_weight * cost_penalty
            - waste_weight * waste_penalty
        )

    @staticmethod
    def _estimate_accuracy(
        chosen: list[str], profile: QueryProfile, registry: object,
    ) -> float:
        """Estimate combined accuracy of selected stores."""
        from lyra_memory.routing.store import MultiStoreRegistry

        reg: MultiStoreRegistry = registry  # type: ignore[assignment]

        if not chosen:
            return 0.0

        accuracies = []
        for name in chosen:
            store = reg.stores.get(name)
            if store:
                adjusted = store.exact_match_rate * store.coverage
                accuracies.append(adjusted)

        if not accuracies:
            return 0.0

        combined = 1.0
        for acc in accuracies:
            combined *= (1.0 - acc)
        return round(1.0 - combined, 4)

    @staticmethod
    def _parse_profile(response: str, query: str) -> QueryProfile:
        import json

        try:
            data = json.loads(_extract_json(response))
            return QueryProfile(
                query=query,
                match_difficulty=float(data.get("match_difficulty", 0.5)),
                required_coverage=float(data.get("required_coverage", 0.5)),
                urgency=float(data.get("urgency", 0.5)),
                domain=str(data.get("domain", "general")),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return QueryProfile(query=query)


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()
