"""SDLC automation — test pipeline, quality gates, changelog, release, hooks."""

from .changelog_generator import ChangeEntry, ChangelogGenerator
from .hooks import HookManager, HookResult, PreCommitHook, PrePushHook
from .quality_gates import Gate, GateResult, GateSeverity, QualityGateRunner
from .release_manager import ReleaseManager, ReleaseResult, VersionBumper
from .test_pipeline import PipelineConfig, PipelineResult, PipelineRunner, StageResult

__all__ = [
    "PipelineConfig",
    "PipelineResult",
    "StageResult",
    "PipelineRunner",
    "Gate",
    "GateResult",
    "GateSeverity",
    "QualityGateRunner",
    "ChangeEntry",
    "ChangelogGenerator",
    "ReleaseManager",
    "ReleaseResult",
    "VersionBumper",
    "HookManager",
    "HookResult",
    "PreCommitHook",
    "PrePushHook",
]
