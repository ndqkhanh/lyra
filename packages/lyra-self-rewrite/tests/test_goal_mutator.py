"""Tests for the goal-driven mutation module."""

from __future__ import annotations

import pytest

from lyra_self_rewrite.exceptions import GoalMutationError
from lyra_self_rewrite.goal_mutator import (
    GoalMutationResult,
    GoalMutator,
    GoalSpec,
    MutationStrategy,
)
from lyra_self_rewrite.hyper_agent import AgentGene, HyperAgent


def _make_agent(agent_id: str = "a1") -> HyperAgent:
    genes = (
        AgentGene("g1", "speed", 0.5, 0.0, 1.0),
        AgentGene("g2", "creativity", 0.3, 0.0, 1.0),
        AgentGene("g3", "thoroughness", 0.7, 0.0, 1.0),
    )
    return HyperAgent(
        agent_id=agent_id,
        genome=genes,
        fitness=0.5,
        generation=0,
        lineage=(agent_id,),
    )


class TestGoalSpec:
    def test_goal_spec_creation(self) -> None:
        goal = GoalSpec(
            goal_id="g1",
            description="Improve speed",
            constraints=("no slowdown",),
            success_criteria=("faster",),
            priority=1.0,
        )
        assert goal.goal_id == "g1"
        assert goal.priority == 1.0
        assert len(goal.constraints) == 1

    def test_goal_spec_frozen(self) -> None:
        goal = GoalSpec("g1", "desc", (), ())
        with pytest.raises(AttributeError):
            goal.priority = 2.0  # type: ignore[misc]

    def test_goal_spec_default_priority(self) -> None:
        goal = GoalSpec("g1", "desc", ("c1",), ("s1",))
        assert goal.priority == 1.0

    def test_goal_spec_empty_constraints(self) -> None:
        goal = GoalSpec("g1", "desc", (), ())
        assert goal.constraints == ()
        assert goal.success_criteria == ()


class TestMutationStrategy:
    def test_strategy_creation(self) -> None:
        strat = MutationStrategy(
            strategy_id="s1",
            mutation_type="boost",
            target_genes=("speed",),
            probability=0.8,
            magnitude=0.2,
        )
        assert strat.strategy_id == "s1"
        assert strat.mutation_type == "boost"
        assert strat.probability == 0.8

    def test_strategy_frozen(self) -> None:
        strat = MutationStrategy("s1", "boost", ("speed",), 0.5, 0.1)
        with pytest.raises(AttributeError):
            strat.probability = 0.9  # type: ignore[misc]

    def test_strategy_zero_probability(self) -> None:
        strat = MutationStrategy("s1", "boost", (), 0.0, 0.0)
        assert strat.probability == 0.0
        assert strat.magnitude == 0.0


class TestGoalMutationResult:
    def test_mutation_result_creation(self) -> None:
        goal = GoalSpec("g1", "desc", (), ())
        agent = _make_agent()
        strat = MutationStrategy("s1", "boost", ("speed",), 0.5, 0.1)
        result = GoalMutationResult(
            goal=goal,
            original=agent,
            mutated=agent,
            strategy_used=strat,
            success=True,
        )
        assert result.success
        assert result.original.agent_id == "a1"

    def test_mutation_result_frozen(self) -> None:
        goal = GoalSpec("g1", "desc", (), ())
        agent = _make_agent()
        strat = MutationStrategy("s1", "boost", (), 0.5, 0.1)
        result = GoalMutationResult(goal, agent, agent, strat, False)
        with pytest.raises(AttributeError):
            result.success = True  # type: ignore[misc]

    def test_mutation_result_failed_mutation(self) -> None:
        goal = GoalSpec("g1", "desc", (), ())
        agent = _make_agent()
        strat = MutationStrategy("s1", "boost", (), 0.0, 0.0)
        result = GoalMutationResult(goal, agent, agent, strat, False)
        assert not result.success


class TestGoalMutator:
    @pytest.mark.asyncio
    async def test_define_goal(self) -> None:
        mutator = GoalMutator()
        goal = await mutator.define_goal(
            description="Optimize performance",
            constraints=["no regression"],
            criteria=["speedup", "memory_reduction"],
        )
        assert "goal-" in goal.goal_id
        assert goal.description == "Optimize performance"
        assert len(goal.constraints) == 1
        assert len(goal.success_criteria) == 2

    @pytest.mark.asyncio
    async def test_define_goal_empty_criteria(self) -> None:
        mutator = GoalMutator()
        goal = await mutator.define_goal(
            description="test", constraints=[], criteria=[]
        )
        assert goal.success_criteria == ()

    @pytest.mark.asyncio
    async def test_generate_strategies(self) -> None:
        mutator = GoalMutator()
        goal = await mutator.define_goal(
            description="Improve speed",
            constraints=["safe"],
            criteria=["faster", "cleaner"],
        )
        strategies = await mutator.generate_strategies(goal)
        assert len(strategies) == 2
        assert strategies[0].mutation_type == "boost"

    @pytest.mark.asyncio
    async def test_generate_strategies_no_criteria_raises(self) -> None:
        mutator = GoalMutator()
        goal = GoalSpec("g1", "desc", (), ())
        with pytest.raises(GoalMutationError, match="no success criteria"):
            await mutator.generate_strategies(goal)

    @pytest.mark.asyncio
    async def test_generate_strategies_strategy_has_target_genes(self) -> None:
        mutator = GoalMutator()
        goal = GoalSpec("g1", "desc", (), ("Speed Up",))
        strategies = await mutator.generate_strategies(goal)
        assert len(strategies) == 1
        assert "speed_up" in strategies[0].target_genes

    @pytest.mark.asyncio
    async def test_apply_mutation(self) -> None:
        mutator = GoalMutator()
        agent = _make_agent()
        goal = GoalSpec("g1", "desc", (), ("speed",))
        strat = MutationStrategy("s1", "boost", ("speed",), 1.0, 0.5)
        result = await mutator.apply_mutation(agent, goal, strat)
        assert result.goal.goal_id == "g1"
        assert result.strategy_used.strategy_id == "s1"

    @pytest.mark.asyncio
    async def test_apply_mutation_updates_gene_value(self) -> None:
        mutator = GoalMutator()
        agent = _make_agent()
        goal = GoalSpec("g1", "desc", (), ("speed",))
        strat = MutationStrategy("s1", "boost", ("speed",), 1.0, 0.5)
        result = await mutator.apply_mutation(agent, goal, strat)
        # With probability=1.0 and non-zero magnitude, value should change
        assert any(
            mo.value != orig.value
            for mo, orig in zip(result.mutated.genome, agent.genome)
        )

    @pytest.mark.asyncio
    async def test_apply_mutation_empty_genome(self) -> None:
        mutator = GoalMutator()
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        goal = GoalSpec("g1", "desc", (), ("speed",))
        strat = MutationStrategy("s1", "boost", ("speed",), 1.0, 0.5)
        result = await mutator.apply_mutation(agent, goal, strat)
        assert not result.success

    @pytest.mark.asyncio
    async def test_multi_objective_mutate(self) -> None:
        mutator = GoalMutator()
        agent = _make_agent()
        goals = (
            GoalSpec("g1", "Speed up", ("safe",), ("faster",)),
            GoalSpec("g2", "Clean code", ("style",), ("readable",)),
        )
        result = await mutator.multi_objective_mutate(agent, goals)
        assert result.agent_id == "a1"
        assert len(result.genome) == 3

    @pytest.mark.asyncio
    async def test_multi_objective_mutate_no_goals_raises(self) -> None:
        mutator = GoalMutator()
        agent = _make_agent()
        with pytest.raises(GoalMutationError, match="No goals provided"):
            await mutator.multi_objective_mutate(agent, ())

    @pytest.mark.asyncio
    async def test_multi_objective_mutate_single_goal(self) -> None:
        mutator = GoalMutator()
        agent = _make_agent()
        goals = (GoalSpec("g1", "test", ("c1",), ("faster",)),)
        result = await mutator.multi_objective_mutate(agent, goals)
        assert result.agent_id == "a1"

    @pytest.mark.asyncio
    async def test_multi_objective_mutate_many_goals(self) -> None:
        mutator = GoalMutator()
        agent = _make_agent()
        goals = tuple(
            GoalSpec(f"g{i}", f"Goal {i}", ("c1",), ("criterion",))
            for i in range(5)
        )
        result = await mutator.multi_objective_mutate(agent, goals)
        assert result.agent_id == "a1"

    @pytest.mark.asyncio
    async def test_apply_mutation_with_zero_probability(self) -> None:
        mutator = GoalMutator()
        agent = _make_agent()
        goal = GoalSpec("g1", "desc", (), ("speed",))
        strat = MutationStrategy("s1", "boost", ("speed",), 0.0, 0.5)
        result = await mutator.apply_mutation(agent, goal, strat)
        # With probability 0, no changes should happen
        assert all(
            mo.value == orig.value
            for mo, orig in zip(result.mutated.genome, agent.genome)
        )

    @pytest.mark.asyncio
    async def test_apply_mutation_mutates_value_within_bounds(self) -> None:
        mutator = GoalMutator()
        # Create agent at boundary
        genes = (AgentGene("g1", "speed", 0.0, 0.0, 1.0),)
        agent = HyperAgent("a1", genes, 0.0, 0, ("a1",))
        goal = GoalSpec("g1", "desc", (), ("speed",))
        strat = MutationStrategy("s1", "boost", ("speed",), 1.0, -0.5)
        result = await mutator.apply_mutation(agent, goal, strat)
        # Value should be clamped to valid range
        assert result.mutated.genome[0].value >= 0.0

    @pytest.mark.asyncio
    async def test_generate_strategies_different_criteria(self) -> None:
        mutator = GoalMutator()
        goal = GoalSpec("g1", "desc", (), ("a", "b", "c"))
        strategies = await mutator.generate_strategies(goal)
        assert len(strategies) == 3
        # Probabilities should be different for each
        assert strategies[0].probability != strategies[1].probability
