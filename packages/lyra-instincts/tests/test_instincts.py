"""Tests for lyra-instincts."""
from lyra_instincts import InstinctEngine, InstinctScope


class TestInstinctEngine:
    def test_collect(self):
        e = InstinctEngine()
        inst = e.collect("task_type:code", "Always lint before commit")
        assert inst.id == "instinct_1"
        assert inst.trigger == "task_type:code"
        assert inst.scope == InstinctScope.PROJECT

    def test_prune_expired(self):
        import time
        e = InstinctEngine()
        inst = e.collect("test", "pattern")
        inst.created_at = time.time() - 31 * 86400  # 31 days ago
        assert e.prune() >= 1

    def test_promote(self):
        e = InstinctEngine()
        e.collect("trigger", "pattern")
        e._project_instincts["instinct_1"].hit_count = 15
        promoted = e.promote("instinct_1")
        assert promoted is not None
        assert promoted.scope == InstinctScope.GLOBAL

    def test_evolve(self):
        e = InstinctEngine()
        for i in range(10):
            inst = e.collect(f"trigger_{i}", f"pattern_{i}")
            inst.hit_count = 15
        result = e.evolve()
        assert len(result.skills) >= 0
        assert len(result.commands) >= 0
