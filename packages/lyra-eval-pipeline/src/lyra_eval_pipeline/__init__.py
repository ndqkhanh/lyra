"""Lyra Eval Pipeline — Evaluation pipeline framework with domain evaluation, adaptive rubrics,
cross-model judging, cost guardrails, leaderboards, and report generation."""

from __future__ import annotations

from lyra_eval_pipeline.adaptive_rubric import (
    AdaptiveRubric,
    RubricDimension,
    RubricResult,
    RubricScore,
    RubricTemplate,
)
from lyra_eval_pipeline.bench_guard import (
    BenchGuard,
    BenchGuardConfig,
    CostEstimate,
    GuardResult,
)
from lyra_eval_pipeline.cross_model_judge import (
    ConsensusResult,
    CrossModelJudge,
    JudgeModel,
    JudgePanel,
    ModelVerdict,
)
from lyra_eval_pipeline.domain_evaluator import (
    DomainEvalConfig,
    DomainEvalReport,
    DomainEvaluator,
    EvalResult,
    EvalSample,
)
from lyra_eval_pipeline.eval_scheduler import (
    EvalJob,
    EvalScheduler,
    ScheduleConfig,
    ScheduleStatus,
)
from lyra_eval_pipeline.exceptions import (
    BenchGuardError,
    CrossModelError,
    DomainEvalError,
    EvalPipelineError,
    LeaderboardError,
    ReportError,
    RubricError,
    SchedulerError,
)
from lyra_eval_pipeline.leaderboard import (
    HistoricalEntry,
    Leaderboard,
    LeaderboardEntry,
    LeaderboardManager,
)
from lyra_eval_pipeline.report_generator import (
    EvalReport,
    ReportArtifact,
    ReportConfig,
    ReportGenerator,
)

__all__ = [
    # exceptions
    "EvalPipelineError",
    "DomainEvalError",
    "RubricError",
    "CrossModelError",
    "BenchGuardError",
    "LeaderboardError",
    "SchedulerError",
    "ReportError",
    # domain_evaluator
    "DomainEvalConfig",
    "EvalSample",
    "EvalResult",
    "DomainEvalReport",
    "DomainEvaluator",
    # adaptive_rubric
    "RubricDimension",
    "RubricScore",
    "RubricResult",
    "RubricTemplate",
    "AdaptiveRubric",
    # cross_model_judge
    "JudgeModel",
    "ModelVerdict",
    "ConsensusResult",
    "JudgePanel",
    "CrossModelJudge",
    # bench_guard
    "BenchGuardConfig",
    "CostEstimate",
    "GuardResult",
    "BenchGuard",
    # leaderboard
    "LeaderboardEntry",
    "Leaderboard",
    "HistoricalEntry",
    "LeaderboardManager",
    # eval_scheduler
    "ScheduleConfig",
    "EvalJob",
    "ScheduleStatus",
    "EvalScheduler",
    # report_generator
    "ReportConfig",
    "EvalReport",
    "ReportArtifact",
    "ReportGenerator",
]
