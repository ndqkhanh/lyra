"""Subagents + worktrees (Phase 7)."""
from __future__ import annotations

from .fs_sandbox import FsSandbox, FsSandboxViolation
from .merge import MergeResult, three_way_merge
from .orchestrator import (
    DepthLimitError,
    ScopeCollisionError,
    SubagentOrchestrator,
    SubagentResult,
    SubagentSpec,
)
from .presets import PresetBundle, PresetRole, SubagentPreset, load_presets
from .registry import SubagentRecord, SubagentRegistry, SubagentState
from .runner import (
    SubagentRunner,
    SubagentRunResult,
    SubagentRunSpec,
    SubagentStatus,
)
from .scheduler import (
    SchedulerError,
    SubagentDAGRun,
    SubagentDAGSpec,
    SubagentNodeResult,
    SubagentNodeStatus,
    SubagentScheduler,
)
from .variants import (
    VariantOutcome,
    VariantSpec,
    VariantStatus,
    VariantsResult,
    run_variants,
)
from .worktree import Worktree, WorktreeError, WorktreeManager

__all__ = [
    "DepthLimitError",
    "FsSandbox",
    "FsSandboxViolation",
    "MergeResult",
    "PresetBundle",
    "PresetRole",
    "SchedulerError",
    "ScopeCollisionError",
    "SubagentDAGRun",
    "SubagentDAGSpec",
    "SubagentNodeResult",
    "SubagentNodeStatus",
    "SubagentOrchestrator",
    "SubagentPreset",
    "SubagentRecord",
    "SubagentRegistry",
    "SubagentResult",
    "SubagentRunResult",
    "SubagentRunSpec",
    "SubagentRunner",
    "SubagentScheduler",
    "SubagentSpec",
    "SubagentState",
    "SubagentStatus",
    "VariantOutcome",
    "VariantSpec",
    "VariantStatus",
    "VariantsResult",
    "Worktree",
    "WorktreeError",
    "WorktreeManager",
    "load_presets",
    "run_variants",
    "three_way_merge",
]
