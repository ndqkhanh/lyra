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

from .exceptions import (
    EvolutionError,
    PatchError,
    BenchmarkError,
    RegressionError,
    VersionError,
    MetricsError,
)

from .trajectory_patcher import (
    PatchType,
    TrajectoryPatch,
    PatchResult,
    TrajectoryPatcher,
)

from .lifelong_learner import (
    LearningCycle,
    LearningConfig,
    LearningState,
    LifelongLearner,
)

from .skill_benchmark import (
    Difficulty,
    TaskFamily,
    BenchmarkTask,
    BenchmarkResult,
    BenchmarkReport,
    SkillBenchmark,
)

from .regression_tester import (
    TestCase,
    TestSuite,
    RegressionResult,
    RegressionReport,
    RegressionTester,
)

from .version_manager import (
    VersionStatus,
    SkillVersion,
    VersionDiff,
    VersionHistory,
    VersionManager,
)

from .evolution_metrics import (
    TrendDirection,
    MetricsSnapshot,
    EvolutionTrend,
    PeriodComparison,
    EvolutionReport,
    EvolutionMetrics,
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
