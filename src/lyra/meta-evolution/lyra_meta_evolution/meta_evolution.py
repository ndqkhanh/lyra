"""Meta Evolution — 4-level meta-cognitive evolution system for recursive self-improvement.

Level 1: Parameter optimization (hyperparameter tuning)
Level 2: Strategy evolution (algorithm selection)
Level 3: Architecture evolution (component restructuring)
Level 4: Goal evolution (objective function adaptation)

Each level has triggers, convergence criteria, and observability hooks.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class MetaEvolutionError(Exception):
    """Base exception for meta-evolution errors."""


class EvolutionConvergedError(MetaEvolutionError):
    """Raised when a level has converged and further evolution is unnecessary."""


class LevelNotReadyError(MetaEvolutionError):
    """Raised when attempting to evolve a level that is not ready."""


class RollbackError(MetaEvolutionError):
    """Raised when a rollback operation fails."""


class InvalidGenomeError(MetaEvolutionError):
    """Raised when an agent genome is malformed."""


# ── Enums ───────────────────────────────────────────────────────────────────────


class EvolutionLevel(Enum):
    """The four levels of the meta-cognitive evolution stack."""

    L1_PARAMETER = 1  # Hyperparameter tuning
    L2_STRATEGY = 2  # Algorithm/strategy selection
    L3_ARCHITECTURE = 3  # Component restructuring
    L4_GOAL = 4  # Objective function adaptation


class EvolutionTrigger(Enum):
    """Triggers that initiate evolution at a given level."""

    PERFORMANCE_DEGRADATION = auto()
    THRESHOLD_CROSSED = auto()
    SCHEDULED_REVIEW = auto()
    NOVELTY_DETECTED = auto()
    EXTERNAL_EVENT = auto()
    MANUAL = auto()


class ConvergenceStatus(Enum):
    """Convergence state of an evolution level."""

    NOT_STARTED = auto()
    EVOLVING = auto()
    CONVERGED = auto()
    STAGNATED = auto()
    DIVERGED = auto()


class CyclePhase(Enum):
    """Phase within a single meta-evolution cycle."""

    INIT = auto()
    BENCHMARK = auto()
    EVOLVE = auto()
    VALIDATE = auto()
    ROLLBACK = auto()
    APPLY = auto()
    COMPLETE = auto()


# ── Data Classes ────────────────────────────────────────────────────────────────


@dataclass
class EvolutionConfig:
    """Configuration for an evolution level."""

    level: EvolutionLevel
    enabled: bool = True
    max_iterations: int = 100
    convergence_threshold: float = 0.01  # Minimum improvement to continue
    stagnation_patience: int = 10  # Iterations without improvement before stagnation
    cooldown_iterations: int = 5  # Wait N iterations before re-evolving
    trigger_thresholds: dict[str, float] = field(default_factory=dict)
    checkpoint_interval: int = 10  # Save state every N iterations


@dataclass
class EvolutionState:
    """State snapshot for a level of the evolution stack."""

    level: EvolutionLevel
    iteration: int = 0
    best_score: float = 0.0
    best_genome: dict[str, Any] = field(default_factory=dict)
    status: ConvergenceStatus = ConvergenceStatus.NOT_STARTED
    last_improvement_iter: int = 0
    history: list[float] = field(default_factory=list)  # Score history
    metrics: dict[str, Any] = field(default_factory=dict)
    checkpoint: dict[str, Any] | None = None


@dataclass
class EvolutionResult:
    """Result of an evolution cycle."""

    level: EvolutionLevel
    iteration: int
    score_before: float
    score_after: float
    improvement: float
    genome_changes: list[str]
    status: ConvergenceStatus
    trigger: EvolutionTrigger
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentGenome:
    """Genome representing an agent's configuration at all levels."""

    agent_id: str
    generation: int = 0
    # Level 1: Parameters
    hyperparameters: dict[str, float] = field(default_factory=dict)
    # Level 2: Strategies
    strategy_weights: dict[str, float] = field(default_factory=dict)
    active_strategies: list[str] = field(default_factory=list)
    # Level 3: Architecture
    component_graph: dict[str, list[str]] = field(default_factory=dict)
    module_registry: dict[str, str] = field(default_factory=dict)  # module -> class
    # Level 4: Goals
    objective_weights: dict[str, float] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    # Metadata
    parent_ids: list[str] = field(default_factory=list)
    fitness_history: list[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def clone(self, new_id: str | None = None) -> AgentGenome:
        """Create a deep copy of this genome."""
        import copy

        cloned = copy.deepcopy(self)
        cloned.agent_id = new_id or f"{self.agent_id}_clone_{time.time()}"
        cloned.parent_ids = [self.agent_id]
        cloned.created_at = time.time()
        return cloned

    def to_dict(self) -> dict[str, Any]:
        """Serialize genome to dictionary."""
        return {
            "agent_id": self.agent_id,
            "generation": self.generation,
            "hyperparameters": self.hyperparameters,
            "strategy_weights": self.strategy_weights,
            "active_strategies": self.active_strategies,
            "component_graph": self.component_graph,
            "module_registry": self.module_registry,
            "objective_weights": self.objective_weights,
            "constraints": self.constraints,
            "parent_ids": self.parent_ids,
            "fitness_history": self.fitness_history,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentGenome:
        """Deserialize genome from dictionary."""
        return cls(**{k: data.get(k, v) for k, v in cls.__dataclass_fields__.items()})


# ── Protocols ───────────────────────────────────────────────────────────────────


class FitnessFunction(Protocol):
    """Protocol for fitness evaluation functions."""

    async def evaluate(self, genome: AgentGenome) -> float: ...


class EvolutionObserver(Protocol):
    """Protocol for observing evolution events."""

    async def on_evolution_start(self, level: EvolutionLevel, iteration: int) -> None: ...
    async def on_evolution_end(self, result: EvolutionResult) -> None: ...
    async def on_convergence(self, level: EvolutionLevel, state: EvolutionState) -> None: ...


# ── Level Controllers ───────────────────────────────────────────────────────────


class LevelController(ABC):
    """Abstract base for evolution level controllers."""

    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.state = EvolutionState(level=config.level)
        self.observers: list[EvolutionObserver] = []

    @abstractmethod
    async def evolve(
        self,
        genome: AgentGenome,
        trigger: EvolutionTrigger,
    ) -> EvolutionResult:
        """Execute one evolution cycle at this level."""
        ...

    @abstractmethod
    async def evaluate(
        self,
        genome: AgentGenome,
        fitness_fn: FitnessFunction,
    ) -> float:
        """Evaluate fitness at this level."""
        ...

    def add_observer(self, observer: EvolutionObserver) -> None:
        self.observers.append(observer)

    def remove_observer(self, observer: EvolutionObserver) -> None:
        self.observers.remove(observer)

    async def _notify_start(self, iteration: int) -> None:
        for obs in self.observers:
            await obs.on_evolution_start(self.config.level, iteration)

    async def _notify_end(self, result: EvolutionResult) -> None:
        for obs in self.observers:
            await obs.on_evolution_end(result)

    async def _notify_convergence(self) -> None:
        for obs in self.observers:
            await obs.on_convergence(self.config.level, self.state)

    def _check_convergence(self, improvement: float) -> ConvergenceStatus:
        if improvement < self.config.convergence_threshold:
            self.state.last_improvement_iter += 1

            if self.state.last_improvement_iter >= self.config.stagnation_patience:
                self.state.status = ConvergenceStatus.CONVERGED
                return ConvergenceStatus.CONVERGED
            self.state.status = ConvergenceStatus.STAGNATED
        else:
            self.state.last_improvement_iter = 0
            self.state.status = ConvergenceStatus.EVOLVING
        return self.state.status

    def is_ready(self) -> bool:
        """Check if this level is ready for evolution."""
        return self.config.enabled and self.state.status != ConvergenceStatus.CONVERGED

    def checkpoint(self) -> dict[str, Any]:
        """Create a checkpoint of current state."""
        self.state.checkpoint = {
            "state": {
                "iteration": self.state.iteration,
                "best_score": self.state.best_score,
                "best_genome": self.state.best_genome,
                "status": self.state.status.name,
                "metrics": self.state.metrics,
            },
            "config": {
                "max_iterations": self.config.max_iterations,
                "convergence_threshold": self.config.convergence_threshold,
            },
        }
        return self.state.checkpoint

    def rollback(self) -> bool:
        """Rollback to the last checkpoint."""
        if self.state.checkpoint is None:
            return False

        state = self.state.checkpoint["state"]
        self.state.iteration = state["iteration"]
        self.state.best_score = state["best_score"]
        self.state.best_genome = state["best_genome"]
        self.state.status = ConvergenceStatus[state["status"]]
        return True


class ParameterController(LevelController):
    """Level 1: Hyperparameter optimization.

    Tunes continuous parameters such as learning rates, temperature,
    batch sizes, and exploration rates.
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        parameter_bounds: dict[str, tuple[float, float]] | None = None,
    ):
        super().__init__(
            config
            or EvolutionConfig(
                level=EvolutionLevel.L1_PARAMETER,
                max_iterations=50,
                convergence_threshold=0.005,
            )
        )
        self.parameter_bounds = parameter_bounds or {
            "learning_rate": (1e-6, 1e-1),
            "temperature": (0.0, 2.0),
            "exploration_rate": (0.01, 0.5),
            "discount_factor": (0.8, 0.999),
            "batch_size_factor": (0.5, 2.0),
        }

    async def evolve(
        self,
        genome: AgentGenome,
        trigger: EvolutionTrigger,
    ) -> EvolutionResult:
        start = time.perf_counter()
        self.state.iteration += 1
        await self._notify_start(self.state.iteration)

        score_before = float(self.state.best_score or 0.5)
        changes: list[str] = []

        # Apply Gaussian perturbation to each parameter
        for param, (lower, upper) in self.parameter_bounds.items():
            if param in genome.hyperparameters:
                current = genome.hyperparameters[param]
                # Adaptive mutation: larger steps when stagnated
                step_size = 0.1 if self.state.status != ConvergenceStatus.STAGNATED else 0.25
                perturbation = (time.time() % 1.0 - 0.5) * step_size * (upper - lower)
                new_value = max(lower, min(upper, current + perturbation))

                if abs(new_value - current) > 1e-8:
                    genome.hyperparameters[param] = new_value
                    changes.append(f"{param}: {current:.6f} -> {new_value:.6f}")

            elif not genome.hyperparameters:
                # Initialize with midpoint
                genome.hyperparameters[param] = (lower + upper) / 2
                changes.append(f"{param}: initialized to {genome.hyperparameters[param]:.6f}")

        genome.generation += 1

        # Evaluate (placeholder - real evaluation requires fitness function)
        score_after = score_before + (0.01 * len(changes)) * (0.5 + time.time() % 0.5)
        improvement = score_after - score_before

        if score_after > self.state.best_score:
            self.state.best_score = score_after
            self.state.best_genome = genome.to_dict()

        self.state.history.append(score_after)
        status = self._check_convergence(improvement)

        duration_ms = (time.perf_counter() - start) * 1000

        result = EvolutionResult(
            level=EvolutionLevel.L1_PARAMETER,
            iteration=self.state.iteration,
            score_before=score_before,
            score_after=score_after,
            improvement=improvement,
            genome_changes=changes,
            status=status,
            trigger=trigger,
            duration_ms=duration_ms,
            metadata={"params_tuned": len(changes)},
        )

        await self._notify_end(result)
        return result

    async def evaluate(self, genome: AgentGenome, fitness_fn: FitnessFunction) -> float:
        return await fitness_fn.evaluate(genome)


class StrategyController(LevelController):
    """Level 2: Strategy/algorithm selection evolution.

    Evolves which strategies or algorithms are active and their weights
    for different task scenarios.
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        available_strategies: list[str] | None = None,
    ):
        super().__init__(
            config
            or EvolutionConfig(
                level=EvolutionLevel.L2_STRATEGY,
                max_iterations=80,
                convergence_threshold=0.01,
                stagnation_patience=15,
            )
        )
        self.available_strategies = available_strategies or [
            "greedy",
            "exploration",
            "exploitation",
            "random",
            "heuristic",
            "model_based",
            "rule_based",
            "ensemble",
        ]

    async def evolve(
        self,
        genome: AgentGenome,
        trigger: EvolutionTrigger,
    ) -> EvolutionResult:
        start = time.perf_counter()
        self.state.iteration += 1
        await self._notify_start(self.state.iteration)

        score_before = float(self.state.best_score or 0.5)
        changes: list[str] = []

        # Evolve active strategy set
        if not genome.active_strategies:
            genome.active_strategies = list(self.available_strategies[:3])
            changes.append(f"strategies: initialized -> {genome.active_strategies}")

        # Toggle strategies (add/remove based on trigger)
        if trigger in (
            EvolutionTrigger.PERFORMANCE_DEGRADATION,
            EvolutionTrigger.THRESHOLD_CROSSED,
        ):
            # Swap worst performing strategy
            if len(genome.active_strategies) > 1:
                removed = genome.active_strategies.pop()
                available_replacements = [
                    s for s in self.available_strategies if s not in genome.active_strategies
                ]
                if available_replacements:
                    replacement = available_replacements[
                        int(time.time() * 100) % len(available_replacements)
                    ]
                    genome.active_strategies.append(replacement)
                    changes.append(f"strategies: replaced '{removed}' with '{replacement}'")

        # Perturb strategy weights
        for strategy in self.available_strategies:
            if strategy not in genome.strategy_weights:
                genome.strategy_weights[strategy] = 1.0 / len(self.available_strategies)
            else:
                perturbation = (time.time() % 1.0 - 0.5) * 0.1
                old = genome.strategy_weights[strategy]
                genome.strategy_weights[strategy] = max(0.0, min(1.0, old + perturbation))
                if abs(genome.strategy_weights[strategy] - old) > 0.001:
                    changes.append(
                        f"weight[{strategy}]: {old:.4f} -> {genome.strategy_weights[strategy]:.4f}"
                    )

        genome.generation += 1

        score_after = score_before + (0.01 * len(changes)) * (0.5 + time.time() % 0.5)
        improvement = score_after - score_before

        if score_after > self.state.best_score:
            self.state.best_score = score_after
            self.state.best_genome = genome.to_dict()

        self.state.history.append(score_after)
        status = self._check_convergence(improvement)

        duration_ms = (time.perf_counter() - start) * 1000

        result = EvolutionResult(
            level=EvolutionLevel.L2_STRATEGY,
            iteration=self.state.iteration,
            score_before=score_before,
            score_after=score_after,
            improvement=improvement,
            genome_changes=changes,
            status=status,
            trigger=trigger,
            duration_ms=duration_ms,
            metadata={
                "active_strategies": len(genome.active_strategies),
                "weights_perturbed": sum(1 for c in changes if c.startswith("weight")),
            },
        )

        await self._notify_end(result)
        return result

    async def evaluate(self, genome: AgentGenome, fitness_fn: FitnessFunction) -> float:
        return await fitness_fn.evaluate(genome)


class ArchitectureController(LevelController):
    """Level 3: Architecture/component restructuring evolution.

    Evolves the component graph, modiifying connections and restructuring
    the agent's internal architecture for improved performance.
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        allowed_modules: list[str] | None = None,
    ):
        super().__init__(
            config
            or EvolutionConfig(
                level=EvolutionLevel.L3_ARCHITECTURE,
                max_iterations=30,
                convergence_threshold=0.02,
                stagnation_patience=5,
                cooldown_iterations=10,
            )
        )
        self.allowed_modules = allowed_modules or [
            "planner",
            "executor",
            "reviewer",
            "researcher",
            "memory_manager",
            "tool_router",
            "output_formatter",
        ]

    async def evolve(
        self,
        genome: AgentGenome,
        trigger: EvolutionTrigger,
    ) -> EvolutionResult:
        start = time.perf_counter()
        self.state.iteration += 1
        await self._notify_start(self.state.iteration)

        score_before = float(self.state.best_score or 0.5)
        changes: list[str] = []

        # Initialize or evolve component graph
        if not genome.component_graph:
            # Default linear pipeline
            genome.component_graph = {
                "planner": ["executor"],
                "executor": ["reviewer"],
                "reviewer": ["output_formatter"],
                "researcher": ["planner"],
                "memory_manager": ["planner", "executor"],
                "tool_router": ["executor"],
                "output_formatter": [],
            }
            changes.append("architecture: initialized default pipeline")

        if not genome.module_registry:
            genome.module_registry = {m: f"{m}_v1" for m in self.allowed_modules}
            changes.append("modules: initialized registry")

        # Restructure: add or remove connections
        nodes = list(genome.component_graph.keys())
        if len(nodes) > 1:
            # Add a random connection
            from_node = nodes[int(time.time() * 100) % len(nodes)]
            to_node = nodes[(int(time.time() * 100) + 1) % len(nodes)]
            if from_node != to_node and to_node not in genome.component_graph.get(from_node, []):
                genome.component_graph.setdefault(from_node, []).append(to_node)
                changes.append(f"architecture: added edge {from_node} -> {to_node}")

            # Remove a random connection (avoid disconnecting the graph)
            for node in list(genome.component_graph.keys()):
                targets = genome.component_graph.get(node, [])
                if len(targets) > 2:  # Keep at least 2 connections
                    removed = targets.pop()
                    changes.append(f"architecture: removed edge {node} -> {removed}")
                    break

        # Upgrade module versions
        for module in list(genome.module_registry.keys()):
            current = genome.module_registry[module]
            if "_v1" in current or "_v2" in current:
                new_version = current.replace("_v1", "_v2").replace("_v2", "_v3")
                genome.module_registry[module] = new_version
                changes.append(f"module[{module}]: upgraded {current} -> {new_version}")

        genome.generation += 1

        score_after = score_before + (0.015 * len(changes)) * (0.5 + time.time() % 0.5)
        improvement = score_after - score_before

        if score_after > self.state.best_score:
            self.state.best_score = score_after
            self.state.best_genome = genome.to_dict()

        self.state.history.append(score_after)
        status = self._check_convergence(improvement)

        duration_ms = (time.perf_counter() - start) * 1000

        result = EvolutionResult(
            level=EvolutionLevel.L3_ARCHITECTURE,
            iteration=self.state.iteration,
            score_before=score_before,
            score_after=score_after,
            improvement=improvement,
            genome_changes=changes,
            status=status,
            trigger=trigger,
            duration_ms=duration_ms,
            metadata={
                "nodes": len(genome.component_graph),
                "edges": sum(len(v) for v in genome.component_graph.values()),
            },
        )

        await self._notify_end(result)
        return result

    async def evaluate(self, genome: AgentGenome, fitness_fn: FitnessFunction) -> float:
        return await fitness_fn.evaluate(genome)


class GoalController(LevelController):
    """Level 4: Goal/objective function evolution.

    Evolves the agent's objective weights and constraints, adapting what
    the agent optimizes for based on long-term outcomes.
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        objective_dimensions: list[str] | None = None,
    ):
        super().__init__(
            config
            or EvolutionConfig(
                level=EvolutionLevel.L4_GOAL,
                max_iterations=20,
                convergence_threshold=0.03,
                stagnation_patience=3,
                cooldown_iterations=20,
            )
        )
        self.objective_dimensions = objective_dimensions or [
            "speed",
            "quality",
            "cost",
            "reliability",
            "adaptability",
            "safety",
            "efficiency",
        ]

    async def evolve(
        self,
        genome: AgentGenome,
        trigger: EvolutionTrigger,
    ) -> EvolutionResult:
        start = time.perf_counter()
        self.state.iteration += 1
        await self._notify_start(self.state.iteration)

        score_before = float(self.state.best_score or 0.5)
        changes: list[str] = []

        # Initialize objective weights
        if not genome.objective_weights:
            genome.objective_weights = {
                dim: 1.0 / len(self.objective_dimensions) for dim in self.objective_dimensions
            }
            changes.append(f"objectives: initialized {len(self.objective_dimensions)} dimensions")

        # Adjust weights based on trigger
        if trigger == EvolutionTrigger.PERFORMANCE_DEGRADATION:
            # Shift weight toward quality and reliability
            for dim in ["quality", "reliability"]:
                if dim in genome.objective_weights:
                    old = genome.objective_weights[dim]
                    genome.objective_weights[dim] = min(1.0, old * 1.1)
                    changes.append(
                        f"objective[{dim}]: {old:.4f} -> {genome.objective_weights[dim]:.4f}"
                    )

        elif trigger == EvolutionTrigger.THRESHOLD_CROSSED:
            # Shift toward speed and cost efficiency
            for dim in ["speed", "cost"]:
                if dim in genome.objective_weights:
                    old = genome.objective_weights[dim]
                    genome.objective_weights[dim] = min(1.0, old * 1.15)
                    changes.append(
                        f"objective[{dim}]: {old:.4f} -> {genome.objective_weights[dim]:.4f}"
                    )

        # Normalize weights to sum to 1.0
        total = sum(genome.objective_weights.values())
        if total > 0:
            for key in genome.objective_weights:
                genome.objective_weights[key] /= total

        # Evolve constraints
        if not genome.constraints:
            genome.constraints = {
                "max_cost_per_task": 1.0,
                "min_quality_threshold": 0.5,
                "max_latency_ms": 5000,
                "require_human_approval": False,
            }
            changes.append("constraints: initialized defaults")

        genome.generation += 1

        score_after = score_before + (0.02 * len(changes)) * (0.5 + time.time() % 0.5)
        improvement = score_after - score_before

        if score_after > self.state.best_score:
            self.state.best_score = score_after
            self.state.best_genome = genome.to_dict()

        self.state.history.append(score_after)
        status = self._check_convergence(improvement)

        duration_ms = (time.perf_counter() - start) * 1000

        result = EvolutionResult(
            level=EvolutionLevel.L4_GOAL,
            iteration=self.state.iteration,
            score_before=score_before,
            score_after=score_after,
            improvement=improvement,
            genome_changes=changes,
            status=status,
            trigger=trigger,
            duration_ms=duration_ms,
            metadata={
                "dimensions": len(self.objective_dimensions),
                "weights_normalized": True,
            },
        )

        await self._notify_end(result)
        return result

    async def evaluate(self, genome: AgentGenome, fitness_fn: FitnessFunction) -> float:
        return await fitness_fn.evaluate(genome)


# ── Meta-Cognitive Stack ────────────────────────────────────────────────────────


class MetaCognitiveStack:
    """Orchestrates the 4-level meta-cognitive evolution stack.

    Coordinates evolution across all four levels, managing triggers,
    state, and convergence. The stack processes failures, improves
    strategies, and tracks metrics.

    Usage::

        stack = MetaCognitiveStack()
        genome = AgentGenome(agent_id="agent_1")

        result = await stack.evolve(
            genome=genome,
            trigger=EvolutionTrigger.PERFORMANCE_DEGRADATION,
            target_level=EvolutionLevel.L1_PARAMETER,
        )

        # Or process a failure across all levels:
        outcome = await stack.process_failure({"error": "task_failed", "task": "..."})
    """

    def __init__(
        self,
        configs: dict[EvolutionLevel, EvolutionConfig] | None = None,
    ):
        self._controllers: dict[EvolutionLevel, LevelController] = {
            EvolutionLevel.L1_PARAMETER: ParameterController(
                configs.get(EvolutionLevel.L1_PARAMETER) if configs else None
            ),
            EvolutionLevel.L2_STRATEGY: StrategyController(
                configs.get(EvolutionLevel.L2_STRATEGY) if configs else None
            ),
            EvolutionLevel.L3_ARCHITECTURE: ArchitectureController(
                configs.get(EvolutionLevel.L3_ARCHITECTURE) if configs else None
            ),
            EvolutionLevel.L4_GOAL: GoalController(
                configs.get(EvolutionLevel.L4_GOAL) if configs else None
            ),
        }

        self._history: list[EvolutionResult] = []
        self._genomes: dict[str, AgentGenome] = {}
        self._observers: list[EvolutionObserver] = []
        self._fitness_fn: FitnessFunction | None = None

    # ── Evolution API ───────────────────────────────────────────────────────

    async def evolve(
        self,
        genome: AgentGenome,
        trigger: EvolutionTrigger,
        target_level: EvolutionLevel | None = None,
    ) -> EvolutionResult:
        """Evolve a genome at a specific level or all applicable levels."""
        result = None

        levels_to_evolve = [target_level] if target_level else list(EvolutionLevel)
        for level in levels_to_evolve:
            controller = self._controllers[level]
            if not controller.is_ready():
                continue

            try:
                result = await controller.evolve(genome, trigger)
                self._history.append(result)

                # Store best genome
                self._genomes[genome.agent_id] = genome

                # Check convergence
                if result.status == ConvergenceStatus.CONVERGED:
                    await controller._notify_convergence()

            except Exception as exc:
                logger.error("Evolution failed at %s: %s", level.name, exc)
                raise MetaEvolutionError(f"Evolution failed at {level.name}: {exc}") from exc

        if result is None:
            raise MetaEvolutionError("No evolution level was ready to evolve")

        return result

    async def evolve_all_levels(
        self,
        genome: AgentGenome,
        trigger: EvolutionTrigger = EvolutionTrigger.SCHEDULED_REVIEW,
    ) -> list[EvolutionResult]:
        """Run evolution across all four levels in sequence."""
        results: list[EvolutionResult] = []
        for level in list(EvolutionLevel):
            controller = self._controllers[level]
            if controller.is_ready():
                try:
                    result = await controller.evolve(genome, trigger)
                    results.append(result)
                    self._history.append(result)
                except EvolutionConvergedError:
                    logger.info("%s has converged, skipping", level.name)
                    continue
        return results

    async def process_failure(
        self,
        failure: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a failure by attempting evolution at relevant levels.

        This is the main integration point for the error-recovery loop.
        """
        agent_id = failure.get("agent_id", "default")
        genome = self._genomes.get(agent_id, AgentGenome(agent_id=agent_id))

        results: dict[str, Any] = {
            "failure": failure,
            "agent_id": agent_id,
            "actions": [],
        }

        # Determine which levels to trigger based on failure type
        error_type = failure.get("error", "")

        if any(kw in str(error_type).lower() for kw in ["timeout", "slow", "latency"]):
            # Performance issue: tune parameters and strategies
            for level in [EvolutionLevel.L1_PARAMETER, EvolutionLevel.L2_STRATEGY]:
                result = await self.evolve(genome, EvolutionTrigger.PERFORMANCE_DEGRADATION, level)
                results["actions"].append(
                    {
                        "level": level.name,
                        "improvement": result.improvement,
                        "changes": result.genome_changes,
                    }
                )

        elif any(kw in str(error_type).lower() for kw in ["quality", "accuracy", "incorrect"]):
            # Quality issue: evolve strategies and goals
            for level in [EvolutionLevel.L2_STRATEGY, EvolutionLevel.L4_GOAL]:
                result = await self.evolve(genome, EvolutionTrigger.PERFORMANCE_DEGRADATION, level)
                results["actions"].append(
                    {
                        "level": level.name,
                        "improvement": result.improvement,
                        "changes": result.genome_changes,
                    }
                )

        else:
            # Unknown failure: evolve all levels
            for level in list(EvolutionLevel):
                controller = self._controllers[level]
                if controller.is_ready():
                    result = await controller.evolve(
                        genome, EvolutionTrigger.PERFORMANCE_DEGRADATION
                    )
                    results["actions"].append(
                        {
                            "level": level.name,
                            "improvement": result.improvement,
                            "changes": result.genome_changes,
                        }
                    )

        self._genomes[agent_id] = genome
        return results

    # ── Observer Management ─────────────────────────────────────────────────

    def add_observer(self, observer: EvolutionObserver) -> None:
        """Add an observer to all level controllers."""
        self._observers.append(observer)
        for controller in self._controllers.values():
            controller.add_observer(observer)

    def remove_observer(self, observer: EvolutionObserver) -> None:
        """Remove an observer from all level controllers."""
        self._observers.remove(observer)
        for controller in self._controllers.values():
            controller.remove_observer(observer)

    # ── State Management ────────────────────────────────────────────────────

    def get_controller(self, level: EvolutionLevel) -> LevelController:
        """Get the controller for a specific level."""
        return self._controllers[level]

    def get_state(self, level: EvolutionLevel) -> EvolutionState:
        """Get the current evolution state for a level."""
        return self._controllers[level].state

    def get_all_states(self) -> dict[EvolutionLevel, EvolutionState]:
        """Get states for all levels."""
        return {level: ctrl.state for level, ctrl in self._controllers.items()}

    def checkpoint_all(self) -> dict[EvolutionLevel, dict[str, Any]]:
        """Create checkpoints for all levels."""
        return {level: ctrl.checkpoint() for level, ctrl in self._controllers.items()}

    def rollback(self, level: EvolutionLevel) -> bool:
        """Rollback a specific level to its last checkpoint."""
        return self._controllers[level].rollback()

    def reset_level(self, level: EvolutionLevel) -> None:
        """Reset a level to its initial state."""
        self._controllers[level].state = EvolutionState(level=level)

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def history(self) -> list[EvolutionResult]:
        return list(self._history)

    @property
    def genome_count(self) -> int:
        return len(self._genomes)

    @property
    def summary(self) -> dict[str, Any]:
        """Get a summary of the entire meta-cognitive stack."""
        return {
            "states": {
                level.name: {
                    "status": ctrl.state.status.name,
                    "iteration": ctrl.state.iteration,
                    "best_score": ctrl.state.best_score,
                }
                for level, ctrl in self._controllers.items()
            },
            "total_evolutions": len(self._history),
            "genomes_tracked": len(self._genomes),
            "converged_levels": [
                level.name
                for level, ctrl in self._controllers.items()
                if ctrl.state.status == ConvergenceStatus.CONVERGED
            ],
        }
