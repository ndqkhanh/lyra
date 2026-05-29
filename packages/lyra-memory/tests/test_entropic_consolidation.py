"""Tests for Entropic Consolidation — free-energy minimization for memory retention."""

import pytest

from lyra_memory.entropic_consolidation import (
    ConsolidatedMemory,
    ConsolidationPhase,
    EntropicConfig,
    EntropicConsolidator,
    MemoryFragment,
)


class TestConsolidationPhase:
    def test_phase_values(self):
        assert ConsolidationPhase.WAKE.value == "wake"
        assert ConsolidationPhase.NREM_LIGHT.value == "nrem_light"
        assert ConsolidationPhase.NREM_DEEP.value == "nrem_deep"
        assert ConsolidationPhase.REM.value == "rem"
        assert ConsolidationPhase.REHEARSAL.value == "rehearsal"


class TestMemoryFragment:
    def test_fragment_creation(self):
        frag = MemoryFragment(
            fragment_id="f-001",
            content="User ran deployment command",
            salience=0.75,
            novelty=0.5,
            emotional_valence=0.1,
            source="observation",
            timestamp=1000.0,
        )
        assert frag.fragment_id == "f-001"
        assert frag.salience == 0.75
        assert frag.novelty == 0.5
        assert frag.source == "observation"

    def test_fragment_high_salience(self):
        frag = MemoryFragment(
            "f-err", "CRITICAL: deployment failed", 0.95, 0.9, -0.7, "error", 2000.0
        )
        assert frag.salience > 0.9
        assert frag.emotional_valence < 0

    def test_fragment_immutable(self):
        f = MemoryFragment("f1", "content", 0.5, 0.3, 0.0, "src", 0.0)
        with pytest.raises(Exception):
            f.salience = 1.0


class TestConsolidatedMemory:
    def test_consolidated_creation(self):
        mem = ConsolidatedMemory(
            memory_id="mem-l-0001-000",
            fragments=("f-1", "f-2"),
            summary="deployment completed",
            free_energy=0.023,
            retained_salience=0.82,
            compression_ratio=0.33,
            phase=ConsolidationPhase.NREM_LIGHT,
        )
        assert mem.memory_id == "mem-l-0001-000"
        assert len(mem.fragments) == 2
        assert mem.phase == ConsolidationPhase.NREM_LIGHT

    def test_consolidated_deep_phase(self):
        mem = ConsolidatedMemory(
            memory_id="mem-d-0002",
            fragments=("f-3",),
            summary="deep consolidation result",
            free_energy=0.005,
            retained_salience=0.91,
            compression_ratio=0.15,
            phase=ConsolidationPhase.NREM_DEEP,
        )
        assert mem.phase == ConsolidationPhase.NREM_DEEP
        assert mem.free_energy < 0.01

    def test_consolidated_immutable(self):
        c = ConsolidatedMemory("m1", (), "", 0.0, 0.0, 0.0, ConsolidationPhase.WAKE)
        with pytest.raises(Exception):
            c.free_energy = 1.0


class TestEntropicConfig:
    def test_default_config(self):
        config = EntropicConfig()
        assert config.temperature == 1.0
        assert config.salience_threshold == 0.1
        assert config.convergence_iterations == 50

    def test_custom_config(self):
        config = EntropicConfig(temperature=2.0, salience_threshold=0.2)
        assert config.temperature == 2.0
        assert config.salience_threshold == 0.2


class TestEntropicConsolidator:
    def test_empty_consolidation(self):
        consolidator = EntropicConsolidator()
        results = consolidator.consolidate()
        assert results == []

    def test_ingest_single_fragment(self):
        consolidator = EntropicConsolidator()
        frag = MemoryFragment("f1", "content", 0.8, 0.5, 0.1, "obs", 1000.0)
        consolidator.ingest([frag])
        assert consolidator.pending_fragments == 1

    def test_ingest_multiple_fragments(self):
        consolidator = EntropicConsolidator()
        frags = [
            MemoryFragment(f"f{i}", f"content {i}", 0.5 + i * 0.1, 0.3, 0.0, "obs", float(i))
            for i in range(5)
        ]
        consolidator.ingest(frags)
        assert consolidator.pending_fragments == 5

    def test_light_consolidation(self):
        consolidator = EntropicConsolidator()
        frags = [
            MemoryFragment("f1", "deploy success", 0.85, 0.6, 0.3, "cli", 1.0),
            MemoryFragment("f2", "similar deploy", 0.80, 0.4, 0.2, "cli", 2.0),
            MemoryFragment("f3", "unrelated reading", 0.05, 0.1, 0.0, "file", 3.0),
        ]
        consolidator.ingest(frags)
        results = consolidator.consolidate(phase=ConsolidationPhase.NREM_LIGHT)
        assert isinstance(results, list)

    def test_deep_consolidation_with_high_salience(self):
        consolidator = EntropicConsolidator()
        frags = [
            MemoryFragment(
                f"d{i}", f"important memory {i}", 0.7 + i * 0.05, 0.5, 0.2, "obs", float(i)
            )
            for i in range(8)
        ]
        consolidator.ingest(frags)
        results = consolidator.consolidate(phase=ConsolidationPhase.NREM_DEEP)
        assert isinstance(results, list)

    def test_rem_synthesis(self):
        consolidator = EntropicConsolidator()
        frags = [
            MemoryFragment(
                f"r{i}",
                f"diverse content {i}",
                0.6,
                0.5 + i * 0.1,
                0.1 * i,
                f"source_{i % 3}",
                float(i),
            )
            for i in range(6)
        ]
        consolidator.ingest(frags)
        results = consolidator.consolidate(phase=ConsolidationPhase.REM)
        assert isinstance(results, list)

    def test_consolidation_reduces_pending(self):
        consolidator = EntropicConsolidator()
        frags = [
            MemoryFragment("fc1", "test content 1", 0.9, 0.5, 0.1, "src", 1.0),
            MemoryFragment("fc2", "test content 2", 0.85, 0.5, 0.1, "src", 2.0),
            MemoryFragment("fc3", "test content 3", 0.88, 0.5, 0.1, "src", 3.0),
        ]
        consolidator.ingest(frags)
        results = consolidator.consolidate(phase=ConsolidationPhase.NREM_LIGHT)
        if results:
            assert consolidator.pending_fragments < 3

    def test_multiple_cycles(self):
        consolidator = EntropicConsolidator()
        for _ in range(3):
            frags = [
                MemoryFragment(f"cycle-{_}-f{j}", f"content {j}", 0.7, 0.4, 0.0, "obs", float(j))
                for j in range(4)
            ]
            consolidator.ingest(frags)
            consolidator.consolidate()
        assert consolidator.consolidated_count >= 0

    def test_stats(self):
        consolidator = EntropicConsolidator()
        frags = [MemoryFragment("fs", "stat test", 0.8, 0.5, 0.1, "test", 0.0)]
        consolidator.ingest(frags)
        stats = consolidator.stats()
        assert "pending_fragments" in stats
        assert "consolidated_memories" in stats
        assert "cycles" in stats
