"""Tests for MemoryHeuristic and HeuristicPool."""

from lyra_memory.heuristics.pool import HeuristicPool, MemoryHeuristic
from lyra_memory.modular.memory_module import ModularMemoryModule


class TestMemoryHeuristic:
    def _make_module(self, size: int = 10) -> ModularMemoryModule:
        m = ModularMemoryModule(name="test")
        for i in range(size):
            m.add(f"entry_{i}")
        return m

    def test_default_values(self):
        h = MemoryHeuristic(
            name="test_h",
            priority=0.5,
            condition=lambda m: True,
            action=lambda m: 1,
        )
        assert h.name == "test_h"
        assert h.priority == 0.5
        assert h.enabled is True
        assert h.cooldown == 0

    def test_applies_when_condition_true(self):
        h = MemoryHeuristic(
            name="always",
            priority=1.0,
            condition=lambda m: True,
            action=lambda m: 1,
        )
        assert h.applies(self._make_module(), cycle=0) is True

    def test_applies_when_condition_false(self):
        h = MemoryHeuristic(
            name="never",
            priority=1.0,
            condition=lambda m: False,
            action=lambda m: 1,
        )
        assert h.applies(self._make_module(), cycle=0) is False

    def test_applies_false_when_disabled(self):
        h = MemoryHeuristic(
            name="disabled",
            priority=1.0,
            condition=lambda m: True,
            action=lambda m: 1,
            enabled=False,
        )
        assert h.applies(self._make_module(), cycle=0) is False

    def test_applies_false_during_cooldown(self):
        h = MemoryHeuristic(
            name="cooldown",
            priority=1.0,
            condition=lambda m: True,
            action=lambda m: 1,
            cooldown=3,
        )
        h.apply(self._make_module(), cycle=0)
        assert h.applies(self._make_module(), cycle=1) is False
        assert h.applies(self._make_module(), cycle=3) is True

    def test_apply_returns_action_result(self):
        h = MemoryHeuristic(
            name="count",
            priority=1.0,
            condition=lambda m: True,
            action=lambda m: 42,
        )
        result = h.apply(self._make_module(), cycle=0)
        assert result == 42

    def test_apply_updates_last_applied(self):
        h = MemoryHeuristic(
            name="track",
            priority=1.0,
            condition=lambda m: True,
            action=lambda m: 1,
        )
        h.apply(self._make_module(), cycle=5)
        assert h._last_applied == 5

    def test_condition_receives_module(self):
        captured = []

        def condition(mod):
            captured.append(mod.size)
            return True

        h = MemoryHeuristic(
            name="capture",
            priority=1.0,
            condition=condition,
            action=lambda m: 1,
        )
        m = self._make_module(7)
        h.applies(m, cycle=0)
        assert captured == [7]


class TestHeuristicPool:
    def _make_pool(self) -> HeuristicPool:
        return HeuristicPool()

    def _make_module(self) -> ModularMemoryModule:
        m = ModularMemoryModule(name="test")
        for i in range(10):
            m.add(f"entry_{i}")
        return m

    def test_initial_state(self):
        pool = self._make_pool()
        assert pool.heuristics == []
        assert pool.enabled_count == 0
        assert pool.cycle == 0

    def test_register_adds_heuristic(self):
        pool = self._make_pool()
        h = MemoryHeuristic(name="h1", priority=0.5, condition=lambda m: True, action=lambda m: 1)
        pool.register(h)
        assert pool.enabled_count == 1

    def test_unregister_removes_heuristic(self):
        pool = self._make_pool()
        h = MemoryHeuristic(name="h1", priority=0.5, condition=lambda m: True, action=lambda m: 1)
        pool.register(h)
        assert pool.unregister(h.id) is True
        assert pool.enabled_count == 0

    def test_unregister_nonexistent(self):
        pool = self._make_pool()
        assert pool.unregister("nonexistent") is False

    def test_disable_enable(self):
        pool = self._make_pool()
        h = MemoryHeuristic(name="h1", priority=0.5, condition=lambda m: True, action=lambda m: 1)
        pool.register(h)
        assert pool.disable(h.id) is True
        assert pool.enabled_count == 0
        assert pool.enable(h.id) is True
        assert pool.enabled_count == 1

    def test_disable_nonexistent(self):
        pool = self._make_pool()
        assert pool.disable("nonexistent") is False
        assert pool.enable("nonexistent") is False

    def test_tick_advances_cycle(self):
        pool = self._make_pool()
        pool.tick()
        pool.tick()
        assert pool.cycle == 2

    def test_apply_runs_in_priority_order(self):
        pool = self._make_pool()
        order = []

        h1 = MemoryHeuristic(
            name="low",
            priority=0.1,
            condition=lambda m: True,
            action=lambda m: order.append("low") or 1,
        )
        h2 = MemoryHeuristic(
            name="high",
            priority=0.9,
            condition=lambda m: True,
            action=lambda m: order.append("high") or 1,
        )
        h3 = MemoryHeuristic(
            name="mid",
            priority=0.5,
            condition=lambda m: True,
            action=lambda m: order.append("mid") or 1,
        )

        pool.register(h1)
        pool.register(h2)
        pool.register(h3)

        pool.apply(self._make_module(), max_heuristics=3)
        assert order == ["high", "mid", "low"]

    def test_apply_respects_max_heuristics(self):
        pool = self._make_pool()
        for i in range(5):
            h = MemoryHeuristic(
                name=f"h{i}",
                priority=float(i),
                condition=lambda m: True,
                action=lambda m: 1,
            )
            pool.register(h)

        affected = pool.apply(self._make_module(), max_heuristics=2)
        assert affected == 2

    def test_apply_skips_disabled(self):
        pool = self._make_pool()
        h = MemoryHeuristic(
            name="off", priority=1.0, condition=lambda m: True, action=lambda m: 1, enabled=False
        )
        pool.register(h)
        affected = pool.apply(self._make_module())
        assert affected == 0

    def test_apply_skips_non_matching(self):
        pool = self._make_pool()
        h = MemoryHeuristic(
            name="never", priority=1.0, condition=lambda m: False, action=lambda m: 1
        )
        pool.register(h)
        affected = pool.apply(self._make_module())
        assert affected == 0

    def test_top_k_returns_by_priority(self):
        pool = self._make_pool()
        for i in range(5):
            h = MemoryHeuristic(
                name=f"h{i}",
                priority=float(i),
                condition=lambda m: True,
                action=lambda m: 1,
            )
            pool.register(h)

        top = pool.top_k(3)
        assert len(top) == 3
        assert top[0].priority > top[1].priority > top[2].priority

    def test_top_k_skips_disabled(self):
        pool = self._make_pool()
        h1 = MemoryHeuristic(name="on", priority=1.0, condition=lambda m: True, action=lambda m: 1)
        h2 = MemoryHeuristic(
            name="off", priority=0.9, condition=lambda m: True, action=lambda m: 1, enabled=False
        )
        pool.register(h1)
        pool.register(h2)
        top = pool.top_k(2)
        assert len(top) == 1
        assert top[0].name == "on"

    def test_find_by_substring(self):
        pool = self._make_pool()
        h1 = MemoryHeuristic(
            name="compress_large", priority=0.5, condition=lambda m: True, action=lambda m: 1
        )
        h2 = MemoryHeuristic(
            name="compress_small", priority=0.3, condition=lambda m: True, action=lambda m: 1
        )
        h3 = MemoryHeuristic(
            name="evict_old", priority=0.7, condition=lambda m: True, action=lambda m: 1
        )
        pool.register(h1)
        pool.register(h2)
        pool.register(h3)

        results = pool.find("compress")
        assert len(results) == 2

    def test_find_case_insensitive(self):
        pool = self._make_pool()
        h = MemoryHeuristic(
            name="COMPRESS", priority=0.5, condition=lambda m: True, action=lambda m: 1
        )
        pool.register(h)
        assert len(pool.find("compress")) == 1

    def test_apply_total_affected(self):
        pool = self._make_pool()
        h1 = MemoryHeuristic(name="a", priority=1.0, condition=lambda m: True, action=lambda m: 3)
        h2 = MemoryHeuristic(name="b", priority=0.5, condition=lambda m: True, action=lambda m: 5)
        pool.register(h1)
        pool.register(h2)

        affected = pool.apply(self._make_module(), max_heuristics=2)
        assert affected == 8

    def test_heuristics_property_returns_list(self):
        pool = self._make_pool()
        h = MemoryHeuristic(name="h1", priority=0.5, condition=lambda m: True, action=lambda m: 1)
        pool.register(h)
        assert len(pool.heuristics) == 1
        assert pool.heuristics[0].name == "h1"
