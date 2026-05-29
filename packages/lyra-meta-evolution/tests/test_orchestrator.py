"""Tests for lyra_meta_evolution.orchestrator module."""

import asyncio

import pytest
from lyra_meta_evolution.meta_evolution import (
    AgentGenome,
    EvolutionLevel,
)
from lyra_meta_evolution.orchestrator import (
    CycleConfig,
    CycleResult,
    EvolutionOrchestrator,
    OrchestratorSnapshot,
    OrchestratorStatus,
)

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def seed_genome():
    return AgentGenome(
        agent_id="seed_agent",
        hyperparameters={"learning_rate": 0.001, "temperature": 0.7},
        objective_weights={"speed": 0.3, "quality": 0.3, "cost": 0.2, "reliability": 0.2},
    )


@pytest.fixture
def cycle_config():
    return CycleConfig(
        max_cycles=5,
        cycles_per_level={
            EvolutionLevel.L1_PARAMETER: 3,
            EvolutionLevel.L2_STRATEGY: 2,
        },
        auto_promote=True,
        promote_threshold=0.001,  # Low threshold for testing
    )


@pytest.fixture
def orchestrator(cycle_config):
    return EvolutionOrchestrator(config=cycle_config)


# ── CycleConfig ─────────────────────────────────────────────────────────────────


class TestCycleConfig:
    def test_default_creation(self):
        config = CycleConfig()
        assert config.max_cycles == 50
        assert config.auto_promote is True

    def test_get_cycles(self):
        config = CycleConfig()
        assert config.get_cycles(EvolutionLevel.L1_PARAMETER) > 0


# ── EvolutionOrchestrator ───────────────────────────────────────────────────────


class TestEvolutionOrchestrator:
    def test_initial_status_is_idle(self, orchestrator):
        assert orchestrator.status == OrchestratorStatus.IDLE

    def test_run_cycle_returns_result(self, orchestrator, seed_genome):
        orchestrator._best_genome = seed_genome
        result = asyncio.run(orchestrator.run_cycle(EvolutionLevel.L1_PARAMETER))
        assert isinstance(result, CycleResult)
        assert result.level == EvolutionLevel.L1_PARAMETER

    def test_run_cycle_accumulates_history(self, orchestrator, seed_genome):
        orchestrator._best_genome = seed_genome
        asyncio.run(orchestrator.run_cycle(EvolutionLevel.L1_PARAMETER))
        assert len(orchestrator.cycle_history) == 1

    def test_get_status_returns_snapshot(self, orchestrator, seed_genome):
        orchestrator._best_genome = seed_genome
        snapshot = orchestrator.get_status()
        assert isinstance(snapshot, OrchestratorSnapshot)
        assert snapshot.status == OrchestratorStatus.IDLE

    def test_checkpoint_and_rollback(self, orchestrator, seed_genome):
        orchestrator._best_genome = seed_genome
        asyncio.run(orchestrator.run_cycle(EvolutionLevel.L1_PARAMETER))
        snapshot = asyncio.run(orchestrator.checkpoint())
        assert isinstance(snapshot, OrchestratorSnapshot)

        result = asyncio.run(orchestrator.rollback())
        assert result is True

    def test_rollback_without_checkpoint_raises(self, orchestrator):
        from lyra_meta_evolution.orchestrator import RollbackError
        with pytest.raises(RollbackError):
            asyncio.run(orchestrator.rollback())

    def test_export_best_genome_empty(self, orchestrator):
        exported = asyncio.run(orchestrator.export_best_genome())
        assert exported == {}

    def test_export_best_genome(self, orchestrator, seed_genome):
        orchestrator._best_genome = seed_genome
        orchestrator._best_fitness = 0.85
        exported = asyncio.run(orchestrator.export_best_genome())
        assert "genome" in exported
        assert exported["fitness"] == 0.85

    def test_integrate_with_evolution_package(self, orchestrator):
        data = {
            "agent_id": "imported_agent",
            "hyperparameters": {"lr": 0.01},
            "fitness": 0.75,
        }
        asyncio.run(orchestrator.integrate_with_evolution_package(data))
        assert orchestrator.best_genome is not None

    def test_properties(self, orchestrator, seed_genome):
        assert orchestrator.current_cycle == 0
        assert orchestrator.best_genome is None
        assert orchestrator.best_fitness == 0.0
        assert orchestrator.error_count == 0

    def test_run_pipeline_completes(self, orchestrator, seed_genome):
        """Pipeline should complete with a small cycle config."""
        results = asyncio.run(orchestrator.run_pipeline(seed_genome))
        assert len(results) > 0
        assert orchestrator.status == OrchestratorStatus.COMPLETED

    def test_stream_cycles(self, orchestrator, seed_genome):
        orchestrator._best_genome = seed_genome
        asyncio.run(orchestrator.run_cycle(EvolutionLevel.L1_PARAMETER))

        async def _collect():
            cycles = []
            async for cycle in orchestrator.stream_cycles():
                cycles.append(cycle)
            return cycles

        cycles = asyncio.run(_collect())
        assert len(cycles) > 0


# ── CycleResult ─────────────────────────────────────────────────────────────────


class TestCycleResult:
    def test_default_creation(self):
        result = CycleResult(
            cycle_id=1,
            level=EvolutionLevel.L1_PARAMETER,
            phase=None,
            generations_executed=0,
            fitness_before=0.5,
            fitness_after=0.6,
            improvement=0.1,
            best_genome_id="agent_1",
            promoted=False,
        )
        assert result.cycle_id == 1
        assert result.improvement == 0.1
