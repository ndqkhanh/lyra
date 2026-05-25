"""Tests for MemoryStore and MultiStoreRegistry."""

from lyra_memory.routing.store import MemoryStore, MultiStoreRegistry


class TestMemoryStore:
    def test_default_values(self):
        s = MemoryStore(name="Test Store")
        assert s.name == "Test Store"
        assert s.cost_per_query == 200
        assert s.coverage == 0.5
        assert s.exact_match_rate == 0.7
        assert s.waste_rate == 0.3
        assert s.latency_ms == 50.0

    def test_custom_values(self):
        s = MemoryStore(
            name="Custom",
            cost_per_query=500,
            coverage=0.8,
            exact_match_rate=0.9,
            waste_rate=0.2,
            latency_ms=25.0,
        )
        assert s.cost_per_query == 500
        assert s.coverage == 0.8

    def test_efficiency_score(self):
        s = MemoryStore(name="Efficient", cost_per_query=100, exact_match_rate=0.8)
        assert s.efficiency_score == 0.008

    def test_efficiency_score_zero_cost(self):
        s = MemoryStore(name="Free", cost_per_query=0, exact_match_rate=0.9)
        assert s.efficiency_score == 0.0

    def test_net_utility(self):
        s = MemoryStore(name="Clean", exact_match_rate=0.9, waste_rate=0.2)
        assert s.net_utility == 0.9 * 0.8


class TestMultiStoreRegistry:
    def test_default_registry_has_four_stores(self):
        reg = MultiStoreRegistry()
        assert len(reg.stores) == 4
        assert "STM" in reg.stores
        assert "SUMMARY" in reg.stores
        assert "LTM" in reg.stores
        assert "EPISODIC" in reg.stores

    def test_default_stm_is_cheapest(self):
        reg = MultiStoreRegistry()
        cheapest = min(reg.stores.values(), key=lambda s: s.cost_per_query)
        assert cheapest.name == "Summary Store"

    def test_episodic_has_highest_coverage(self):
        reg = MultiStoreRegistry()
        highest = max(reg.stores.values(), key=lambda s: s.coverage)
        assert highest.name == "Episodic Memory (Raw Traces)"

    def test_get_store_returns_correct_store(self):
        reg = MultiStoreRegistry()
        stm = reg.get_store("STM")
        assert stm is not None
        assert stm.name == "Short-Term Memory"

    def test_get_store_nonexistent(self):
        reg = MultiStoreRegistry()
        assert reg.get_store("NONEXISTENT") is None

    def test_within_budget_true(self):
        reg = MultiStoreRegistry()
        assert reg.within_budget("STM", 500) is True

    def test_within_budget_false(self):
        reg = MultiStoreRegistry()
        assert reg.within_budget("EPISODIC", 100) is False

    def test_within_budget_nonexistent(self):
        reg = MultiStoreRegistry()
        assert reg.within_budget("NOPE", 1000) is False

    def test_stores_within_budget(self):
        reg = MultiStoreRegistry()
        within = reg.stores_within_budget(300)
        assert "STM" in within
        assert "SUMMARY" in within
        assert "LTM" not in within
        assert "EPISODIC" not in within

    def test_custom_stores(self):
        reg = MultiStoreRegistry(stores={
            "FAST": MemoryStore(name="Fast", cost_per_query=50),
            "SLOW": MemoryStore(name="Slow", cost_per_query=500),
        })
        assert len(reg.stores) == 2
        assert reg.get_store("FAST").cost_per_query == 50

    def test_store_names(self):
        reg = MultiStoreRegistry()
        names = reg.store_names
        assert len(names) == 4
        assert "STM" in names
