"""Goal-driven mutation of agent behaviour through specification-guided evolution."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from .exceptions import GoalMutationError
from .hyper_agent import AgentGene, HyperAgent


@dataclass(frozen=True)
class GoalSpec:
    """A goal specification with constraints and success criteria."""

    goal_id: str
    description: str
    constraints: tuple[str, ...]
    success_criteria: tuple[str, ...]
    priority: float = 1.0


@dataclass(frozen=True)
class MutationStrategy:
    """A strategy describing how a mutation should be applied."""

    strategy_id: str
    mutation_type: str
    target_genes: tuple[str, ...]
    probability: float
    magnitude: float


@dataclass(frozen=True)
class GoalMutationResult:
    """Result of applying a goal-driven mutation to an agent."""

    goal: GoalSpec
    original: HyperAgent
    mutated: HyperAgent
    strategy_used: MutationStrategy
    success: bool


class GoalMutator:
    """Applies goal-driven mutations to HyperAgent genomes."""

    def __init__(self) -> None:
        self._random = secrets.SystemRandom()

    async def define_goal(
        self,
        description: str,
        constraints: list[str],
        criteria: list[str],
    ) -> GoalSpec:
        """Define a new goal specification."""
        goal_id = f"goal-{self._random.randint(100000, 999999)}"
        return GoalSpec(
            goal_id=goal_id,
            description=description,
            constraints=tuple(constraints),
            success_criteria=tuple(criteria),
            priority=1.0,
        )

    async def generate_strategies(
        self, goal: GoalSpec
    ) -> tuple[MutationStrategy, ...]:
        """Generate mutation strategies based on a goal specification."""
        if not goal.success_criteria:
            raise GoalMutationError("Goal has no success criteria to derive strategies")

        strategies: list[MutationStrategy] = []
        for i, criterion in enumerate(goal.success_criteria):
            trait = criterion.lower().replace(" ", "_")
            strategy_id = f"strat-{goal.goal_id}-{i}"
            strategies.append(MutationStrategy(
                strategy_id=strategy_id,
                mutation_type="boost",
                target_genes=(trait,),
                probability=0.5 + (0.1 * i),
                magnitude=0.1 + (0.05 * i),
            ))
        return tuple(strategies)

    async def apply_mutation(
        self,
        agent: HyperAgent,
        goal: GoalSpec,
        strategy: MutationStrategy,
    ) -> GoalMutationResult:
        """Apply a single mutation strategy to a HyperAgent."""
        if not agent.genome:
            mutated = HyperAgent(
                agent_id=agent.agent_id,
                genome=(),
                fitness=agent.fitness,
                generation=agent.generation,
                lineage=agent.lineage,
            )
            return GoalMutationResult(
                goal=goal,
                original=agent,
                mutated=mutated,
                strategy_used=strategy,
                success=False,
            )

        mutated_genes: list[AgentGene] = []
        for gene in agent.genome:
            if gene.trait in strategy.target_genes or not strategy.target_genes:
                if self._random.random() < strategy.probability:
                    delta = strategy.magnitude * self._random.uniform(-1.0, 1.0)
                    new_value = max(
                        gene.min_bound,
                        min(gene.max_bound, gene.value + delta),
                    )
                    mutated_genes.append(AgentGene(
                        gene_id=gene.gene_id,
                        trait=gene.trait,
                        value=new_value,
                        min_bound=gene.min_bound,
                        max_bound=gene.max_bound,
                    ))
                else:
                    mutated_genes.append(gene)
            else:
                mutated_genes.append(gene)

        success = any(
            mg.value != og.value
            for mg, og in zip(mutated_genes, agent.genome, strict=False)
        )

        mutated = HyperAgent(
            agent_id=agent.agent_id,
            genome=tuple(mutated_genes),
            fitness=agent.fitness,
            generation=agent.generation,
            lineage=agent.lineage,
        )
        return GoalMutationResult(
            goal=goal,
            original=agent,
            mutated=mutated,
            strategy_used=strategy,
            success=success,
        )

    async def multi_objective_mutate(
        self,
        agent: HyperAgent,
        goals: tuple[GoalSpec, ...],
    ) -> HyperAgent:
        """Apply mutations from multiple goals sequentially."""
        if not goals:
            raise GoalMutationError("No goals provided for multi-objective mutation")

        result = agent
        for goal in goals:
            strategies = await self.generate_strategies(goal)
            if not strategies:
                continue
            strategy = strategies[0]
            mutation_result = await self.apply_mutation(result, goal, strategy)
            result = mutation_result.mutated
        return result
