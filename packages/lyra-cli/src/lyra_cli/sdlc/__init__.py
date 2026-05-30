"""SDLC Automation — CI/CD pipeline, quality gates, release management, and git hooks."""

from __future__ import annotations

from .gates import GateCheck, GateResult, GateSeverity, GateStatus, QualityGate
from .hooks import HookEvent, HookResult, HookScript, HooksManager
from .pipeline import Pipeline, PipelineRun, PipelineStatus, StageDefinition, StageResult, StageType
from .release import BumpLevel, ChangelogEntry, ReleaseManager, ReleaseNotes, ReleaseStatus, Version

__all__ = [
    # Pipeline
    "Pipeline",
    "PipelineRun",
    "PipelineStatus",
    "StageDefinition",
    "StageResult",
    "StageType",
    # Gates
    "GateCheck",
    "GateResult",
    "GateSeverity",
    "GateStatus",
    "QualityGate",
    # Release
    "BumpLevel",
    "ChangelogEntry",
    "ReleaseManager",
    "ReleaseNotes",
    "ReleaseStatus",
    "Version",
    # Hooks
    "HookEvent",
    "HookResult",
    "HookScript",
    "HooksManager",
]
