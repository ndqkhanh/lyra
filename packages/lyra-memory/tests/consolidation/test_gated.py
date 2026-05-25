"""Tests for GatedMemory, GateConfig, and ConsolidationGate."""

from lyra_memory.consolidation.gated import (
    ConsolidationGate,
    GateConfig,
    GatedMemory,
)


class TestGatedMemory:
    def test_default_values(self):
        gm = GatedMemory(content="test", importance=0.7)
        assert gm.content == "test"
        assert gm.importance == 0.7
        assert gm.source == ""
        assert gm.passed is False
        assert len(gm.id) > 0

    def test_with_source(self):
        gm = GatedMemory(content="test", importance=0.5, source="stm")
        assert gm.source == "stm"

    def test_unique_ids(self):
        gm1 = GatedMemory(content="a", importance=0.5)
        gm2 = GatedMemory(content="b", importance=0.5)
        assert gm1.id != gm2.id

    def test_timestamp_is_set(self):
        gm = GatedMemory(content="test", importance=0.5)
        assert len(gm.timestamp) > 0


class TestGateConfig:
    def test_default_values(self):
        config = GateConfig()
        assert config.threshold == 0.5
        assert config.cooldown_cycles == 3
        assert config.max_batch == 100

    def test_custom_values(self):
        config = GateConfig(threshold=0.8, cooldown_cycles=5, max_batch=50)
        assert config.threshold == 0.8
        assert config.cooldown_cycles == 5
        assert config.max_batch == 50


class TestConsolidationGate:
    def test_initial_state(self):
        gate = ConsolidationGate()
        assert gate.pool_size == 0
        assert gate.consolidated_count == 0
        assert gate.cycle == 0
        assert gate.pass_rate == 0.0

    def test_submit_returns_gated_memory(self):
        gate = ConsolidationGate()
        mem = gate.submit("hello", importance=0.6)
        assert isinstance(mem, GatedMemory)
        assert mem.content == "hello"
        assert gate.pool_size == 1

    def test_submit_not_immediately_passed(self):
        gate = ConsolidationGate()
        mem = gate.submit("test", importance=0.6)
        assert mem.passed is False

    def test_consolidate_passes_above_threshold(self):
        gate = ConsolidationGate()
        gate.submit("important", importance=0.8)
        passed = gate.consolidate()
        assert len(passed) == 1
        assert passed[0].passed is True
        assert gate.consolidated_count == 1

    def test_consolidate_blocks_below_threshold(self):
        gate = ConsolidationGate()
        gate.submit("not important", importance=0.3)
        passed = gate.consolidate()
        assert len(passed) == 0
        assert gate.pass_rate == 0.0

    def test_consolidate_mixed_batch(self):
        gate = ConsolidationGate()
        gate.submit("high", importance=0.9)
        gate.submit("low", importance=0.2)
        gate.submit("mid", importance=0.5)
        passed = gate.consolidate()
        assert len(passed) == 2
        assert gate.pass_rate == 2 / 3

    def test_cooldown_blocks_consolidation(self):
        gate = ConsolidationGate()
        gate.submit("a", importance=0.9)
        passed = gate.consolidate()
        assert len(passed) == 1
        gate.submit("b", importance=0.9)
        passed = gate.consolidate()
        assert len(passed) == 0

    def test_cycle_increments(self):
        gate = ConsolidationGate()
        gate.consolidate()
        gate.consolidate()
        assert gate.cycle == 2

    def test_pool_size_tracks_submissions(self):
        gate = ConsolidationGate()
        for i in range(5):
            gate.submit(f"m{i}", importance=0.5)
        assert gate.pool_size == 5

    def test_custom_config_threshold(self):
        config = GateConfig(threshold=0.9)
        gate = ConsolidationGate(config=config)
        gate.submit("barely", importance=0.8)
        passed = gate.consolidate()
        assert len(passed) == 0

    def test_custom_config_cooldown(self):
        config = GateConfig(cooldown_cycles=2)
        gate = ConsolidationGate(config=config)
        gate.submit("a", importance=0.9)
        gate.consolidate()
        gate.submit("b", importance=0.9)
        passed = gate.consolidate()
        assert len(passed) == 0
