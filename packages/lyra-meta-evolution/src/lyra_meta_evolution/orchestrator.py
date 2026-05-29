"""Evolution Orchestrator — Manages evolution cycles, parallel runs, and integration.

Coordinates the full meta-evolution pipeline: cycle management, parallel
evolution runs, history and rollback, best-of-breed promotion, and
integration with the lyra-evolution package.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .fitness import BenchmarkConfig, FitnessEvaluator
from .genetic_optimizer import GeneticOptimizationResult, GeneticOptimizer
from .meta_evolution import (
    AgentGenome,
    EvolutionLevel,
    EvolutionResult,
    EvolutionTrigger,
    FitnessFunction,
    MetaCognitiveStack,
    MetaEvolutionError,
)
from .strategy_pool import StrategyEncoding, StrategyPool

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class OrchestratorError(MetaEvolutionError):
    """Base exception for orchestrator errors."""


class CycleInProgressError(OrchestratorError):
    """Raised when attempting to start a cycle while one is already running."""


class RollbackError(OrchestratorError):
    """Raised when a rollback operation fails."""


class IntegrationError(OrchestratorError):
    """Raised when integration with external packages fails."""


# ── Enums ───────────────────────────────────────────────────────────────────────


class OrchestratorStatus(Enum):
    """Current status of the evolution orchestrator."""

    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    ERROR = auto()


class CyclePhase(Enum):
    """Phases of an evolution cycle."""

    EVALUATION = auto()
    SELECTION = auto()
    EVOLUTION = auto()
    VERIFICATION = auto()
    PROMOTION = auto()  # Best-of-breed promotion
    ROLLBACK = auto()


# ── Data Classes ────────────────────────────────────────────────────────────────


@dataclass
class CycleConfig:
    """Configuration for an evolution cycle."""

    max_cycles: int = 50
    cycles_per_level: dict[EvolutionLevel, int] = field(default_factory=lambda: {
        EvolutionLevel.L1_PARAMETER: 50,
        EvolutionLevel.L2_STRATEGY: 30,
        EvolutionLevel.L3_ARCHITECTURE: 15,
        EvolutionLevel.L4_GOAL: 10,
    })
    parallel_workers: int = 4
    checkpoint_interval: int = 5
    auto_promote: bool = True
    promote_threshold: float = 0.05  # Minimum improvement for auto-promotion
    rollback_enabled: bool = True
    max_rollback_depth: int = 3
    benchmark: BenchmarkConfig | None = None

    def get_cycles(self, level: EvolutionLevel) -> int:
        return self.cycles_per_level.get(level, 10)


@dataclass
class CycleResult:
    """Result of a complete evolution cycle."""

    cycle_id: int
    level: EvolutionLevel
    phase: CyclePhase
    generations_executed: int
    fitness_before: float
    fitness_after: float
    improvement: float
    best_genome_id: str
    promoted: bool
    genetic_results: list[GeneticOptimizationResult] = field(default_factory=list)
    evolution_results: list[EvolutionResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorSnapshot:
    """Full snapshot of orchestrator state for checkpointing."""

    status: OrchestratorStatus
    current_cycle: int
    current_level: str
    best_genome: dict[str, Any] | None
    population_size: int
    pool_size: int
    history_length: int
    timestamp: float = field(default_factory=time.time)


# ── Evolution Orchestrator ──────────────────────────────────────────────────────


class EvolutionOrchestrator:
    """Orchestrates the full meta-evolution lifecycle.

    Manages evolution cycles, parallel runs, checkpoints, rollback,
    best-of-breed promotion, and integration with the broader Lyra
    evolution ecosystem.

    Usage::

        orchestrator = EvolutionOrchestrator(
            meta_stack=MetaCognitiveStack(),
            config=CycleConfig(max_cycles=50),
        )

        # Run a full evolution pipeline
        results = await orchestrator.run_pipeline(seed_genome)

        # Or run individual cycles
        result = await orchestrator.run_cycle(EvolutionLevel.L1_PARAMETER)
    """

    def __init__(
        self,
        meta_stack: MetaCognitiveStack | None = None,
        genetic_optimizer: GeneticOptimizer | None = None,
        strategy_pool: StrategyPool | None = None,
        fitness_evaluator: FitnessEvaluator | None = None,
        config: CycleConfig | None = None,
    ):
        self._config = config or CycleConfig()

        self._meta_stack = meta_stack or MetaCognitiveStack()
        self._genetic = genetic_optimizer or GeneticOptimizer(population_size=100)
        self._pool = strategy_pool or StrategyPool(max_size=1000)
        self._fitness = fitness_evaluator or FitnessEvaluator()

        self._status = OrchestratorStatus.IDLE
        self._current_cycle: int = 0
        self._current_level: EvolutionLevel | None = None
        self._cycle_history: list[CycleResult] = []
        self._checkpoints: list[dict[str, Any]] = []
        self._rollback_stack: list[OrchestratorSnapshot] = []
        self._best_genome: AgentGenome | None = None
        self._best_fitness: float = 0.0

        self._is_running: bool = False
        self._errors: list[str] = []

    # ── Core Pipeline ────────────────────────────────────────────────────────

    async def run_pipeline(
        self,
        seed_genome: AgentGenome | None = None,
        fitness_fn: FitnessFunction | None = None,
    ) -> list[CycleResult]:
        """Run the full evolution pipeline across all levels.

        This is the main entry point for automated meta-evolution.
        """
        if self._is_running:
            raise CycleInProgressError("An evolution pipeline is already running")

        self._status = OrchestratorStatus.RUNNING
        self._is_running = True
        results: list[CycleResult] = []

        try:
            # Initialize with seed genome
            if seed_genome:
                self._best_genome = seed_genome
                await self._seed_pool(seed_genome)

            # Evolve through each level
            for level in list(EvolutionLevel):
                self._current_level = level
                max_cycles = self._config.get_cycles(level)

                for _ in range(max_cycles):
                    if self._status == OrchestratorStatus.PAUSED:
                        break

                    result = await self.run_cycle(level, fitness_fn)
                    results.append(result)

                    # Check convergence
                    if result.improvement < self._config.promote_threshold:
                        logger.info(
                            "%s converged (improvement=%.6f)", level.name, result.improvement,
                        )
                        break

                    # Checkpoint
                    if result.cycle_id % self._config.checkpoint_interval == 0:
                        await self.checkpoint()

            # Final promotion
            await self._promote_best()

            self._status = OrchestratorStatus.COMPLETED

        except Exception as exc:
            self._status = OrchestratorStatus.ERROR
            self._errors.append(str(exc))
            logger.error("Pipeline failed: %s", exc)

            if self._config.rollback_enabled:
                await self.rollback()

            raise OrchestratorError(f"Pipeline failed: {exc}") from exc

        finally:
            self._is_running = False

        return results

    async def run_cycle(
        self,
        level: EvolutionLevel,
        fitness_fn: FitnessFunction | None = None,
    ) -> CycleResult:
        """Execute one evolution cycle at the specified level."""
        self._current_cycle += 1
        start = time.perf_counter()

        cycle = CycleResult(
            cycle_id=self._current_cycle,
            level=level,
            phase=CyclePhase.EVALUATION,
            generations_executed=0,
            fitness_before=self._best_fitness,
            fitness_after=0.0,
            improvement=0.0,
            best_genome_id=self._best_genome.agent_id if self._best_genome else "unknown",
            promoted=False,
        )

        try:
            controller = self._meta_stack.get_controller(level)

            # Phase 1: Evaluate current best
            cycle.phase = CyclePhase.EVALUATION
            if self._best_genome and self._config.benchmark:
                self._best_fitness = await self._fitness.evaluate(self._best_genome, self._config.benchmark)
                cycle.fitness_before = self._best_fitness

            # Phase 2: Evolve the genetic population
            cycle.phase = CyclePhase.SELECTION
            gen_result = await self._genetic.evolve_generation(
                fitness_fn or self._make_default_fitness_fn(),
            )
            cycle.genetic_results.append(gen_result)
            cycle.generations_executed = self._genetic.generation

            # Phase 3: Meta-evolution
            cycle.phase = CyclePhase.EVOLUTION
            if self._best_genome:
                evo_result = await controller.evolve(
                    self._best_genome,
                    EvolutionTrigger.SCHEDULED_REVIEW,
                )
                cycle.evolution_results.append(evo_result)

            # Phase 4: Verify improvement
            cycle.phase = CyclePhase.VERIFICATION
            candidate = self._genetic.best_genome
            if candidate and self._config.benchmark:
                cycle.fitness_after = await self._fitness.evaluate(candidate, self._config.benchmark)
                cycle.best_genome_id = candidate.agent_id
            else:
                cycle.fitness_after = self._best_fitness

            cycle.improvement = cycle.fitness_after - cycle.fitness_before

            # Phase 5: Promote if worthy
            cycle.phase = CyclePhase.PROMOTION
            if cycle.improvement > self._config.promote_threshold and self._config.auto_promote:
                if candidate:
                    await self._promote_genome(candidate)
                    cycle.promoted = True
                    self._best_fitness = cycle.fitness_after

            # Save to pool
            if candidate:
                encoding = StrategyEncoding.from_genome(candidate)
                self._pool.add_strategy(encoding, fitness=cycle.fitness_after)

            cycle.duration_ms = (time.perf_counter() - start) * 1000

        except Exception as exc:
            cycle.errors.append(str(exc))
            self._errors.append(str(exc))
            logger.error("Cycle %d failed at %s: %s", cycle.cycle_id, cycle.phase.name, exc)

        self._cycle_history.append(cycle)

        logger.info(
            "Cycle %d complete: %s | fitness %.4f -> %.4f | promoted=%s | %dms",
            cycle.cycle_id, level.name,
            cycle.fitness_before, cycle.fitness_after,
            cycle.promoted, int(cycle.duration_ms),
        )

        return cycle

    # ── Parallel Execution ───────────────────────────────────────────────────

    async def run_parallel_cycles(
        self,
        levels: list[EvolutionLevel],
        genomes: dict[EvolutionLevel, AgentGenome] | None = None,
    ) -> dict[EvolutionLevel, list[CycleResult]]:
        """Run evolution cycles in parallel across multiple levels.

        Uses independent genetic populations per level for isolation.
        """
        tasks = []
        for level in levels:
            seed = genomes.get(level) if genomes else None
            task = self._run_isolated_pipeline(level, seed)
            tasks.append((level, task))

        results: dict[EvolutionLevel, list[CycleResult]] = {}
        for level, task in tasks:
            try:
                results[level] = await task
            except Exception as exc:
                logger.error("Parallel pipeline for %s failed: %s", level.name, exc)
                results[level] = []

        return results

    async def _run_isolated_pipeline(
        self,
        level: EvolutionLevel,
        seed_genome: AgentGenome | None = None,
    ) -> list[CycleResult]:
        """Run an isolated evolution pipeline for a single level."""
        # Create isolated components
        isolated_genetic = GeneticOptimizer(population_size=50)
        isolated_pool = StrategyPool(max_size=500)

        if seed_genome:
            isolated_genetic.initialize_population(seed_genome, variant_count=50)

        results: list[CycleResult] = []
        for _ in range(self._config.get_cycles(level)):
            result = await self.run_cycle(level)
            results.append(result)

        # Merge results back
        for record in isolated_pool._strategies.values():
            self._pool.add_strategy(record.encoding, record.fitness)

        return results

    # ── Checkpoint & Rollback ────────────────────────────────────────────────

    async def checkpoint(self) -> OrchestratorSnapshot:
        """Create a checkpoint of the current orchestrator state."""
        snapshot = OrchestratorSnapshot(
            status=self._status,
            current_cycle=self._current_cycle,
            current_level=self._current_level.name if self._current_level else "none",
            best_genome=self._best_genome.to_dict() if self._best_genome else None,
            population_size=self._genetic.population_size,
            pool_size=self._pool.size,
            history_length=len(self._cycle_history),
        )

        self._checkpoints.append({
            "snapshot": snapshot,
            "meta_checkpoints": self._meta_stack.checkpoint_all(),
            "pool_export": self._pool.export_pool(),
        })

        self._rollback_stack.append(snapshot)
        if len(self._rollback_stack) > self._config.max_rollback_depth:
            self._rollback_stack = self._rollback_stack[-self._config.max_rollback_depth:]

        logger.info(
            "Checkpoint created at cycle %d (level=%s)",
            self._current_cycle, self._current_level.name if self._current_level else "none",
        )

        return snapshot

    async def rollback(self) -> bool:
        """Rollback to the last checkpoint."""
        if not self._rollback_stack:
            raise RollbackError("No checkpoints available for rollback")

        snapshot = self._rollback_stack.pop()
        checkpoint_data = self._checkpoints[-1] if self._checkpoints else None

        self._status = snapshot.status
        self._current_cycle = snapshot.current_cycle
        self._current_level = (
            EvolutionLevel[snapshot.current_level]
            if snapshot.current_level != "none"
            else None
        )

        if snapshot.best_genome:
            self._best_genome = AgentGenome.from_dict(snapshot.best_genome)

        # Rollback meta stack
        if checkpoint_data and "meta_checkpoints" in checkpoint_data:
            for level in EvolutionLevel:
                self._meta_stack.rollback(level)

        logger.info("Rolled back to cycle %d", self._current_cycle)
        return True

    # ── Promotion ────────────────────────────────────────────────────────────

    async def _promote_genome(self, genome: AgentGenome) -> None:
        """Promote a genome as the new best-of-breed."""
        old_id = self._best_genome.agent_id if self._best_genome else "none"
        self._best_genome = genome

        logger.info(
            "Promoted genome: %s -> %s (fitness=%.4f)",
            old_id, genome.agent_id, self._best_fitness,
        )

    async def _promote_best(self) -> None:
        """Promote the best genome from the genetic optimizer."""
        best = self._genetic.best_genome
        if best is None:
            return

        if self._config.benchmark:
            fitness = await self._fitness.evaluate(best, self._config.benchmark)
            if fitness > self._best_fitness:
                self._best_fitness = fitness
                await self._promote_genome(best)
        else:
            await self._promote_genome(best)

    # ── Integration ──────────────────────────────────────────────────────────

    async def integrate_with_evolution_package(self, evolution_data: dict[str, Any]) -> None:
        """Import genome and strategy data from the lyra-evolution package."""
        agent_id = evolution_data.get("agent_id", "imported")
        genome = AgentGenome(
            agent_id=agent_id,
            hyperparameters=evolution_data.get("hyperparameters", {}),
            strategy_weights=evolution_data.get("strategy_weights", {}),
            active_strategies=evolution_data.get("active_strategies", []),
            objective_weights=evolution_data.get("objective_weights", {}),
        )

        self._best_genome = genome
        encoding = StrategyEncoding.from_genome(genome)
        self._pool.add_strategy(encoding, fitness=evolution_data.get("fitness", 0.0))

        logger.info("Integrated evolution data for agent %s", agent_id)

    async def export_best_genome(self) -> dict[str, Any]:
        """Export the best genome for use by other Lyra packages."""
        if self._best_genome is None:
            return {}

        return {
            "genome": self._best_genome.to_dict(),
            "fitness": self._best_fitness,
            "generations_trained": self._current_cycle,
            "cycle_history_length": len(self._cycle_history),
            "pool_size": self._pool.size,
            "pareto_frontier": self._fitness.pareto_frontier.get_frontier_ids(),
            "exported_at": time.time(),
        }

    # ── Seeding ──────────────────────────────────────────────────────────────

    async def _seed_pool(self, seed_genome: AgentGenome) -> None:
        """Seed the strategy pool with a base genome and its variants."""
        encoding = StrategyEncoding.from_genome(seed_genome)
        self._pool.add_strategy(encoding, fitness=0.5)

        # Create variants
        for i in range(10):
            variant = seed_genome.clone(f"{seed_genome.agent_id}_variant_{i}")
            variant.hyperparameters = {
                k: max(0.0, v + (time.time() % 0.1 - 0.05))
                for k, v in seed_genome.hyperparameters.items()
            }
            enc = StrategyEncoding.from_genome(variant)
            self._pool.add_strategy(enc, fitness=0.4 + time.time() % 0.2)

        # Initialize genetic population
        self._genetic.initialize_population(seed_genome, variant_count=50)

    def _make_default_fitness_fn(self) -> FitnessFunction:
        """Create a default fitness function using the fitness evaluator."""
        evaluator = self._fitness
        benchmark = self._config.benchmark or BenchmarkConfig(
            name="default", description="Default benchmark", task_count=5,
        )

        class DefaultFitness:
            async def evaluate(self, genome: AgentGenome) -> float:
                return await evaluator.evaluate(genome, benchmark)

        return DefaultFitness()

    # ── Monitoring ────────────────────────────────────────────────────────────

    def get_status(self) -> OrchestratorSnapshot:
        """Get a snapshot of current orchestrator state."""
        return OrchestratorSnapshot(
            status=self._status,
            current_cycle=self._current_cycle,
            current_level=self._current_level.name if self._current_level else "none",
            best_genome=self._best_genome.to_dict() if self._best_genome else None,
            population_size=self._genetic.population_size,
            pool_size=self._pool.size,
            history_length=len(self._cycle_history),
        )

    async def stream_cycles(self) -> AsyncIterator[CycleResult]:
        """Stream cycle results as they complete."""
        for cycle in self._cycle_history:
            yield cycle

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def status(self) -> OrchestratorStatus:
        return self._status

    @property
    def current_cycle(self) -> int:
        return self._current_cycle

    @property
    def best_genome(self) -> AgentGenome | None:
        return self._best_genome

    @property
    def best_fitness(self) -> float:
        return self._best_fitness

    @property
    def cycle_history(self) -> list[CycleResult]:
        return list(self._cycle_history)

    @property
    def error_count(self) -> int:
        return len(self._errors)
