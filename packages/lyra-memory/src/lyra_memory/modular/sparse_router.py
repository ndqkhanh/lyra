"""
Sparse Module Router — routes queries to relevant memory modules
using sparse activation, avoiding interference from irrelevant modules.

Source: Modular Compression (ztmwHisqJ4), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RouteDecision:
    """Result of routing a query to memory modules."""

    query: str
    selected_modules: list[str]
    scores: dict[str, float]
    reason: str = ""

    @property
    def module_count(self) -> int:
        return len(self.selected_modules)


@dataclass
class ModularRouter:
    """Routes queries to relevant modules using keyword-based scoring.

    Only routes to modules whose content overlaps with the query,
    minimizing interference from irrelevant modules.
    """

    modules: dict[str, object] = field(default_factory=dict)  # name -> ModularMemoryModule
    top_k: int = 3

    def register(self, name: str, module: object) -> None:
        """Register a memory module for routing."""
        self.modules[name] = module

    def route(self, query: str) -> RouteDecision:
        """Route a query to the most relevant modules."""
        from lyra_memory.modular.memory_module import ModularMemoryModule

        query_words = set(query.lower().split())
        scores: dict[str, float] = {}

        for name, mod in self.modules.items():
            m: ModularMemoryModule = mod  # type: ignore[assignment]
            if not m.entries:
                scores[name] = 0.0
                continue
            module_text = " ".join(m.entries).lower()
            module_words = set(module_text.split())
            overlap = query_words & module_words
            scores[name] = len(overlap) / max(len(query_words), 1)

        sorted_modules = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [name for name, score in sorted_modules[:self.top_k] if score > 0]

        if not selected:
            for name, mod in self.modules.items():
                m = mod  # type: ignore[assignment]
                if m.interference.is_stable:
                    selected.append(name)
                    break
            if not selected and self.modules:
                selected = [list(self.modules.keys())[0]]

        return RouteDecision(
            query=query,
            selected_modules=selected,
            scores={n: scores[n] for n in selected},
            reason=f"Routed to {len(selected)} module(s) via keyword overlap",
        )

    @property
    def module_names(self) -> list[str]:
        return list(self.modules.keys())
