"""CI/CD pipeline automation — stage definitions, execution, and status tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class PipelineStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class StageType(StrEnum):
    BUILD = "build"
    TEST = "test"
    LINT = "lint"
    TYPE_CHECK = "type_check"
    SECURITY_SCAN = "security_scan"
    COVERAGE = "coverage"
    DEPLOY = "deploy"
    INTEGRATION = "integration"
    CUSTOM = "custom"


@dataclass(frozen=True)
class StageResult:
    stage: str
    stage_type: StageType
    status: PipelineStatus
    duration_ms: float
    output: str = ""
    error: str = ""


@dataclass(frozen=True)
class PipelineRun:
    run_id: str
    stages: tuple[StageResult, ...]
    status: PipelineStatus
    started_at: float
    completed_at: float
    total_duration_ms: float


@dataclass
class StageDefinition:
    name: str
    stage_type: StageType
    command: str
    timeout_seconds: float = 300.0
    required: bool = True
    allow_failure: bool = False
    env: dict[str, str] = field(default_factory=dict)


class Pipeline:
    """Define and execute CI/CD pipelines with stage sequencing.

    Usage::

        pipeline = Pipeline("ci")
        pipeline.add_stage(StageDefinition("lint", StageType.LINT, "ruff check ."))
        pipeline.add_stage(StageDefinition("test", StageType.TEST, "pytest"))
        result = pipeline.run()
        print(f"Pipeline {result.status} in {result.total_duration_ms:.0f}ms")
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._stages: list[StageDefinition] = []
        self._run_counter: int = 0

    @property
    def stage_count(self) -> int:
        return len(self._stages)

    def add_stage(self, stage: StageDefinition) -> None:
        self._stages.append(stage)

    def remove_stage(self, name: str) -> None:
        self._stages = [s for s in self._stages if s.name != name]

    def run(self, skip_stages: set[str] | None = None) -> PipelineRun:
        import subprocess

        skip = skip_stages or set()
        self._run_counter += 1
        run_id = f"{self.name}-{self._run_counter:03d}"
        results: list[StageResult] = []
        overall = PipelineStatus.PASSED
        started = time.time()

        for stage in self._stages:
            if stage.name in skip:
                results.append(
                    StageResult(
                        stage=stage.name, stage_type=stage.stage_type,
                        status=PipelineStatus.SKIPPED, duration_ms=0.0,
                    )
                )
                continue

            stage_start = time.time()
            try:
                proc = subprocess.run(
                    stage.command, shell=True, capture_output=True, text=True,
                    timeout=stage.timeout_seconds, env={**__import__("os").environ, **stage.env},
                )
                duration = (time.time() - stage_start) * 1000
                passed = proc.returncode == 0

                if passed:
                    status = PipelineStatus.PASSED
                elif stage.allow_failure:
                    status = PipelineStatus.PASSED
                else:
                    status = PipelineStatus.FAILED
                    if stage.required:
                        overall = PipelineStatus.FAILED

                results.append(
                    StageResult(
                        stage=stage.name, stage_type=stage.stage_type,
                        status=status, duration_ms=duration,
                        output=proc.stdout[:2000], error=proc.stderr[:2000],
                    )
                )

                if status == PipelineStatus.FAILED and stage.required:
                    break

            except subprocess.TimeoutExpired:
                results.append(
                    StageResult(
                        stage=stage.name, stage_type=stage.stage_type,
                        status=PipelineStatus.FAILED, duration_ms=stage.timeout_seconds * 1000,
                        error=f"Timed out after {stage.timeout_seconds}s",
                    )
                )
                if stage.required:
                    overall = PipelineStatus.FAILED
                    break

        completed = time.time()
        return PipelineRun(
            run_id=run_id,
            stages=tuple(results),
            status=overall,
            started_at=started,
            completed_at=completed,
            total_duration_ms=(completed - started) * 1000,
        )
