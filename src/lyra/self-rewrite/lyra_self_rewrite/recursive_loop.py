"""Recursive self-improvement loop — evolves a population until convergence."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import ConvergenceError, RecursionError
from .fitness_evaluator import FitnessConfig, FitnessEvaluator
from .hyper_agent import (
    HyperAgent,
    HyperAgentConfig,
    HyperAgentEngine,
    Population,
)


@dataclass(frozen=True)
class LoopConfig:
    """Configuration governing the recursive self-improvement loop."""

    max_iterations: int = 10
    convergence_threshold: float = 0.01
    improvement_min_delta: float = 0.001
    stagnation_limit: int = 3


@dataclass(frozen=True)
class LoopIteration:
    """A single iteration snapshot from the recursive loop."""

    iteration: int
    population: Population
    best_fitness: float
    improvement_delta: float
    converged: bool


@dataclass(frozen=True)
class LoopResult:
    """Final result of the recursive self-improvement loop."""

    iterations: tuple[LoopIteration, ...]
    final_population: Population
    champion: HyperAgent
    converged: bool
    total_cycles: int
    final_fitness: float


class RecursiveLoop:
    """Drives the recursive self-improvement loop over generations."""

    def __init__(
        self,
        engine: HyperAgentEngine | None = None,
        evaluator: FitnessEvaluator | None = None,
    ) -> None:
        self._engine = engine or HyperAgentEngine()
        self._evaluator = evaluator or FitnessEvaluator()
        self._fitness_config = FitnessConfig()

    async def run_loop(
        self,
        initial_pop: Population,
        config: LoopConfig,
    ) -> LoopResult:
        """Run the recursive self-improvement loop until convergence or max iterations."""
        if not initial_pop.agents:
            raise RecursionError("Cannot start loop with an empty population")

        hyper_config = HyperAgentConfig(
            population_size=len(initial_pop.agents),
        )

        pop = initial_pop
        iterations: list[LoopIteration] = []
        previous_best = 0.0
        stagnation_counter = 0

        for iteration in range(config.max_iterations):
            # Evaluate fitness for all agents
            agents = list(pop.agents)
            for i, agent in enumerate(agents):
                score = await self._evaluator.evaluate(agent, self._fitness_config)
                agents[i] = HyperAgent(
                    agent_id=agent.agent_id,
                    genome=agent.genome,
                    fitness=score.weighted_total,
                    generation=agent.generation,
                    lineage=agent.lineage,
                )
            pop = Population(
                agents=tuple(agents),
                generation=pop.generation,
                best_fitness=max(a.fitness for a in agents),
                avg_fitness=sum(a.fitness for a in agents) / len(agents),
                diversity=pop.diversity,
            )

            best_fitness = max(a.fitness for a in agents)
            improvement_delta = best_fitness - previous_best

            converged = await self.check_convergence(
                tuple(iterations), config.convergence_threshold
            )

            iterations.append(LoopIteration(
                iteration=iteration,
                population=pop,
                best_fitness=best_fitness,
                improvement_delta=improvement_delta,
                converged=converged,
            ))

            if converged:
                break

            # Check stagnation
            if improvement_delta < config.improvement_min_delta:
                stagnation_counter += 1
            else:
                stagnation_counter = 0

            if stagnation_counter >= config.stagnation_limit:
                if iteration == 0:
                    raise ConvergenceError(
                        "Loop stagnated at the first iteration"
                    )
                break

            previous_best = best_fitness

            # Evolve to next generation
            pop = await self._engine.evolve_population(pop, hyper_config)

        # Determine champion
        champion = max(
            pop.agents, key=lambda a: a.fitness
        )

        return LoopResult(
            iterations=tuple(iterations),
            final_population=pop,
            champion=champion,
            converged=iterations[-1].converged if iterations else False,
            total_cycles=len(iterations),
            final_fitness=champion.fitness,
        )

    async def check_convergence(
        self,
        history: tuple[LoopIteration, ...],
        threshold: float,
    ) -> bool:
        """Check if the loop has converged based on recent improvement history."""
        if len(history) < 2:
            return False

        recent = history[-3:] if len(history) >= 3 else history
        # If improvement deltas have all been below threshold, we have converged
        for iteration in recent:
            if iteration.improvement_delta >= threshold:
                return False
        return True

    async def detect_stagnation(
        self,
        history: tuple[LoopIteration, ...],
        limit: int,
    ) -> bool:
        """Detect whether the loop has stagnated."""
        if len(history) < limit + 1:
            return False

        recent = history[-(limit + 1):]
        improvements = [
            recent[i + 1].best_fitness - recent[i].best_fitness
            for i in range(len(recent) - 1)
        ]
        # Check if all recent improvements are effectively zero
        return all(abs(delta) < 1e-10 for delta in improvements)
