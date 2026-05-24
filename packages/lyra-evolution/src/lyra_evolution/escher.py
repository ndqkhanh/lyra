"""Escher-Loop Recursive Self-Improvement.

Two-population architecture:
- **Solver population**: generates candidate solutions.
- **Critic population**: evaluates and filters solutions.
Top solutions feed back into Solver training, enabling recursive
improvement through alternating generations.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable, Sequence

from .models import EscherGeneration, EscherSolver, EvolutionMetrics

logger = logging.getLogger(__name__)


class EscherLoop:
    """Recursive self-improvement via alternating solver + critic populations.

    Typical usage::

        loop = EscherLoop(population_size=50, top_k=10)
        best = loop.evolve(problem="<task>", generations=20)
    """

    def __init__(
        self,
        population_size: int = 50,
        top_k: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.5,
        *,
        seed: int | None = None,
    ) -> None:
        """Initialise the Escher Loop.

        Args:
            population_size: Number of solvers per generation.
            top_k: Survivors selected by the critic each generation.
            mutation_rate: Probability of mutating any single solution component.
            crossover_rate: Proportion of new solutions produced via crossover.
            seed: Optional RNG seed for reproducibility.
        """
        if population_size < 2:
            raise ValueError("population_size must be >= 2")
        if top_k < 1 or top_k > population_size:
            raise ValueError("top_k must be in [1, population_size]")

        self.population_size = population_size
        self.top_k = top_k
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self._rng = random.Random(seed)

        self._population: list[EscherSolver] = []
        self._generation: int = 0
        self._history: list[EscherGeneration] = []

    # ------------------------------------------------------------------
    # Population management
    # ------------------------------------------------------------------

    def initialize_population(self, size: int | None = None) -> list[EscherSolver]:
        """Create an initial random solver population.

        Args:
            size: Override the configured population_size.

        Returns:
            The initial population list.
        """
        n = size or self.population_size
        self._population = [
            EscherSolver(
                content=f"solver-seed-{i:04d}-{self._rng.randint(0, 9999)}",
                generation=0,
            )
            for i in range(n)
        ]
        logger.info("Initialised population of %d solvers", n)
        return list(self._population)

    @property
    def population(self) -> list[EscherSolver]:
        """Current solver population (read-only copy)."""
        return list(self._population)

    @property
    def generation(self) -> int:
        """Current generation index."""
        return self._generation

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def evolve(
        self,
        problem: str,
        generations: int = 20,
        *,
        evaluator: Callable[[EscherSolver], float] | None = None,
    ) -> EscherSolver:
        """Run the full recursive self-improvement loop.

        Args:
            problem: The problem to optimise against.
            generations: Number of generations to run.
            evaluator: Optional fitness function. Falls back to a heuristic
                       scorer when not provided.

        Returns:
            The best solver discovered across all generations.

        Raises:
            ValueError: If no initial population exists and none can be created.
        """
        if not self._population:
            self.initialize_population()

        _evaluate = evaluator or self._default_evaluator

        best_overall: EscherSolver | None = None
        best_score_overall = float("-inf")

        for gen in range(generations):
            self._generation = gen

            # --- Solver phase: generate solutions ---
            solutions = self.generate_solutions(self._population, problem)

            # --- Critic phase: evaluate ---
            scores = self.evaluate_solutions(solutions, _evaluate)

            # Record generation snapshot
            gen_snapshot = EscherGeneration(
                solutions=tuple(solutions),
                scores=tuple(scores),
                generation_number=gen,
            )
            self._history.append(gen_snapshot)

            # Track best
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            if scores[best_idx] > best_score_overall:
                best_score_overall = scores[best_idx]
                best_overall = solutions[best_idx]

            diversity = self.compute_diversity(solutions)
            prev_best_score = (
                max(self._history[-2].scores) if len(self._history) > 1 else 0.0
            )

            logger.info(
                "Gen %03d | avg=%.4f best=%.4f diversity=%.3f improvement=%.4f",
                gen,
                gen_snapshot.average_score,
                scores[best_idx],
                diversity,
                scores[best_idx] - prev_best_score,
            )

            # --- Select top ---
            survivors = self.select_top(solutions, self.top_k, scores)

            # --- Reproduce ---
            self._population = self._reproduce(survivors)

        if best_overall is None:
            raise RuntimeError("Evolution produced no solutions")

        logger.info(
            "Evolution complete. Best fitness=%.4f after %d generations",
            best_score_overall,
            generations,
        )
        return best_overall

    # ------------------------------------------------------------------
    # Solver phase
    # ------------------------------------------------------------------

    def generate_solutions(
        self,
        population: Sequence[EscherSolver],
        problem: str,
    ) -> list[EscherSolver]:
        """Generate candidate solutions for the given problem.

        Each solver in the population produces a solution. The default
        implementation is a placeholder; real deployments inject an LLM
        callable via the *evaluator* pathway or subclass override.

        Args:
            population: Current solver population.
            problem: Problem description.

        Returns:
            Fresh list of solutions (one per solver).
        """
        solutions: list[EscherSolver] = []
        for solver in population:
            solution = EscherSolver(
                content=f"solution to '{problem[:60]}' by {solver.solution_id}",
                fitness_score=0.0,
                parent_ids=(solver.solution_id,),
                generation=self._generation,
            )
            solutions.append(solution)
        return solutions

    # ------------------------------------------------------------------
    # Critic phase
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_solutions(
        solutions: Sequence[EscherSolver],
        evaluator: Callable[[EscherSolver], float],
    ) -> list[float]:
        """Score every solution using the critic evaluator.

        Args:
            solutions: Candidate solutions.
            evaluator: Fitness function returning a scalar score.

        Returns:
            Parallel list of scores.
        """
        scores = [evaluator(s) for s in solutions]
        logger.debug("Evaluated %d solutions", len(scores))
        return scores

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    @staticmethod
    def select_top(
        solutions: Sequence[EscherSolver],
        top_k: int,
        scores: Sequence[float] | None = None,
    ) -> list[EscherSolver]:
        """Select the top-k solutions by fitness.

        Args:
            solutions: Candidate solutions.
            top_k: Number to keep.
            scores: Fitness scores. If omitted, uses solution.fitness_score.

        Returns:
            The top_k highest-fitness solutions.
        """
        if not solutions:
            return []

        k = min(top_k, len(solutions))
        if scores is not None:
            paired = list(zip(solutions, scores))
            paired.sort(key=lambda x: x[1], reverse=True)
            return [p[0] for p in paired[:k]]

        sorted_sols = sorted(solutions, key=lambda s: s.fitness_score, reverse=True)
        return sorted_sols[:k]

    # ------------------------------------------------------------------
    # Variation operators
    # ------------------------------------------------------------------

    def crossover(
        self,
        parent_a: EscherSolver,
        parent_b: EscherSolver,
    ) -> EscherSolver:
        """Combine two parent solutions to produce an offspring.

        Uses midpoint content merge. Real deployments should override
        with domain-specific recombination.

        Args:
            parent_a: First parent.
            parent_b: Second parent.

        Returns:
            Offspring solver.
        """
        midpoint = (len(parent_a.content) + len(parent_b.content)) // 2
        child_content = parent_a.content[:midpoint] + " | " + parent_b.content[midpoint:]

        return EscherSolver(
            content=child_content,
            parent_ids=(parent_a.solution_id, parent_b.solution_id),
            generation=self._generation + 1,
        )

    def mutate(self, solution: EscherSolver, rate: float | None = None) -> EscherSolver:
        """Apply random variation to a solution.

        Args:
            solution: The solution to mutate.
            rate: Mutation rate override.

        Returns:
            Mutated copy of the solution.
        """
        r = rate if rate is not None else self.mutation_rate
        if self._rng.random() > r:
            return solution

        suffix = f" [mutated-g{self._generation}-{self._rng.randint(0, 999)}]"
        return EscherSolver(
            content=solution.content + suffix,
            parent_ids=solution.parent_ids,
            generation=solution.generation,
        )

    # ------------------------------------------------------------------
    # Diversity
    # ------------------------------------------------------------------

    @staticmethod
    def compute_diversity(solutions: Sequence[EscherSolver]) -> float:
        """Estimate population diversity as normalised unique-content ratio.

        Args:
            solutions: Current population.

        Returns:
            Diversity score in [0, 1] where 1 = all unique.
        """
        if len(solutions) <= 1:
            return 0.0

        unique = len({s.content for s in solutions})
        return (unique - 1) / (len(solutions) - 1)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> EvolutionMetrics | None:
        """Return metrics for the most recent generation, if any."""
        if not self._history:
            return None

        last = self._history[-1]
        avg = last.average_score
        best = last.best_solution.fitness_score if last.best_solution else 0.0
        diversity = self.compute_diversity(last.solutions)

        improvement = 0.0
        if len(self._history) > 1:
            prev_best = self._history[-2].best_solution
            if prev_best:
                improvement = best - prev_best.fitness_score

        return EvolutionMetrics(
            generation=last.generation_number,
            avg_fitness=avg,
            best_fitness=best,
            diversity=diversity,
            improvement_rate=improvement,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reproduce(self, survivors: list[EscherSolver]) -> list[EscherSolver]:
        """Fill the population back to `population_size` via crossover + mutation."""
        next_gen: list[EscherSolver] = list(survivors)

        while len(next_gen) < self.population_size:
            if len(survivors) >= 2 and self._rng.random() < self.crossover_rate:
                a, b = self._rng.sample(survivors, 2)
                child = self.crossover(a, b)
            elif survivors:
                child = self._rng.choice(survivors)
            else:
                child = EscherSolver(content="seed", generation=self._generation + 1)

            child = self.mutate(child)
            next_gen.append(child)

        return next_gen[: self.population_size]

    @staticmethod
    def _default_evaluator(solver: EscherSolver) -> float:
        """Heuristic scorer when no evaluator is supplied."""
        return float(len(solver.content) % 100) / 100.0
