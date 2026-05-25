"""Tests for ModularRouter and RouteDecision."""

from lyra_memory.modular.memory_module import ModularMemoryModule
from lyra_memory.modular.sparse_router import ModularRouter, RouteDecision


class TestRouteDecision:
    def test_default_values(self):
        rd = RouteDecision(query="test", selected_modules=[], scores={})
        assert rd.query == "test"
        assert rd.selected_modules == []
        assert rd.scores == {}
        assert rd.module_count == 0

    def test_with_modules(self):
        rd = RouteDecision(
            query="what is memory",
            selected_modules=["math", "code"],
            scores={"math": 0.8, "code": 0.5},
            reason="keyword match",
        )
        assert rd.module_count == 2
        assert rd.reason == "keyword match"
        assert "math" in rd.selected_modules
        assert rd.scores["math"] == 0.8

    def test_module_count_zero(self):
        rd = RouteDecision(query="x", selected_modules=[], scores={})
        assert rd.module_count == 0


class TestModularRouter:
    def _make_router(self) -> ModularRouter:
        router = ModularRouter(top_k=3)
        math = ModularMemoryModule(name="math")
        for e in ["linear algebra basics", "calculus derivatives", "matrix multiplication"]:
            math.add(e)
        code = ModularMemoryModule(name="code")
        for e in ["python async patterns", "rust ownership", "type hints"]:
            code.add(e)
        router.register("math", math)
        router.register("code", code)
        return router

    def test_register_module(self):
        router = ModularRouter()
        mod = ModularMemoryModule(name="test")
        router.register("test", mod)
        assert "test" in router.modules
        assert router.module_names == ["test"]

    def test_route_finds_relevant_module(self):
        router = self._make_router()
        decision = router.route("linear algebra problem")
        assert "math" in decision.selected_modules

    def test_route_finds_code_module(self):
        router = self._make_router()
        decision = router.route("python async code")
        assert "code" in decision.selected_modules

    def test_route_returns_scores(self):
        router = self._make_router()
        decision = router.route("python async code")
        for name in decision.selected_modules:
            assert decision.scores[name] > 0

    def test_route_respects_top_k(self):
        router = ModularRouter(top_k=1)
        for name in ["a", "b", "c"]:
            mod = ModularMemoryModule(name=name)
            mod.add(f"{name} specific content here")
            router.register(name, mod)
        decision = router.route("specific content")
        assert decision.module_count <= 1

    def test_route_empty_query(self):
        router = self._make_router()
        decision = router.route("")
        assert decision.module_count >= 1

    def test_route_falls_back_to_stable(self):
        router = ModularRouter()
        stable = ModularMemoryModule(name="stable")
        stable.add("irrelevant content")
        router.register("stable", stable)
        decision = router.route("completely unrelated query")
        assert "stable" in decision.selected_modules

    def test_route_falls_back_to_first_module(self):
        router = ModularRouter()
        a = ModularMemoryModule(name="a")
        a.add("x")
        a.interference.overlap_ratio = 1.0
        a.interference.update_magnitude = 1.0
        router.register("a", a)
        decision = router.route("unrelated")
        assert decision.selected_modules == ["a"]

    def test_empty_modules_skip(self):
        router = ModularRouter()
        empty = ModularMemoryModule(name="empty")
        full = ModularMemoryModule(name="full")
        full.add("important content here")
        router.register("empty", empty)
        router.register("full", full)
        decision = router.route("important")
        assert "empty" not in decision.selected_modules
        assert "full" in decision.selected_modules

    def test_scores_sum_to_coverage(self):
        router = self._make_router()
        decision = router.route("linear algebra")
        assert all(0 <= s <= 1 for s in decision.scores.values())

    def test_route_returns_reason(self):
        router = self._make_router()
        decision = router.route("test query")
        assert len(decision.reason) > 0
        assert "Routed to" in decision.reason
