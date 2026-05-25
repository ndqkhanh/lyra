"""Lyra Self-Rewrite — DGM (Differentiable Goal Model) HyperAgent engine for recursive self-improvement through goal-driven mutation, multi-objective fitness, and constraint-guided code rewrite generation."""

from __future__ import annotations

from lyra_self_rewrite.exceptions import (  # type: ignore[import-unused]
    ConstraintError,
    ConvergenceError,
    FitnessError,
    GenerationError,
    GoalMutationError,
    HyperAgentError,
    RecursionError,
    RewriteValidationError,
    SelfRewriteError,
)
from lyra_self_rewrite.constraint_generator import (
    ConstraintCheck,
    ConstraintGenerator,
    ConstraintReport,
    ConstraintSpec,
)
from lyra_self_rewrite.fitness_evaluator import (
    FitnessConfig,
    FitnessEvaluator,
    FitnessScore,
    ParetoFront,
)
from lyra_self_rewrite.goal_mutator import (
    GoalMutationResult,
    GoalMutator,
    GoalSpec,
    MutationStrategy,
)
from lyra_self_rewrite.hyper_agent import (
    AgentGene,
    HyperAgent,
    HyperAgentConfig,
    HyperAgentEngine,
    Population,
)
from lyra_self_rewrite.recursive_loop import (
    LoopConfig,
    LoopIteration,
    LoopResult,
    RecursiveLoop,
)
from lyra_self_rewrite.rewrite_generator import (
    GeneratedRewrite,
    RewriteGenerator,
    RewriteLibrary,
    RewriteTemplate,
)
from lyra_self_rewrite.rewrite_validator import (
    ValidationConfig,
    ValidationIssue,
    ValidationResult,
    RewriteValidator,
)

__all__ = [
    # exceptions
    "SelfRewriteError",
    "HyperAgentError",
    "GoalMutationError",
    "FitnessError",
    "ConstraintError",
    "GenerationError",
    "RecursionError",
    "RewriteValidationError",
    "ConvergenceError",
    # hyper_agent
    "HyperAgentConfig",
    "AgentGene",
    "HyperAgent",
    "Population",
    "HyperAgentEngine",
    # goal_mutator
    "GoalSpec",
    "MutationStrategy",
    "GoalMutationResult",
    "GoalMutator",
    # fitness_evaluator
    "FitnessConfig",
    "FitnessScore",
    "ParetoFront",
    "FitnessEvaluator",
    # constraint_generator
    "ConstraintSpec",
    "ConstraintCheck",
    "ConstraintReport",
    "ConstraintGenerator",
    # rewrite_generator
    "RewriteTemplate",
    "GeneratedRewrite",
    "RewriteLibrary",
    "RewriteGenerator",
    # recursive_loop
    "LoopConfig",
    "LoopIteration",
    "LoopResult",
    "RecursiveLoop",
    # rewrite_validator
    "ValidationConfig",
    "ValidationIssue",
    "ValidationResult",
    "RewriteValidator",
]
