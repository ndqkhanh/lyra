"""lyra-evals: eval runner + corpora + public-benchmark adapters."""
from __future__ import annotations

from .aer import AERStore, AgentExecutionRecord, new_aer
from .slo import DEFAULT_SLOS, SLOBreach, SLOTracker
from .adapters import (
    ConversationDriver,
    LoCoEvalResult,
    LoCoEvalTask,
    PublicBenchmarkTask,
    SWEBenchProAdapter,
    load_swe_bench_pro,
    score_requirement_coverage,
    write_submission,
)
from .contamination import ContaminationError, ContaminationGuard
from .corpora import (
    Task,
    golden_tasks,
    long_horizon_tasks,
    red_team_tasks,
)
from .runner import EvalRunner, Report, TaskResult
from .snapshot import HarnessSnapshot, snapshot_hash

__version__ = "0.1.0"

__all__ = [
    # Phase A — AER + SLO
    "AERStore",
    "AgentExecutionRecord",
    "DEFAULT_SLOS",
    "SLOBreach",
    "SLOTracker",
    "new_aer",
    # Legacy
    "ContaminationError",
    "ContaminationGuard",
    "ConversationDriver",
    "EvalRunner",
    "HarnessSnapshot",
    "LoCoEvalResult",
    "LoCoEvalTask",
    "PublicBenchmarkTask",
    "Report",
    "SWEBenchProAdapter",
    "Task",
    "TaskResult",
    "golden_tasks",
    "load_swe_bench_pro",
    "long_horizon_tasks",
    "red_team_tasks",
    "score_requirement_coverage",
    "snapshot_hash",
    "write_submission",
]
