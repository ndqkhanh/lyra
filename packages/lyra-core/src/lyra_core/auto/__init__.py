"""Phase 4.2 — Autonomy & Benchmarking modules.

Goal decomposition engine, budget enforcement, verification-driven
progress, mission control, campaign coordination, and unified
benchmark harness for tracking Lyra's 7-domain performance.
"""
from __future__ import annotations

from .benchmark_harness import (
    BenchmarkDomain,
    BenchmarkHarness,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkStatus,
)
from .budget_enforcer import (
    BudgetEnforcer,
    BudgetLevel,
    BudgetLimits,
    BudgetState,
)
from .campaign_coordinator import (
    CampaignConfig,
    CampaignCoordinator,
    CampaignResult,
    CampaignState,
    CampaignStatus,
    MissionDependency,
)
from .goal_decomposer import (
    Goal,
    GoalDecomposer,
    GoalProgressReport,
    GoalType,
    Milestone,
    MilestoneStatus,
)
from .mission_control import (
    MissionConfig,
    MissionControl,
    MissionPriority,
    MissionResult,
    MissionState,
    MissionStatus,
    TaskState,
)
from .verifier_driven_progress import (
    ProgressReport,
    VerificationGate,
    VerificationResult,
    VerificationStatus,
    VerifierDrivenProgress,
)

__all__ = [
    "BenchmarkDomain",
    "BenchmarkHarness",
    "BenchmarkResult",
    "BenchmarkRun",
    "BenchmarkStatus",
    "BudgetEnforcer",
    "BudgetLevel",
    "BudgetLimits",
    "BudgetState",
    "CampaignConfig",
    "CampaignCoordinator",
    "CampaignResult",
    "CampaignState",
    "CampaignStatus",
    "Goal",
    "GoalDecomposer",
    "GoalProgressReport",
    "GoalType",
    "Milestone",
    "MilestoneStatus",
    "MissionConfig",
    "MissionControl",
    "MissionDependency",
    "MissionPriority",
    "MissionResult",
    "MissionState",
    "MissionStatus",
    "ProgressReport",
    "TaskState",
    "VerificationGate",
    "VerificationResult",
    "VerificationStatus",
    "VerifierDrivenProgress",
]
