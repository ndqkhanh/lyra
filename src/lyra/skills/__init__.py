"""
Skills system for Lyra.

This module provides infrastructure for managing skills - reusable
knowledge and patterns that agents can apply to tasks.
"""

from .evolution import (
    CORRECTNESS,
    COMPLETENESS,
    CLARITY,
    EFFICIENCY,
    SAFETY,
    RUBRIC_DIMENSIONS,
    DIMENSION_WEIGHTS,
    EvalResult,
    EvalScore,
    EvolutionConfig,
    EvolutionRound,
    SkillEvolutionEngine,
)
from .executor import (
    ExecutionPlan,
    ExecutionResult,
    ExecutionStatus,
    SkillExecutor,
    SkillHook,
)
from .importer import ECCSkillImporter, ImportResult
from .parser import SkillParser
from .registry import CycleError, SkillGraph, SkillRegistry
from .skill import Skill, SkillCategory, SkillSearchResult
from .skillnet import (
    CONFLICT,
    DEPENDENCY,
    PREREQUISITE,
    SIMILARITY,
    GraphTraversal,
    GraphVisualization,
    LinkType,
    SkillGraphLink,
    SkillNet,
    SkillNetAutoCreator,
    SkillRecommender,
)
from .quality_calibrator import (
    CalibrationResult,
    CalibrationSample,
    QualityCalibrator,
    RegressionReport,
    calibrate_from_feedback,
)

__all__ = [
    "Skill",
    "SkillCategory",
    "SkillSearchResult",
    "SkillRegistry",
    "SkillGraph",
    "CycleError",
    "SkillParser",
    "ECCSkillImporter",
    "ImportResult",
    "SkillExecutor",
    "ExecutionPlan",
    "ExecutionResult",
    "ExecutionStatus",
    "SkillHook",
    # evolution
    "SkillEvolutionEngine",
    "EvolutionConfig",
    "EvolutionRound",
    "EvalResult",
    "EvalScore",
    "CORRECTNESS",
    "COMPLETENESS",
    "CLARITY",
    "EFFICIENCY",
    "SAFETY",
    "RUBRIC_DIMENSIONS",
    "DIMENSION_WEIGHTS",
    # skillnet
    "SkillNetAutoCreator",
    "SkillNet",
    "SkillGraphLink",
    "DEPENDENCY",
    "PREREQUISITE",
    "SIMILARITY",
    "CONFLICT",
    "LinkType",
    # advanced skill graph
    "GraphTraversal",
    "SkillRecommender",
    "GraphVisualization",
    # quality calibrator
    "QualityCalibrator",
    "CalibrationResult",
    "CalibrationSample",
    "RegressionReport",
    "calibrate_from_feedback",
]

__version__ = "1.2.0"
