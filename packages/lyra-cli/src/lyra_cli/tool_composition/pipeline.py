"""Tool Composition Pipeline — chain tools with data flow and error handling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class PipelineStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class StepResult:
    step_name: str
    status: PipelineStepStatus
    output: str
    error: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True)
class PipelineResult:
    pipeline_name: str
    steps: tuple[StepResult, ...]
    final_output: str
    success: bool
    total_duration_ms: float


class ToolPipeline:
    """Compose multiple tool calls into a sequential pipeline with data flow.

    Each step receives the output of the previous step as input.
    Supports error strategies: stop, skip, continue.

    Usage::

        pipeline = ToolPipeline("process-repo")
        pipeline.add_step("list_files", lambda input: ls_cmd(input))
        pipeline.add_step("search_code", lambda input: grep_cmd(input))
        result = pipeline.run(".")
    """

    def __init__(
        self,
        name: str,
        error_strategy: str = "stop",
    ) -> None:
        self.name = name
        self.error_strategy = error_strategy  # stop, skip, continue
        self._steps: list[tuple[str, Callable[[str], str]]] = []

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def add_step(self, name: str, fn: Callable[[str], str]) -> None:
        self._steps.append((name, fn))

    def insert_step(self, index: int, name: str, fn: Callable[[str], str]) -> None:
        self._steps.insert(index, (name, fn))

    def remove_step(self, name: str) -> None:
        self._steps = [(n, fn) for n, fn in self._steps if n != name]

    def run(self, initial_input: str = "") -> PipelineResult:
        import time

        started = time.monotonic()
        results: list[StepResult] = []
        current_input = initial_input
        overall_success = True

        for step_name, step_fn in self._steps:
            step_start = time.monotonic()
            try:
                output = step_fn(current_input)
                results.append(
                    StepResult(
                        step_name=step_name,
                        status=PipelineStepStatus.COMPLETED,
                        output=output,
                        duration_ms=(time.monotonic() - step_start) * 1000,
                    )
                )
                current_input = output
            except Exception as exc:
                results.append(
                    StepResult(
                        step_name=step_name,
                        status=PipelineStepStatus.FAILED,
                        output=current_input,
                        error=str(exc),
                        duration_ms=(time.monotonic() - step_start) * 1000,
                    )
                )
                if self.error_strategy == "stop":
                    overall_success = False
                    break
                elif self.error_strategy == "skip":
                    continue
                else:  # continue
                    pass

        return PipelineResult(
            pipeline_name=self.name,
            steps=tuple(results),
            final_output=current_input,
            success=overall_success,
            total_duration_ms=(time.monotonic() - started) * 1000,
        )


@dataclass(frozen=True)
class PipelineTemplate:
    """A reusable pipeline template with named steps."""

    name: str
    description: str
    step_names: tuple[str, ...]
    error_strategy: str = "stop"
    tags: tuple[str, ...] = ()
