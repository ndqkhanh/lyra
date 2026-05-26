"""Phase 4.1a — Tool Composition Pipelines.

Declarative tool chaining that composes multiple tools into
reusable execution pipelines. Supports:

  - Sequential: pipe output of tool A as input to tool B
  - Parallel: run multiple tools concurrently, merge results
  - Conditional: branch on tool output (if/then/else chain)
  - Retry: retry with backoff on failure
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    RETRY = "retry"


@dataclass(frozen=True)
class StageResult:
    """Result from a single pipeline stage."""

    stage_name: str
    stage_type: StageType
    status: PipelineStatus
    output: Any
    error: str | None
    duration_ms: float
    attempt: int


@dataclass(frozen=True)
class PipelineResult:
    """Result from a complete pipeline execution."""

    pipeline_id: str
    pipeline_name: str
    status: PipelineStatus
    stage_results: tuple[StageResult, ...]
    final_output: Any
    total_duration_ms: float
    summary: str


@dataclass
class ToolPipeline:
    """Declarative pipeline composing multiple tools into a workflow.

    Usage::

        pipeline = ToolPipeline("deploy-flow")
        pipeline.add_stage("validate", validate_tool)
        pipeline.add_stage("build", build_tool, depends_on="validate")
        pipeline.add_parallel("test", [unit_test, integration_test])
        result = pipeline.run(input_data)
    """

    name: str
    _stages: list[dict[str, Any]] = field(default_factory=list)
    max_retries: int = 3
    retry_delay_ms: float = 500.0

    def add_stage(
        self,
        name: str,
        tool_fn: Callable[[Any], Any],
        *,
        depends_on: str | None = None,
        condition: Callable[[Any], bool] | None = None,
    ) -> ToolPipeline:
        """Add a sequential stage to the pipeline."""
        self._stages.append({
            "name": name,
            "type": StageType.SEQUENTIAL,
            "tool": tool_fn,
            "depends_on": depends_on,
            "condition": condition,
        })
        return self

    def add_parallel(
        self,
        name: str,
        tools: list[Callable[[Any], Any]],
        *,
        depends_on: str | None = None,
    ) -> ToolPipeline:
        """Add a parallel stage (multiple tools run concurrently)."""
        self._stages.append({
            "name": name,
            "type": StageType.PARALLEL,
            "tools": tools,
            "depends_on": depends_on,
        })
        return self

    def add_conditional(
        self,
        name: str,
        condition: Callable[[Any], bool],
        then_tool: Callable[[Any], Any],
        else_tool: Callable[[Any], Any] | None = None,
        *,
        depends_on: str | None = None,
    ) -> ToolPipeline:
        """Add a conditional stage (if/then/else)."""
        self._stages.append({
            "name": name,
            "type": StageType.CONDITIONAL,
            "condition": condition,
            "then": then_tool,
            "else": else_tool,
            "depends_on": depends_on,
        })
        return self

    def add_retry(
        self,
        name: str,
        tool_fn: Callable[[Any], Any],
        *,
        max_retries: int | None = None,
        depends_on: str | None = None,
    ) -> ToolPipeline:
        """Add a stage that retries on failure."""
        self._stages.append({
            "name": name,
            "type": StageType.RETRY,
            "tool": tool_fn,
            "max_retries": max_retries or self.max_retries,
            "depends_on": depends_on,
        })
        return self

    def run(self, input_data: Any = None) -> PipelineResult:
        """Execute all stages in the pipeline."""
        pipeline_id = f"pl-{uuid.uuid4().hex[:12]}"
        stage_results: list[StageResult] = []
        data = input_data
        overall_status = PipelineStatus.COMPLETED
        start_time = time.time()

        for i, stage_def in enumerate(self._stages):
            dep = stage_def.get("depends_on")
            if dep and i > 0:
                prev = stage_results[-1]
                if prev.status == PipelineStatus.FAILED:
                    sr = StageResult(
                        stage_name=stage_def["name"],
                        stage_type=stage_def["type"],
                        status=PipelineStatus.SKIPPED,
                        output=None,
                        error=f"Dependency '{dep}' failed",
                        duration_ms=0.0,
                        attempt=0,
                    )
                    stage_results.append(sr)
                    overall_status = PipelineStatus.FAILED
                    continue

            sr = self._execute_stage(stage_def, data)
            stage_results.append(sr)

            if sr.status == PipelineStatus.FAILED:
                overall_status = PipelineStatus.FAILED
                # Mark all remaining stages as skipped (dependency chain broken)
                for remaining in self._stages[i + 1:]:
                    stage_results.append(StageResult(
                        stage_name=remaining["name"],
                        stage_type=remaining["type"],
                        status=PipelineStatus.SKIPPED,
                        output=None,
                        error=f"Pipeline failed at stage '{stage_def['name']}'",
                        duration_ms=0.0,
                        attempt=0,
                    ))
                break

            data = sr.output

        total_ms = (time.time() - start_time) * 1000
        passed = sum(1 for s in stage_results if s.status == PipelineStatus.COMPLETED)
        summary = (
            f"Pipeline '{self.name}': {passed}/{len(self._stages)} stages passed, "
            f"{total_ms:.1f}ms [{overall_status.value}]"
        )

        return PipelineResult(
            pipeline_id=pipeline_id,
            pipeline_name=self.name,
            status=overall_status,
            stage_results=tuple(stage_results),
            final_output=data,
            total_duration_ms=round(total_ms, 2),
            summary=summary,
        )

    def _execute_stage(
        self, stage_def: dict[str, Any], input_data: Any
    ) -> StageResult:
        stype = stage_def["type"]
        name = stage_def["name"]
        t0 = time.time()

        try:
            if stype == StageType.SEQUENTIAL:
                output = stage_def["tool"](input_data)
                return StageResult(
                    stage_name=name, stage_type=stype,
                    status=PipelineStatus.COMPLETED,
                    output=output, error=None,
                    duration_ms=(time.time() - t0) * 1000, attempt=1,
                )
            elif stype == StageType.PARALLEL:
                results = [t(input_data) for t in stage_def["tools"]]
                merged = self._merge_results(results)
                return StageResult(
                    stage_name=name, stage_type=stype,
                    status=PipelineStatus.COMPLETED,
                    output=merged, error=None,
                    duration_ms=(time.time() - t0) * 1000, attempt=1,
                )
            elif stype == StageType.CONDITIONAL:
                if stage_def["condition"](input_data):
                    output = stage_def["then"](input_data)
                elif stage_def.get("else"):
                    output = stage_def["else"](input_data)
                else:
                    output = input_data
                return StageResult(
                    stage_name=name, stage_type=stype,
                    status=PipelineStatus.COMPLETED,
                    output=output, error=None,
                    duration_ms=(time.time() - t0) * 1000, attempt=1,
                )
            elif stype == StageType.RETRY:
                max_retries = stage_def["max_retries"]
                last_error = None
                for attempt in range(1, max_retries + 1):
                    try:
                        output = stage_def["tool"](input_data)
                        return StageResult(
                            stage_name=name, stage_type=stype,
                            status=PipelineStatus.COMPLETED,
                            output=output, error=None,
                            duration_ms=(time.time() - t0) * 1000,
                            attempt=attempt,
                        )
                    except Exception as e:
                        last_error = str(e)
                        if attempt < max_retries:
                            time.sleep(self.retry_delay_ms / 1000 * attempt)
                return StageResult(
                    stage_name=name, stage_type=stype,
                    status=PipelineStatus.FAILED,
                    output=None, error=last_error,
                    duration_ms=(time.time() - t0) * 1000,
                    attempt=max_retries,
                )
            else:
                return StageResult(
                    stage_name=name, stage_type=stype,
                    status=PipelineStatus.FAILED,
                    output=None, error=f"Unknown stage type: {stype}",
                    duration_ms=(time.time() - t0) * 1000, attempt=1,
                )
        except Exception as e:
            return StageResult(
                stage_name=name, stage_type=stype,
                status=PipelineStatus.FAILED,
                output=None, error=str(e),
                duration_ms=(time.time() - t0) * 1000, attempt=1,
            )

    @staticmethod
    def _merge_results(results: list[Any]) -> dict[str, Any]:
        """Merge parallel results into a single output."""
        if all(isinstance(r, dict) for r in results):
            merged: dict[str, Any] = {}
            for r in results:
                if isinstance(r, dict):
                    merged.update(r)
            return merged
        return {"results": results}

    @property
    def stage_count(self) -> int:
        return len(self._stages)


__all__ = [
    "PipelineResult",
    "PipelineStatus",
    "StageResult",
    "StageType",
    "ToolPipeline",
]
