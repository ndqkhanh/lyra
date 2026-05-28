"""Automated test pipeline with stage-based execution and reporting."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class StageResult:
    stage_name: str
    status: StageStatus
    duration_ms: float
    details: str = ""
    test_count: int = 0
    passed_count: int = 0
    failed_count: int = 0


@dataclass(frozen=True)
class PipelineResult:
    stages: tuple[StageResult, ...]
    total_duration_ms: float
    overall_status: StageStatus

    @property
    def total_tests(self) -> int:
        return sum(s.test_count for s in self.stages)

    @property
    def total_passed(self) -> int:
        return sum(s.passed_count for s in self.stages)

    @property
    def total_failed(self) -> int:
        return sum(s.failed_count for s in self.stages)


@dataclass
class PipelineConfig:
    stages: tuple[str, ...] = ("unit", "integration", "e2e")
    fail_fast: bool = False
    timeout_per_stage_ms: float = 300_000
    parallel_stages: bool = False


@dataclass
class PipelineRunner:
    """Multi-stage automated test pipeline."""

    config: PipelineConfig = field(default_factory=PipelineConfig)
    _handlers: dict[str, callable] = field(default_factory=dict)

    def register_stage(self, name: str, handler: callable) -> None:
        self._handlers[name] = handler

    def run(self) -> PipelineResult:
        stage_results: list[StageResult] = []
        start = time.time()

        for stage_name in self.config.stages:
            stage_start = time.time()
            handler = self._handlers.get(stage_name)

            if handler is None:
                stage_results.append(StageResult(
                    stage_name=stage_name,
                    status=StageStatus.SKIPPED,
                    duration_ms=0.0,
                    details="No handler registered",
                ))
                continue

            try:
                result = handler()
                duration = (time.time() - stage_start) * 1000

                if isinstance(result, dict):
                    stage_results.append(StageResult(
                        stage_name=stage_name,
                        status=StageStatus(result.get("status", "passed")),
                        duration_ms=duration,
                        test_count=result.get("total", 0),
                        passed_count=result.get("passed", 0),
                        failed_count=result.get("failed", 0),
                    ))
                else:
                    stage_results.append(StageResult(
                        stage_name=stage_name,
                        status=StageStatus.PASSED,
                        duration_ms=duration,
                    ))

                if self.config.fail_fast:
                    latest = stage_results[-1]
                    if latest.status == StageStatus.FAILED:
                        break
            except Exception as e:
                duration = (time.time() - stage_start) * 1000
                stage_results.append(StageResult(
                    stage_name=stage_name,
                    status=StageStatus.FAILED,
                    duration_ms=duration,
                    details=str(e),
                ))
                if self.config.fail_fast:
                    break

        total_duration = (time.time() - start) * 1000
        overall = self._compute_overall(stage_results)

        return PipelineResult(
            stages=tuple(stage_results),
            total_duration_ms=total_duration,
            overall_status=overall,
        )

    def _compute_overall(self, results: list[StageResult]) -> StageStatus:
        for r in results:
            if r.status == StageStatus.FAILED:
                return StageStatus.FAILED
        if all(r.status == StageStatus.SKIPPED for r in results):
            return StageStatus.SKIPPED
        return StageStatus.PASSED
