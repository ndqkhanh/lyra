"""Lyra Skill Evolution — Agentic skill evolution, lifelong learning, and benchmarking.

Supports:
- Lifelong learning cycles with skill patching
- Trajectory-driven patching from agent traces
- SkillFlow 166-task benchmark evaluation
- Capability regression testing
- Skill versioning and rollback
- Evolution metrics and trend tracking
"""

from __future__ import annotations

from .evolution_metrics import (
    EvolutionMetrics,
    EvolutionReport,
    EvolutionTrend,
    MetricsSnapshot,
    PeriodComparison,
    TrendDirection,
)
from .exceptions import (
    BenchmarkError,
    EvolutionError,
    MetricsError,
    PatchError,
    RegressionError,
    VersionError,
)
from .lifelong_learner import (
    LearningConfig,
    LearningCycle,
    LearningState,
    LifelongLearner,
)
from .regression_tester import (
    RegressionReport,
    RegressionResult,
    RegressionTester,
    TestCase,
    TestSuite,
)
from .skill_benchmark import (
    BenchmarkReport,
    BenchmarkResult,
    BenchmarkTask,
    Difficulty,
    SkillBenchmark,
    TaskFamily,
)
from .trajectory_patcher import (
    PatchResult,
    PatchType,
    TrajectoryPatch,
    TrajectoryPatcher,
)
from .version_manager import (
    SkillVersion,
    VersionDiff,
    VersionHistory,
    VersionManager,
    VersionStatus,
)

__all__ = [
    # Exceptions
    "EvolutionError",
    "PatchError",
    "BenchmarkError",
    "RegressionError",
    "VersionError",
    "MetricsError",
    # Trajectory patcher
    "PatchType",
    "TrajectoryPatch",
    "PatchResult",
    "TrajectoryPatcher",
    # Lifelong learner
    "LearningCycle",
    "LearningConfig",
    "LearningState",
    "LifelongLearner",
    # Skill benchmark
    "Difficulty",
    "TaskFamily",
    "BenchmarkTask",
    "BenchmarkResult",
    "BenchmarkReport",
    "SkillBenchmark",
    # Regression tester
    "TestCase",
    "TestSuite",
    "RegressionResult",
    "RegressionReport",
    "RegressionTester",
    # Version manager
    "VersionStatus",
    "SkillVersion",
    "VersionDiff",
    "VersionHistory",
    "VersionManager",
    # Evolution metrics
    "TrendDirection",
    "MetricsSnapshot",
    "EvolutionTrend",
    "PeriodComparison",
    "EvolutionReport",
    "EvolutionMetrics",
]
