"""Fitness Evaluation System — Multi-objective fitness scoring and Pareto analysis.

Provides multi-objective fitness evaluation (speed, quality, cost, reliability),
Pareto frontier tracking, fitness landscape analysis, adaptive fitness weights,
and benchmark-based evaluation.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .meta_evolution import AgentGenome

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class FitnessError(Exception):
    """Base exception for fitness evaluation errors."""


class IncompleteBenchmarkError(FitnessError):
    """Raised when a benchmark run is incomplete."""


class ParetoError(FitnessError):
    """Raised when Pareto frontier operations fail."""


# ── Enums ───────────────────────────────────────────────────────────────────────


class ObjectiveDimension(Enum):
    """Dimensions for multi-objective fitness evaluation."""

    SPEED = auto()  # Task completion speed
    QUALITY = auto()  # Output quality
    COST = auto()  # Computational/token cost
    RELIABILITY = auto()  # Consistency / error rate
    ADAPTABILITY = auto()  # Performance on novel tasks
    SAFETY = auto()  # Safety constraint adherence
    EFFICIENCY = auto()  # Resource utilization efficiency


# ── Data Classes ────────────────────────────────────────────────────────────────


@dataclass
class ObjectiveVector:
    """Multi-dimensional objective value vector."""

    values: dict[ObjectiveDimension, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for dim in ObjectiveDimension:
            self.values.setdefault(dim, 0.0)

    def dominates(self, other: ObjectiveVector) -> bool:
        """Check if this vector Pareto-dominates another.

        Dominates if it is at least as good in all dimensions and strictly
        better in at least one.
        """
        at_least_as_good = all(self.values[dim] >= other.values[dim] for dim in ObjectiveDimension)
        strictly_better = any(self.values[dim] > other.values[dim] for dim in ObjectiveDimension)
        return at_least_as_good and strictly_better

    def to_list(self) -> list[float]:
        return [self.values[dim] for dim in ObjectiveDimension]

    @classmethod
    def from_list(cls, values: list[float]) -> ObjectiveVector:
        dims = list(ObjectiveDimension)
        return cls(
            values={dim: values[i] if i < len(values) else 0.0 for i, dim in enumerate(dims)}
        )


@dataclass
class FitnessWeights:
    """Adaptive weights for combining multi-objective scores.

    Higher weight = more important in combined fitness.
    """

    weights: dict[ObjectiveDimension, float] = field(
        default_factory=lambda: {
            ObjectiveDimension.SPEED: 0.15,
            ObjectiveDimension.QUALITY: 0.30,
            ObjectiveDimension.COST: 0.15,
            ObjectiveDimension.RELIABILITY: 0.20,
            ObjectiveDimension.ADAPTABILITY: 0.10,
            ObjectiveDimension.SAFETY: 0.05,
            ObjectiveDimension.EFFICIENCY: 0.05,
        }
    )

    def __post_init__(self) -> None:
        self.normalize()

    def normalize(self) -> None:
        total = sum(self.weights.values())
        if total > 0:
            for dim in self.weights:
                self.weights[dim] /= total

    def combine(self, vector: ObjectiveVector) -> float:
        """Combine an objective vector into a scalar fitness score."""
        return sum(self.weights[dim] * vector.values[dim] for dim in ObjectiveDimension)

    def adapt(self, performance_history: list[dict[str, float]]) -> FitnessWeights:
        """Adapt weights based on historical performance.

        Dimensions with high variance get reduced weight (less reliable).
        Dimensions with consistent improvement get increased weight.
        """
        if len(performance_history) < 3:
            return self

        new_weights: dict[ObjectiveDimension, float] = {}
        for dim in ObjectiveDimension:
            values = [
                h.get(dim.name.lower(), 0.0) for h in performance_history if dim.name.lower() in h
            ]
            if len(values) < 2:
                new_weights[dim] = self.weights[dim]
                continue

            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            trend = values[-1] - values[0]

            # Inverse variance weighting + trend bonus
            stability = 1.0 / (1.0 + math.sqrt(max(variance, 1e-8)))
            trend_bonus = max(0, trend) * 0.5
            new_weights[dim] = self.weights[dim] * stability + trend_bonus

        result = FitnessWeights(weights=new_weights)
        result.normalize()
        return result


@dataclass
class FitnessLandscape:
    """Analysis of the fitness landscape for a population."""

    avg_fitness: float
    max_fitness: float
    min_fitness: float
    std_fitness: float
    ruggedness: float  # Higher = more rugged landscape
    gradient_norm: float  # Average fitness gradient
    local_optima_count: int  # Estimated number of local optima
    plateau_ratio: float  # Fraction of population on fitness plateaus


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark-based fitness evaluation."""

    name: str
    description: str
    task_count: int = 10
    timeout_per_task_ms: float = 30_000
    min_success_rate: float = 0.5
    dimensions: list[ObjectiveDimension] = field(default_factory=lambda: list(ObjectiveDimension))


@dataclass
class BenchmarkResult:
    """Result of a benchmark evaluation run."""

    config: BenchmarkConfig
    agent_id: str
    scores: dict[ObjectiveDimension, float]
    task_results: list[dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0
    total_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.success_rate >= self.config.min_success_rate

    @property
    def objective_vector(self) -> ObjectiveVector:
        return ObjectiveVector(values=dict(self.scores))


# ── Pareto Frontier ─────────────────────────────────────────────────────────────


class ParetoFrontier:
    """Tracks and manages the Pareto frontier of multi-objective solutions.

    The Pareto frontier contains non-dominated solutions — those where
    no other solution is better in all objectives simultaneously.
    """

    def __init__(self, max_size: int = 100):
        self._max_size = max_size
        self._frontier: list[tuple[str, ObjectiveVector]] = []
        self._history: list[dict[str, Any]] = []

    def add(self, genome_id: str, vector: ObjectiveVector) -> bool:
        """Attempt to add a solution to the Pareto frontier.

        Returns True if the solution was added (it is non-dominated).
        """
        # Check if this solution is dominated by any existing frontier member
        for _, frontier_vec in self._frontier:
            if frontier_vec.dominates(vector):
                return False  # Dominated, not added

        # Remove existing solutions that this one dominates
        self._frontier = [(fid, fvec) for fid, fvec in self._frontier if not vector.dominates(fvec)]

        self._frontier.append((genome_id, vector))

        # Trim to max size
        if len(self._frontier) > self._max_size:
            self._frontier = self._frontier[-self._max_size :]

        self._history.append(
            {
                "genome_id": genome_id,
                "frontier_size": len(self._frontier),
                "timestamp": time.time(),
            }
        )

        logger.debug(
            "Added %s to Pareto frontier (size=%d)",
            genome_id,
            len(self._frontier),
        )
        return True

    def get_frontier(self) -> list[tuple[str, ObjectiveVector]]:
        """Get the current Pareto frontier."""
        return list(self._frontier)

    def get_frontier_ids(self) -> list[str]:
        """Get genome IDs on the frontier."""
        return [fid for fid, _ in self._frontier]

    def hypervolume(self, reference_point: ObjectiveVector | None = None) -> float:
        """Approximate the hypervolume dominated by the frontier.

        Higher hypervolume = better coverage of the objective space.
        """
        if not self._frontier:
            return 0.0

        if reference_point is None:
            reference_point = ObjectiveVector(values=dict.fromkeys(ObjectiveDimension, 0.0))

        # Simple approximation: average distance from reference
        total_volume = 0.0
        for _, vec in self._frontier:
            distance = math.sqrt(
                sum(
                    (vec.values[dim] - reference_point.values[dim]) ** 2
                    for dim in ObjectiveDimension
                )
            )
            total_volume += distance

        return total_volume / max(len(self._frontier), 1)

    def coverage(self, target_frontier: ParetoFrontier) -> float:
        """Compute C-metric: fraction of target solutions dominated by this frontier."""
        if not target_frontier._frontier:
            return 1.0

        dominated = 0
        for _, target_vec in target_frontier._frontier:
            for _, our_vec in self._frontier:
                if our_vec.dominates(target_vec):
                    dominated += 1
                    break

        return dominated / len(target_frontier._frontier)

    @property
    def size(self) -> int:
        return len(self._frontier)


# ── Fitness Evaluator ───────────────────────────────────────────────────────────


class FitnessEvaluator:
    """Multi-objective fitness evaluation and landscape analysis.

    Evaluates agent genomes across multiple objective dimensions, tracks
    Pareto frontiers, adapts fitness weights, and analyzes fitness landscapes.

    Usage::

        evaluator = FitnessEvaluator(weights=FitnessWeights())
        score = await evaluator.evaluate(genome, benchmark_config)
        frontier = evaluator.pareto_frontier
    """

    def __init__(
        self,
        weights: FitnessWeights | None = None,
        track_pareto: bool = True,
        dynamic_weights: bool = True,
    ):
        self._weights = weights or FitnessWeights()
        self._track_pareto = track_pareto
        self._dynamic_weights = dynamic_weights
        self._pareto = ParetoFrontier()

        self._evaluation_history: list[dict[str, Any]] = []
        self._evaluation_count: int = 0

    async def evaluate(
        self,
        genome: AgentGenome,
        config: BenchmarkConfig,
    ) -> float:
        """Evaluate genome fitness against a benchmark configuration.

        Returns a scalar combined fitness score (0.0 to 1.0).
        """
        start = time.perf_counter()

        # Run benchmark
        result = await self._run_benchmark(genome, config)

        # Compute objective vector
        vector = self._compute_objectives(genome, result)

        # Track Pareto frontier
        if self._track_pareto:
            self._pareto.add(genome.agent_id, vector)

        # Combine into scalar fitness
        combined = self._weights.combine(vector)

        # Record
        self._evaluation_history.append(
            {
                "agent_id": genome.agent_id,
                "generation": genome.generation,
                "fitness": combined,
                "objectives": {dim.name: vector.values[dim] for dim in ObjectiveDimension},
                "duration_ms": (time.perf_counter() - start) * 1000,
            }
        )

        self._evaluation_count += 1

        # Adapt weights if enabled
        if self._dynamic_weights and self._evaluation_count % 10 == 0:
            self._weights = self._weights.adapt(self._evaluation_history[-50:])

        return combined

    async def evaluate_population(
        self,
        genomes: list[AgentGenome],
        config: BenchmarkConfig,
    ) -> dict[str, float]:
        """Evaluate a population of genomes."""
        tasks = [self.evaluate(genome, config) for genome in genomes]
        scores = await asyncio.gather(*tasks, return_exceptions=True)

        result: dict[str, float] = {}
        for genome, score in zip(genomes, scores, strict=False):
            if isinstance(score, Exception):
                logger.warning("Evaluation failed for %s: %s", genome.agent_id, score)
                result[genome.agent_id] = 0.0
            else:
                result[genome.agent_id] = score

        return result

    def analyze_landscape(
        self,
        genomes: list[AgentGenome],
        fitness_scores: dict[str, float],
    ) -> FitnessLandscape:
        """Analyze the fitness landscape of a population."""
        if not fitness_scores:
            return FitnessLandscape(
                avg_fitness=0.0,
                max_fitness=0.0,
                min_fitness=0.0,
                std_fitness=0.0,
                ruggedness=0.0,
                gradient_norm=0.0,
                local_optima_count=0,
                plateau_ratio=0.0,
            )

        scores = list(fitness_scores.values())
        n = len(scores)

        avg = sum(scores) / n
        max_s = max(scores)
        min_s = min(scores)

        variance = sum((s - avg) ** 2 for s in scores) / n
        std = math.sqrt(variance)

        # Ruggedness: measure of fitness variance between neighbors
        ruggedness = 0.0
        if n > 1:
            sorted_scores = sorted(scores)
            diffs = [abs(sorted_scores[i + 1] - sorted_scores[i]) for i in range(n - 1)]
            ruggedness = sum(diffs) / (n - 1) if diffs else 0.0

        # Gradient norm: average pairwise fitness difference
        gradient_norm = 0.0
        if n > 1:
            comparisons = 0
            total_diff = 0.0
            for i in range(min(n, 50)):  # Sample for large populations
                for j in range(i + 1, min(n, 50)):
                    total_diff += abs(scores[i] - scores[j])
                    comparisons += 1
            gradient_norm = total_diff / max(comparisons, 1)

        # Local optima estimate: peaks in fitness distribution
        local_optima_count = 0
        if n >= 3:
            sorted_s = sorted(scores)
            window = max(3, n // 10)
            for i in range(window, n - window):
                left_max = max(sorted_s[i - window : i])
                right_max = max(sorted_s[i + 1 : i + window + 1])
                if sorted_s[i] > left_max and sorted_s[i] > right_max:
                    local_optima_count += 1

        # Plateau ratio: fraction of population with very similar fitness
        plateau_threshold = 0.01
        plateaus = 0
        for i, s1 in enumerate(scores):
            similar = sum(
                1 for j, s2 in enumerate(scores) if i != j and abs(s1 - s2) < plateau_threshold
            )
            if similar >= n * 0.1:  # 10% of population is similar
                plateaus += 1
        plateau_ratio = plateaus / n if n > 0 else 0.0

        return FitnessLandscape(
            avg_fitness=avg,
            max_fitness=max_s,
            min_fitness=min_s,
            std_fitness=std,
            ruggedness=ruggedness,
            gradient_norm=gradient_norm,
            local_optima_count=local_optima_count,
            plateau_ratio=plateau_ratio,
        )

    def get_pareto_dominated(self, genomes: list[AgentGenome]) -> list[str]:
        """Get genome IDs that are NOT on the Pareto frontier (dominated)."""
        frontier_ids = set(self._pareto.get_frontier_ids())
        dominated = [g.agent_id for g in genomes if g.agent_id not in frontier_ids]
        return dominated

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _run_benchmark(
        self,
        genome: AgentGenome,
        config: BenchmarkConfig,
    ) -> BenchmarkResult:
        """Run a benchmark evaluation. Override for real implementations."""
        task_results: list[dict[str, Any]] = []
        errors: list[str] = []
        successes = 0

        for task_idx in range(config.task_count):
            try:
                # Simulate task execution
                task_score = 0.5 + 0.5 * (time.time() % 1.0)
                successes += 1
                task_results.append(
                    {
                        "task_id": task_idx,
                        "score": task_score,
                        "time_ms": 100 + (time.time() * 1000) % 500,
                    }
                )
            except Exception as exc:
                errors.append(f"Task {task_idx}: {exc}")
                task_results.append({"task_id": task_idx, "error": str(exc)})

        success_rate = successes / config.task_count if config.task_count > 0 else 0.0

        # Compute dimension scores using genome configuration
        scores = self._extract_dimension_scores(genome, success_rate)

        return BenchmarkResult(
            config=config,
            agent_id=genome.agent_id,
            scores=scores,
            task_results=task_results,
            success_rate=success_rate,
            total_time_ms=sum(tr.get("time_ms", 0) for tr in task_results),
            errors=errors,
        )

    @staticmethod
    def _extract_dimension_scores(
        genome: AgentGenome,
        base_success_rate: float,
    ) -> dict[ObjectiveDimension, float]:
        """Extract objective dimension scores from genome configuration."""
        scores: dict[ObjectiveDimension, float] = {}

        # Speed: inverse of exploration rate (higher exploration = slower)
        exploration = genome.hyperparameters.get("exploration_rate", 0.1)
        scores[ObjectiveDimension.SPEED] = 1.0 - exploration * 0.5

        # Quality: based on temperature (lower = more deterministic = higher quality)
        temperature = genome.hyperparameters.get("temperature", 1.0)
        scores[ObjectiveDimension.QUALITY] = max(0.0, 1.0 - temperature * 0.3)

        # Cost: inverse of batch size factor
        batch_factor = genome.hyperparameters.get("batch_size_factor", 1.0)
        scores[ObjectiveDimension.COST] = max(0.0, 1.0 - batch_factor * 0.2)

        # Reliability: base success rate
        scores[ObjectiveDimension.RELIABILITY] = base_success_rate

        # Adaptability: strategy diversity
        num_strategies = len(genome.active_strategies)
        scores[ObjectiveDimension.ADAPTABILITY] = min(num_strategies / 5.0, 1.0)

        # Safety: constraint satisfaction
        safety_threshold = genome.constraints.get("min_quality_threshold", 0.5)
        scores[ObjectiveDimension.SAFETY] = safety_threshold

        # Efficiency: discount factor
        discount = genome.hyperparameters.get("discount_factor", 0.9)
        scores[ObjectiveDimension.EFFICIENCY] = discount

        return scores

    @staticmethod
    def _compute_objectives(
        genome: AgentGenome,
        result: BenchmarkResult,
    ) -> ObjectiveVector:
        """Compute the objective vector from a benchmark result."""
        # Use benchmark scores, falling back to genome-extracted scores
        if result.scores:
            return ObjectiveVector(values=dict(result.scores))
        return ObjectiveVector(
            values=FitnessEvaluator._extract_dimension_scores(
                genome,
                result.success_rate,
            )
        )

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def pareto_frontier(self) -> ParetoFrontier:
        return self._pareto

    @property
    def evaluation_count(self) -> int:
        return self._evaluation_count

    @property
    def weights(self) -> FitnessWeights:
        return self._weights

    @weights.setter
    def weights(self, w: FitnessWeights) -> None:
        self._weights = w
        self._weights.normalize()
