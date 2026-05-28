"""SDLC automation — test pipeline, quality gates, changelog, release, hooks."""

from .test_pipeline import PipelineConfig, PipelineResult, PipelineRunner, StageResult
from .quality_gates import Gate, GateResult, GateSeverity, QualityGateRunner
from .changelog_generator import ChangeEntry, ChangelogGenerator
from .release_manager import ReleaseManager, ReleaseResult, VersionBumper
from .hooks import HookManager, HookResult, PreCommitHook, PrePushHook

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
