"""Tests for Meta Evolution package."""

import pytest
from lyra_meta_evolution import MetaCognitiveStack, Level0Executor, Level1Knowledge, Level2Harness, Level3MetaEvolution


class TestLevels:
    def test_l0_execute(self):
        l = Level0Executor()
        r = l.execute("test task")
        assert r["level"] == 0

    def test_l1_read_write(self):
        l = Level1Knowledge()
        l.write_skill("test", {"data": 42})
        assert l.read_skill("test") == {"data": 42}

    def test_l3_evolution(self):
        l = Level3MetaEvolution()
        s = l.evolve_strategy([{"success": True}, {"success": False}])
        assert s["generation"] == 1

    def test_l3_second_generation(self):
        l = Level3MetaEvolution()
        l.evolve_strategy([])
        s = l.evolve_strategy([{"success": True}])
        assert s["generation"] == 2


class TestMetaCognitiveStack:
    @pytest.mark.asyncio
    async def test_process_failure(self):
        stack = MetaCognitiveStack()
        result = await stack.process_failure({"error": "test failure", "task": "test"})
        assert "failure" in result
        assert "patch" in result

    def test_summary(self):
        stack = MetaCognitiveStack()
        s = stack.summary
        assert "generations" in s
        assert "patches" in s
