"""Meta Evolution — Four-level meta-cognitive evolution stack for recursive self-improvement.

Provides genetic optimization, strategy pools, fitness evaluation,
and orchestration for autonomous agent self-improvement across four
meta-cognitive levels.

Level 1: Parameter optimization (hyperparameter tuning)
Level 2: Strategy evolution (algorithm selection)
Level 3: Architecture evolution (component restructuring)
Level 4: Goal evolution (objective function adaptation)
"""

from __future__ import annotations

from .fitness import (
    BenchmarkConfig,
    BenchmarkResult,
    FitnessError,
    FitnessEvaluator,
    FitnessLandscape,
    FitnessWeights,
    IncompleteBenchmarkError,
    ObjectiveDimension,
    ObjectiveVector,
    ParetoError,
    ParetoFrontier,
)
from .genetic_optimizer import (
    CrossoverError,
    CrossoverOperator,
    CrossoverResult,
    GeneticOptimizationResult,
    GeneticOptimizer,
    GeneticOptimizerError,
    MutationOperator,
    PopulationEmptyError,
    RankSelection,
    RouletteSelection,
    SelectionError,
    SelectionResult,
    SelectionStrategy,
    TournamentSelection,
)
from .meta_evolution import (
    AgentGenome,
    ArchitectureController,
    ConvergenceStatus,
    CyclePhase,
    EvolutionConfig,
    EvolutionConvergedError,
    EvolutionLevel,
    EvolutionObserver,
    EvolutionResult,
    EvolutionState,
    EvolutionTrigger,
    FitnessFunction,
    GoalController,
    InvalidGenomeError,
    LevelController,
    LevelNotReadyError,
    MetaCognitiveStack,
    MetaEvolutionError,
    ParameterController,
    RollbackError,
    StrategyController,
)
from .orchestrator import (
    CycleConfig,
    CycleInProgressError,
    CycleResult,
    EvolutionOrchestrator,
    IntegrationError,
    OrchestratorError,
    OrchestratorSnapshot,
    OrchestratorStatus,
    RollbackError as OrchestratorRollbackError,
)
from .strategy_pool import (
    PoolCapacityError,
    SimilarityMetrics,
    StrategyEncoding,
    StrategyNotFoundError,
    StrategyPool,
    StrategyPoolError,
    StrategyRecord,
)

__all__ = [
    # ── Meta Evolution (Core) ─────────────────────────────────────────
    "MetaCognitiveStack",
    "AgentGenome",
    "EvolutionLevel",
    "EvolutionTrigger",
    "ConvergenceStatus",
    "EvolutionConfig",
    "EvolutionState",
    "EvolutionResult",
    "CyclePhase",
    "LevelController",
    "ParameterController",
    "StrategyController",
    "ArchitectureController",
    "GoalController",
    "FitnessFunction",
    "EvolutionObserver",
    # ── Meta Evolution Exceptions ─────────────────────────────────────
    "MetaEvolutionError",
    "EvolutionConvergedError",
    "LevelNotReadyError",
    "RollbackError",
    "InvalidGenomeError",
    # ── Genetic Optimizer ─────────────────────────────────────────────
    "GeneticOptimizer",
    "CrossoverOperator",
    "MutationOperator",
    "SelectionStrategy",
    "TournamentSelection",
    "RouletteSelection",
    "RankSelection",
    "SelectionResult",
    "CrossoverResult",
    "GeneticOptimizationResult",
    # ── Genetic Optimizer Exceptions ──────────────────────────────────
    "GeneticOptimizerError",
    "PopulationEmptyError",
    "SelectionError",
    "CrossoverError",
    # ── Strategy Pool ─────────────────────────────────────────────────
    "StrategyPool",
    "StrategyEncoding",
    "StrategyRecord",
    "SimilarityMetrics",
    # ── Strategy Pool Exceptions ──────────────────────────────────────
    "StrategyPoolError",
    "StrategyNotFoundError",
    "PoolCapacityError",
    # ── Fitness ───────────────────────────────────────────────────────
    "FitnessEvaluator",
    "FitnessWeights",
    "ParetoFrontier",
    "ObjectiveVector",
    "ObjectiveDimension",
    "FitnessLandscape",
    "BenchmarkConfig",
    "BenchmarkResult",
    # ── Fitness Exceptions ────────────────────────────────────────────
    "FitnessError",
    "IncompleteBenchmarkError",
    "ParetoError",
    # ── Orchestrator ──────────────────────────────────────────────────
    "EvolutionOrchestrator",
    "CycleConfig",
    "CycleResult",
    "OrchestratorSnapshot",
    "OrchestratorStatus",
    # ── Orchestrator Exceptions ───────────────────────────────────────
    "OrchestratorError",
    "CycleInProgressError",
    "IntegrationError",
    "OrchestratorRollbackError",
]
