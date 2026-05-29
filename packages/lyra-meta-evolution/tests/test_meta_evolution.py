"""Tests for lyra_meta_evolution.meta_evolution module."""

import asyncio

import pytest
from lyra_meta_evolution.meta_evolution import (
    AgentGenome,
    ArchitectureController,
    ConvergenceStatus,
    EvolutionConfig,
    EvolutionLevel,
    EvolutionResult,
    EvolutionState,
    EvolutionTrigger,
    GoalController,
    MetaCognitiveStack,
    ParameterController,
    StrategyController,
)

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def genome():
    return AgentGenome(
        agent_id="test_agent",
        hyperparameters={"learning_rate": 0.001, "temperature": 0.7},
        active_strategies=["greedy", "exploration"],
        objective_weights={"speed": 0.3, "quality": 0.3, "cost": 0.2, "reliability": 0.2},
    )


@pytest.fixture
def meta_stack():
    return MetaCognitiveStack()


# ── AgentGenome ─────────────────────────────────────────────────────────────────


class TestAgentGenome:
    def test_default_creation(self):
        g = AgentGenome(agent_id="g1")
        assert g.agent_id == "g1"
        assert g.generation == 0
        assert g.hyperparameters == {}
        assert g.active_strategies == []

    def test_clone_creates_new_id(self, genome):
        cloned = genome.clone()
        assert cloned.agent_id != genome.agent_id
        assert cloned.parent_ids == [genome.agent_id]
        assert cloned.hyperparameters == genome.hyperparameters

    def test_clone_with_custom_id(self, genome):
        cloned = genome.clone(new_id="custom_id")
        assert cloned.agent_id == "custom_id"

    def test_to_dict_from_dict_roundtrip(self, genome):
        d = genome.to_dict()
        restored = AgentGenome.from_dict(d)
        assert restored.agent_id == genome.agent_id
        assert restored.hyperparameters == genome.hyperparameters
        assert restored.active_strategies == genome.active_strategies

    def test_fitness_history(self, genome):
        genome.fitness_history.append(0.5)
        genome.fitness_history.append(0.7)
        assert genome.fitness_history == [0.5, 0.7]


# ── Level Controllers ───────────────────────────────────────────────────────────


class TestParameterController:
    def test_config_level(self):
        ctrl = ParameterController()
        assert ctrl.config.level == EvolutionLevel.L1_PARAMETER
        assert isinstance(ctrl.state, EvolutionState)

    def test_evolve_modifies_hyperparameters(self, genome):
        controller = ParameterController()
        result = asyncio.run(controller.evolve(genome, EvolutionTrigger.SCHEDULED_REVIEW))
        assert isinstance(result, EvolutionResult)
        assert result.level == EvolutionLevel.L1_PARAMETER

    def test_is_ready(self, genome):
        controller = ParameterController()
        assert controller.is_ready() is True

    def test_disabled_not_ready(self):
        config = EvolutionConfig(level=EvolutionLevel.L1_PARAMETER, enabled=False)
        controller = ParameterController(config=config)
        assert controller.is_ready() is False

    def test_checkpoint_and_rollback(self, genome):
        controller = ParameterController()
        asyncio.run(controller.evolve(genome, EvolutionTrigger.SCHEDULED_REVIEW))
        controller.checkpoint()
        asyncio.run(controller.evolve(genome, EvolutionTrigger.SCHEDULED_REVIEW))
        assert controller.rollback() is True

    def test_rollback_without_checkpoint(self):
        controller = ParameterController()
        assert controller.rollback() is False

    def test_custom_parameter_bounds(self):
        controller = ParameterController(parameter_bounds={"custom_param": (0.0, 10.0)})
        assert "custom_param" in controller.parameter_bounds


class TestStrategyController:
    def test_config_level(self):
        ctrl = StrategyController()
        assert ctrl.config.level == EvolutionLevel.L2_STRATEGY
        assert isinstance(ctrl.state, EvolutionState)

    def test_evolve_modifies_strategies(self, genome):
        controller = StrategyController()
        result = asyncio.run(controller.evolve(genome, EvolutionTrigger.SCHEDULED_REVIEW))
        assert isinstance(result, EvolutionResult)
        assert result.level == EvolutionLevel.L2_STRATEGY


class TestArchitectureController:
    def test_evolve_builds_graph(self, genome):
        controller = ArchitectureController()
        result = asyncio.run(controller.evolve(genome, EvolutionTrigger.SCHEDULED_REVIEW))
        assert isinstance(result, EvolutionResult)
        assert result.level == EvolutionLevel.L3_ARCHITECTURE
        assert len(genome.component_graph) > 0


class TestGoalController:
    def test_config_level(self):
        ctrl = GoalController()
        assert ctrl.config.level == EvolutionLevel.L4_GOAL
        assert isinstance(ctrl.state, EvolutionState)

    def test_evolve_modifies_objectives(self, genome):
        controller = GoalController()
        result = asyncio.run(controller.evolve(genome, EvolutionTrigger.SCHEDULED_REVIEW))
        assert isinstance(result, EvolutionResult)
        assert result.level == EvolutionLevel.L4_GOAL

    def test_weights_normalized_after_evolve(self, genome):
        controller = GoalController()
        asyncio.run(controller.evolve(genome, EvolutionTrigger.PERFORMANCE_DEGRADATION))
        total = sum(genome.objective_weights.values())
        assert abs(total - 1.0) < 0.001


# ── MetaCognitiveStack ──────────────────────────────────────────────────────────


class TestMetaCognitiveStack:
    def test_process_failure(self, meta_stack):
        result = asyncio.run(meta_stack.process_failure({
            "error": "timeout occurred",
            "agent_id": "agent_1",
            "task": "test_task",
        }))
        assert "failure" in result
        assert "actions" in result
        assert len(result["actions"]) > 0

    def test_process_failure_unknown_error(self, meta_stack):
        result = asyncio.run(meta_stack.process_failure({
            "error": "something_weird_happened",
        }))
        assert "actions" in result

    def test_process_failure_quality_error(self, meta_stack):
        result = asyncio.run(meta_stack.process_failure({
            "error": "quality_threshold_not_met",
            "task": "revise output",
        }))
        assert len(result["actions"]) > 0

    def test_evolve_runs_single_level(self, meta_stack, genome):
        result = asyncio.run(meta_stack.evolve(
            genome, EvolutionTrigger.SCHEDULED_REVIEW,
            target_level=EvolutionLevel.L1_PARAMETER,
        ))
        assert result.level == EvolutionLevel.L1_PARAMETER

    def test_evolve_all_levels(self, meta_stack, genome):
        results = asyncio.run(meta_stack.evolve_all_levels(genome))
        assert len(results) > 0
        assert all(isinstance(r, EvolutionResult) for r in results)

    def test_summary_returns_dict(self, meta_stack):
        s = meta_stack.summary
        assert "states" in s
        assert "total_evolutions" in s
        assert "genomes_tracked" in s
        assert "converged_levels" in s

    def test_get_controller(self, meta_stack):
        ctrl = meta_stack.get_controller(EvolutionLevel.L1_PARAMETER)
        assert isinstance(ctrl, ParameterController)

    def test_get_all_states(self, meta_stack):
        states = meta_stack.get_all_states()
        assert EvolutionLevel.L1_PARAMETER in states
        assert EvolutionLevel.L4_GOAL in states

    def test_checkpoint_all(self, meta_stack, genome):
        asyncio.run(meta_stack.evolve(
            genome, EvolutionTrigger.SCHEDULED_REVIEW,
            EvolutionLevel.L1_PARAMETER,
        ))
        checkpoints = meta_stack.checkpoint_all()
        assert EvolutionLevel.L1_PARAMETER in checkpoints

    def test_reset_level(self, meta_stack):
        meta_stack.reset_level(EvolutionLevel.L2_STRATEGY)
        state = meta_stack.get_state(EvolutionLevel.L2_STRATEGY)
        assert state.iteration == 0
        assert state.status == ConvergenceStatus.NOT_STARTED

    def test_history_accumulates(self, meta_stack, genome):
        asyncio.run(meta_stack.evolve(
            genome, EvolutionTrigger.SCHEDULED_REVIEW,
            EvolutionLevel.L1_PARAMETER,
        ))
        assert len(meta_stack.history) == 1

    def test_genome_count(self, meta_stack, genome):
        asyncio.run(meta_stack.evolve(
            genome, EvolutionTrigger.SCHEDULED_REVIEW,
            EvolutionLevel.L1_PARAMETER,
        ))
        assert meta_stack.genome_count == 1


# ── EvolutionConfig ─────────────────────────────────────────────────────────────


class TestEvolutionConfig:
    def test_default_values(self):
        config = EvolutionConfig(level=EvolutionLevel.L1_PARAMETER)
        assert config.max_iterations == 100
        assert config.convergence_threshold > 0
        assert config.stagnation_patience > 0
