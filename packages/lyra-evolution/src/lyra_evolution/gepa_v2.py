"""GEPA v2 — Multi-Agent Prompt Evolution.

Parallel prompt learning across the fleet (Combee-inspired, 17x speedup).
Uses tournament selection, single-point crossover, random mutation, and
Pareto frontier selection to evolve optimal prompt strategies.

Phase 13.4 — GEPA v2: Genetic Evolutionary Prompt Adaptation (Generation 2).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    """Generate a unique candidate identifier."""
    return uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """A single prompt candidate in the evolution population.

    Attributes:
        candidate_id: Unique identifier for this candidate.
        prompt_text: The full prompt text being evaluated.
        score: Fitness score assigned after evaluation (0.0 – 1.0).
        tokens_used: Token count consumed during evaluation.
        generation: Which generation produced this candidate.
        parent_ids: Identifiers of parent candidates (lineage tracking).
        model_family: The model family this candidate was tested on.
    """

    candidate_id: str = field(default_factory=_new_id)
    prompt_text: str = ""
    score: float = 0.0
    tokens_used: int = 0
    generation: int = 0
    parent_ids: tuple[str, ...] = ()
    model_family: str = "default"

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")
        if self.tokens_used < 0:
            raise ValueError(
                f"tokens_used must be non-negative, got {self.tokens_used}"
            )


@dataclass(frozen=True)
class ParetoFrontier:
    """Non-dominated candidates in the score-vs-tokens objective space.

    Attributes:
        candidates: The Pareto-optimal candidates.
        frontier_type: Label describing the objective space (e.g.
            ``"score_vs_tokens"``).
        dominated_count: Number of candidates that were dominated.
    """

    candidates: tuple[Candidate, ...] = ()
    frontier_type: str = "score_vs_tokens"
    dominated_count: int = 0

    @property
    def best_by_score(self) -> Candidate | None:
        """Return the candidate with the highest score on the frontier."""
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.score)

    @property
    def best_by_efficiency(self) -> Candidate | None:
        """Return the candidate with the best score-to-token ratio."""
        if not self.candidates:
            return None
        return max(
            self.candidates,
            key=lambda c: c.score / max(c.tokens_used, 1),
        )

    @property
    def frontier_size(self) -> int:
        """Number of candidates on the Pareto frontier."""
        return len(self.candidates)


@dataclass(frozen=True)
class EvolutionConfig:
    """Configuration knobs for the evolution algorithm.

    Attributes:
        population_size: Number of candidates per generation.
        generations: Total number of evolution generations.
        mutation_rate: Probability of mutation per candidate.
        crossover_rate: Probability of crossover per pair.
        tournament_size: Number of candidates in each tournament.
        elite_count: Number of top candidates preserved unchanged.
        parallel_workers: Simulated worker count for logging/reporting.
        target_score: Stopping criterion — stop if best score >= this.
        max_tokens_per_candidate: Maximum allowed tokens per candidate.
    """

    population_size: int = 20
    generations: int = 5
    mutation_rate: float = 0.3
    crossover_rate: float = 0.5
    tournament_size: int = 4
    elite_count: int = 3
    parallel_workers: int = 8
    target_score: float = 0.9
    max_tokens_per_candidate: int = 2000

    def __post_init__(self) -> None:
        if self.population_size < 4:
            raise ValueError(
                f"population_size must be >= 4, got {self.population_size}"
            )
        if self.generations < 1:
            raise ValueError(
                f"generations must be >= 1, got {self.generations}"
            )
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError(
                f"mutation_rate must be in [0, 1], got {self.mutation_rate}"
            )
        if not 0.0 <= self.crossover_rate <= 1.0:
            raise ValueError(
                f"crossover_rate must be in [0, 1], got {self.crossover_rate}"
            )
        if self.tournament_size < 2:
            raise ValueError(
                f"tournament_size must be >= 2, got {self.tournament_size}"
            )
        if self.elite_count < 1:
            raise ValueError(
                f"elite_count must be >= 1, got {self.elite_count}"
            )
        if not 0.0 < self.target_score <= 1.0:
            raise ValueError(
                f"target_score must be in (0, 1], got {self.target_score}"
            )


# ---------------------------------------------------------------------------
# GEPA v2 Evolution Engine
# ---------------------------------------------------------------------------


class GEPAv2:
    """Genetic Evolutionary Prompt Adaptation v2.

    Evolves prompt strategies using a genetic algorithm with tournament
    selection, single-point crossover, mutation, and Pareto frontier
    analysis. Designed for parallel fleet-wide prompt learning inspired
    by the Combee architecture.

    Usage::

        gepa = GEPAv2()
        config = EvolutionConfig(population_size=20, generations=5)
        best, frontier, final_pop = gepa.evolve(
            base_prompt="Answer concisely with citations.",
            test_cases=[{"input": "What is RL?", "expected": "..."}],
            config=config,
        )
    """

    def __init__(self) -> None:
        self._generation: int = 0
        self._best_score: float = 0.0
        self._total_evaluated: int = 0
        self._base_prompt: str = ""
        self._population_history: list[list[Candidate]] = []

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize_population(
        self,
        base_prompt: str,
        config: EvolutionConfig,
    ) -> list[Candidate]:
        """Create the initial population via mutations of the base prompt.

        Args:
            base_prompt: The starting prompt to seed the population.
            config: Evolution configuration.

        Returns:
            The initial population of ``Candidate`` objects.
        """
        self._base_prompt = base_prompt
        self._generation = 0
        self._population_history = []
        self._total_evaluated = 0

        population: list[Candidate] = []

        # Keep the original unchanged as generation 0
        base = Candidate(
            candidate_id=_new_id(),
            prompt_text=base_prompt,
            score=0.0,
            tokens_used=len(base_prompt.split()),
            generation=0,
            parent_ids=(),
            model_family="default",
        )
        population.append(base)

        # Create variants via mutation
        while len(population) < config.population_size:
            variant = self._mutate_prompt(base_prompt)
            candidate = Candidate(
                candidate_id=_new_id(),
                prompt_text=variant,
                score=0.0,
                tokens_used=len(variant.split()),
                generation=0,
                parent_ids=(base.candidate_id,),
                model_family="default",
            )
            population.append(candidate)

        self._population_history.append(population)

        logger.info(
            "Initialized population of %d candidates from base prompt",
            len(population),
        )

        return population

    # ------------------------------------------------------------------
    # Evaluation (stub)
    # ------------------------------------------------------------------

    def evaluate(
        self,
        candidate: Candidate,
        test_cases: list[dict[str, Any]],
    ) -> Candidate:
        """Evaluate a candidate against a set of test cases.

        This is a **stub** implementation that computes a heuristic score
        based on prompt length, keyword coverage, and structural features.
        Replace with a real LLM-based evaluator for production use.

        Args:
            candidate: The candidate to evaluate.
            test_cases: List of test case dicts, each with at least
                ``"input"`` and ``"expected"`` keys.

        Returns:
            A new ``Candidate`` with an updated ``score`` and
            ``tokens_used``.
        """
        if not test_cases:
            return Candidate(
                candidate_id=candidate.candidate_id,
                prompt_text=candidate.prompt_text,
                score=0.5,
                tokens_used=len(candidate.prompt_text.split()),
                generation=candidate.generation,
                parent_ids=candidate.parent_ids,
                model_family=candidate.model_family,
            )

        prompt_text = candidate.prompt_text

        # Score components (heuristic stub):
        # 1. Length score: penalise very short or very long prompts
        word_count = len(prompt_text.split())
        # Ideal range: 20–150 words (tunable)
        if word_count < 10:
            length_score = max(0.0, word_count / 10.0)
        elif word_count > 500:
            length_score = max(0.0, 1.0 - (word_count - 500) / 500.0)
        else:
            length_score = 1.0

        # 2. Keyword coverage: presence of expected keywords from test cases
        expected_keywords: set[str] = set()
        for tc in test_cases:
            expected = tc.get("expected", "")
            if isinstance(expected, str):
                for kw in expected.lower().split():
                    if len(kw) > 3:
                        expected_keywords.add(kw)
        if expected_keywords:
            prompt_lower = prompt_text.lower()
            covered = sum(1 for kw in expected_keywords if kw in prompt_lower)
            keyword_score = covered / len(expected_keywords)
        else:
            keyword_score = 0.5

        # 3. Structure score: check for structural elements
        structure_score = 0.0
        if ":" in prompt_text:
            structure_score += 0.2
        if prompt_text.strip().endswith((".", "?", "!")):
            structure_score += 0.2
        if any(marker in prompt_text for marker in ("1.", "- ", "*")):
            structure_score += 0.2
        if "step" in prompt_text.lower() or "first" in prompt_text.lower():
            structure_score += 0.2
        if "example" in prompt_text.lower() or "e.g." in prompt_text.lower():
            structure_score += 0.2

        # Composite: weighted average
        final_score = (
            0.3 * length_score + 0.4 * keyword_score + 0.3 * structure_score
        )
        # Clamp to [0, 1]
        final_score = max(0.0, min(1.0, final_score))

        self._total_evaluated += 1

        return Candidate(
            candidate_id=candidate.candidate_id,
            prompt_text=candidate.prompt_text,
            score=round(final_score, 4),
            tokens_used=word_count,
            generation=candidate.generation,
            parent_ids=candidate.parent_ids,
            model_family=candidate.model_family,
        )

    # ------------------------------------------------------------------
    # Selection (tournament)
    # ------------------------------------------------------------------

    def select(
        self,
        population: list[Candidate],
        config: EvolutionConfig,
    ) -> list[Candidate]:
        """Perform tournament selection.

        Repeatedly picks ``tournament_size`` random candidates from the
        population and keeps the best one until the selected pool reaches
        the population size.

        Args:
            population: Current candidate population.
            config: Evolution configuration.

        Returns:
            Selected candidates (parents for the next generation).
        """
        selected: list[Candidate] = []
        pool = list(population)

        while len(selected) < config.population_size:
            tournament = random.sample(
                pool, min(config.tournament_size, len(pool))
            )
            winner = max(tournament, key=lambda c: c.score)
            selected.append(winner)

        return selected

    # ------------------------------------------------------------------
    # Crossover
    # ------------------------------------------------------------------

    def crossover(
        self,
        parents: list[Candidate],
        config: EvolutionConfig,
    ) -> list[Candidate]:
        """Apply single-point crossover between pairs of parents.

        Pairs are formed sequentially. With probability ``crossover_rate``,
        two children are produced by swapping text segments at a random
        split point.

        Args:
            parents: Selected parent candidates.
            config: Evolution configuration.

        Returns:
            Offspring candidates, possibly the result of crossover.
        """
        offspring: list[Candidate] = []

        for i in range(0, len(parents) - 1, 2):
            p1 = parents[i]
            p2 = parents[i + 1]

            if random.random() < config.crossover_rate:
                # Single-point crossover at word boundary
                words1 = p1.prompt_text.split()
                words2 = p2.prompt_text.split()

                if len(words1) > 1 and len(words2) > 1:
                    point = random.randint(1, min(len(words1), len(words2)) - 1)

                    child1_text = " ".join(words1[:point] + words2[point:])
                    child2_text = " ".join(words2[:point] + words1[point:])

                    child1 = Candidate(
                        candidate_id=_new_id(),
                        prompt_text=child1_text,
                        score=0.0,
                        tokens_used=len(child1_text.split()),
                        generation=self._generation,
                        parent_ids=(p1.candidate_id, p2.candidate_id),
                        model_family="default",
                    )
                    child2 = Candidate(
                        candidate_id=_new_id(),
                        prompt_text=child2_text,
                        score=0.0,
                        tokens_used=len(child2_text.split()),
                        generation=self._generation,
                        parent_ids=(p2.candidate_id, p1.candidate_id),
                        model_family="default",
                    )
                    offspring.extend([child1, child2])
                else:
                    offspring.extend([p1, p2])
            else:
                offspring.extend([p1, p2])

        # If odd number of parents, carry the last one forward
        if len(parents) % 2 == 1:
            offspring.append(parents[-1])

        return offspring

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def mutate(
        self,
        candidates: list[Candidate],
        config: EvolutionConfig,
    ) -> list[Candidate]:
        """Apply random mutations to candidates.

        Mutation operators applied with probability ``mutation_rate``:
        word swap, phrase insertion, or simple reordering.

        Args:
            candidates: Candidates to potentially mutate.
            config: Evolution configuration.

        Returns:
            Mutated (or unchanged) candidates.
        """
        mutated: list[Candidate] = []

        for c in candidates:
            if random.random() < config.mutation_rate:
                new_text = self._mutate_prompt(c.prompt_text)
                mutated.append(
                    Candidate(
                        candidate_id=_new_id(),
                        prompt_text=new_text,
                        score=0.0,
                        tokens_used=len(new_text.split()),
                        generation=self._generation,
                        parent_ids=(c.candidate_id,),
                        model_family=c.model_family,
                    )
                )
            else:
                mutated.append(c)

        return mutated

    # ------------------------------------------------------------------
    # Full evolution cycle
    # ------------------------------------------------------------------

    def evolve(
        self,
        base_prompt: str,
        test_cases: list[dict[str, Any]],
        config: EvolutionConfig | None = None,
    ) -> tuple[Candidate, ParetoFrontier, list[Candidate]]:
        """Run the full evolution cycle.

        Steps:
            1. Initialise population from base prompt.
            2. Evaluate all candidates against test cases.
            3. For each generation:
                a. Select parents via tournament.
                b. Apply crossover.
                c. Apply mutation.
                d. Evaluate new candidates.
                e. Apply elitism (preserve top ``elite_count``).
            4. Compute Pareto frontier from the final population.

        Args:
            base_prompt: The starting prompt to evolve.
            test_cases: Test cases for candidate evaluation.
            config: Evolution configuration (defaults if omitted).

        Returns:
            Tuple of ``(best_candidate, pareto_frontier, final_population)``.
        """
        cfg = config or EvolutionConfig()
        self._generation = 0

        # Step 1: Initialise
        population = self.initialize_population(base_prompt, cfg)

        # Step 2: Evaluate initial population
        evaluated: list[Candidate] = [
            self.evaluate(c, test_cases) for c in population
        ]
        self._best_score = max(c.score for c in evaluated)

        self._population_history = [evaluated]

        logger.info(
            "Starting evolution: pop=%d, gen=%d, target=%.2f",
            cfg.population_size,
            cfg.generations,
            cfg.target_score,
        )

        # Step 3: Evolve over generations
        for gen in range(1, cfg.generations + 1):
            self._generation = gen

            # Sort by score descending for elitism
            evaluated_sorted = sorted(
                evaluated, key=lambda c: c.score, reverse=True
            )

            # Elite preservation
            elites = evaluated_sorted[: cfg.elite_count]

            # Select parents (excluding elites to maintain diversity)
            non_elite = evaluated_sorted[cfg.elite_count :]
            if not non_elite:
                non_elite = evaluated_sorted
            parents = self.select(non_elite, cfg)

            # Crossover
            children = self.crossover(parents, cfg)

            # Mutate
            mutated = self.mutate(children, cfg)

            # Evaluate new candidates
            new_evaluated = [
                self.evaluate(c, test_cases) for c in mutated
            ]

            # Combine elites + new generation, trim to population size
            combined = elites + new_evaluated
            combined_sorted = sorted(
                combined, key=lambda c: c.score, reverse=True
            )
            evaluated = combined_sorted[: cfg.population_size]

            self._population_history.append(evaluated)

            gen_best = max(c.score for c in evaluated)
            gen_avg = sum(c.score for c in evaluated) / len(evaluated)
            self._best_score = max(self._best_score, gen_best)

            logger.info(
                "Generation %d: best=%.4f, avg=%.4f, pop=%d",
                gen,
                gen_best,
                gen_avg,
                len(evaluated),
            )

            # Early stopping if target reached
            if gen_best >= cfg.target_score:
                logger.info(
                    "Target score %.2f reached at generation %d, stopping early",
                    cfg.target_score,
                    gen,
                )
                break

        # Pareto frontier
        frontier = self.compute_pareto_frontier(evaluated)

        # Best candidate
        best = max(evaluated, key=lambda c: c.score)

        logger.info(
            "Evolution complete: best=%.4f, frontier=%d candidates",
            best.score,
            frontier.frontier_size,
        )

        return best, frontier, evaluated

    # ------------------------------------------------------------------
    # Pareto frontier
    # ------------------------------------------------------------------

    def compute_pareto_frontier(
        self,
        population: list[Candidate],
    ) -> ParetoFrontier:
        """Compute the Pareto frontier balancing score vs tokens.

        A candidate *dominates* another if it has a **higher** score and
        **fewer** tokens. Non-dominated candidates form the frontier.

        Args:
            population: The candidate population to analyse.

        Returns:
            A ``ParetoFrontier`` with non-dominated candidates.
        """
        frontier: list[Candidate] = []
        dominated = 0

        for i, c1 in enumerate(population):
            is_dominated = False
            for j, c2 in enumerate(population):
                if i == j:
                    continue
                # c2 dominates c1 if c2 has higher score AND fewer tokens
                if c2.score > c1.score and c2.tokens_used <= c1.tokens_used:
                    is_dominated = True
                    break
            if is_dominated:
                dominated += 1
            else:
                frontier.append(c1)

        frontier_sorted = sorted(
            frontier, key=lambda c: c.score, reverse=True
        )

        return ParetoFrontier(
            candidates=tuple(frontier_sorted),
            frontier_type="score_vs_tokens",
            dominated_count=dominated,
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate evolution statistics.

        Returns:
            Dict with keys: ``generations_run``, ``best_score``,
            ``avg_score``, ``total_candidates_evaluated``,
            ``improvement_from_base``.
        """
        all_candidates = [
            c
            for gen in self._population_history
            for c in gen
        ]

        avg_score = (
            sum(c.score for c in all_candidates) / len(all_candidates)
            if all_candidates
            else 0.0
        )

        initial_best = (
            max(
                (c.score for c in self._population_history[0]),
                default=0.0,
            )
            if self._population_history
            else 0.0
        )
        improvement = self._best_score - initial_best

        return {
            "generations_run": self._generation,
            "best_score": round(self._best_score, 4),
            "avg_score": round(avg_score, 4),
            "total_candidates_evaluated": self._total_evaluated,
            "improvement_from_base": round(improvement, 4),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _mutate_prompt(text: str) -> str:
        """Apply a random mutation to a prompt string.

        Operators (chosen uniformly at random):
            - Word swap: swap two random words.
            - Phrase insertion: insert a transitional phrase.
            - Reordering: shuffle the order of clauses.
        """
        operator = random.choice(["swap", "insert", "reorder"])
        words = text.split()

        if operator == "swap" and len(words) >= 4:
            # Swap two random non-adjacent words
            idx1, idx2 = random.sample(range(len(words)), 2)
            words[idx1], words[idx2] = words[idx2], words[idx1]
            return " ".join(words)

        if operator == "insert":
            templates = [
                "Consider the following: ",
                "Note that ",
                "Importantly, ",
                "In particular, ",
                "As a general guideline, ",
            ]
            insertion = random.choice(templates)
            if words:
                pos = random.randint(0, len(words))
                words.insert(pos, insertion.strip())
            return " ".join(words)

        if operator == "reorder" and len(words) >= 6:
            # Split into clauses (by comma or period) and reorder
            import re as _re

            clauses = _re.split(r"(?<=[,.!?;])\s+", text)
            if len(clauses) >= 3:
                random.shuffle(clauses)
                return " ".join(clauses)

        # Fallback: word swap at any two positions
        if len(words) >= 2:
            idx1, idx2 = random.sample(range(len(words)), 2)
            words[idx1], words[idx2] = words[idx2], words[idx1]
            return " ".join(words)

        return text


__all__ = [
    "Candidate",
    "EvolutionConfig",
    "GEPAv2",
    "ParetoFrontier",
]
