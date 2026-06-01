"""Pipeline builder with fluent API for declarative tool composition."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepType(Enum):
    """Type of pipeline step."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ERROR_HANDLER = "error_handler"


@dataclass(frozen=True)
class ToolStep:
    """A single step in a tool pipeline.

    Args:
        tool_name: Name of the tool to execute
        params: Parameters to pass to the tool (supports variable interpolation)
        step_id: Optional unique identifier for this step
    """

    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)
    step_id: str | None = None

    def with_params(self, **kwargs: Any) -> ToolStep:
        """Create a new step with additional parameters."""
        new_params = {**self.params, **kwargs}
        return ToolStep(
            tool_name=self.tool_name,
            params=new_params,
            step_id=self.step_id,
        )


@dataclass
class PipelineStep:
    """Internal representation of a pipeline step."""

    step_type: StepType
    tool_step: ToolStep | None = None
    parallel_steps: list[ToolStep] = field(default_factory=list)
    condition: str | None = None
    when_true: ToolStep | None = None
    when_false: ToolStep | None = None
    retry_count: int = 0
    timeout_seconds: float | None = None


class PipelineBuilder:
    """Fluent API builder for creating tool pipelines.

    Example:
        >>> pipeline = PipelineBuilder("code-review") \\
        ...     .then("read_file", file="$input.file_path") \\
        ...     .then("ast_analyze", source="$read_file.content") \\
        ...     .parallel(
        ...         ToolStep("generate_tests", {"source": "$read_file.content"}),
        ...         ToolStep("generate_docs", {"source": "$read_file.content"}),
        ...     ) \\
        ...     .on_error("rollback_file", path="$input.file_path")
    """

    def __init__(self, name: str) -> None:
        """Initialize a new pipeline builder.

        Args:
            name: Name of the pipeline
        """
        self.name = name
        self._steps: list[PipelineStep] = []
        self._error_handler: ToolStep | None = None
        self._metadata: dict[str, Any] = {}

    def then(self, tool_name: str, **params: Any) -> PipelineBuilder:
        """Add a sequential step to the pipeline.

        Args:
            tool_name: Name of the tool to execute
            **params: Parameters to pass to the tool (supports $variable interpolation)

        Returns:
            Self for method chaining
        """
        step = PipelineStep(
            step_type=StepType.SEQUENTIAL,
            tool_step=ToolStep(tool_name=tool_name, params=params),
        )
        self._steps.append(step)
        return self

    def parallel(self, *steps: ToolStep) -> PipelineBuilder:
        """Add parallel steps that execute concurrently.

        Args:
            *steps: ToolStep instances to execute in parallel

        Returns:
            Self for method chaining
        """
        step = PipelineStep(
            step_type=StepType.PARALLEL,
            parallel_steps=list(steps),
        )
        self._steps.append(step)
        return self

    def when(
        self,
        condition: str,
        then_step: ToolStep,
        else_step: ToolStep | None = None,
    ) -> PipelineBuilder:
        """Add a conditional step.

        Args:
            condition: Condition expression (e.g., "$ast_analyze.has_errors")
            then_step: Step to execute if condition is true
            else_step: Optional step to execute if condition is false

        Returns:
            Self for method chaining
        """
        step = PipelineStep(
            step_type=StepType.CONDITIONAL,
            condition=condition,
            when_true=then_step,
            when_false=else_step,
        )
        self._steps.append(step)
        return self

    def retry(
        self,
        tool_name: str,
        count: int = 3,
        **params: Any,
    ) -> PipelineBuilder:
        """Add a step with retry logic.

        Args:
            tool_name: Name of the tool to execute
            count: Number of retry attempts
            **params: Parameters to pass to the tool

        Returns:
            Self for method chaining
        """
        step = PipelineStep(
            step_type=StepType.SEQUENTIAL,
            tool_step=ToolStep(tool_name=tool_name, params=params),
            retry_count=count,
        )
        self._steps.append(step)
        return self

    def timeout(self, seconds: float) -> PipelineBuilder:
        """Set timeout for the last added step.

        Args:
            seconds: Timeout in seconds

        Returns:
            Self for method chaining
        """
        if self._steps:
            self._steps[-1].timeout_seconds = seconds
        return self

    def on_error(self, tool_name: str, **params: Any) -> PipelineBuilder:
        """Set error handler for the pipeline.

        Args:
            tool_name: Name of the tool to execute on error
            **params: Parameters to pass to the error handler

        Returns:
            Self for method chaining
        """
        self._error_handler = ToolStep(tool_name=tool_name, params=params)
        return self

    def with_metadata(self, **metadata: Any) -> PipelineBuilder:
        """Add metadata to the pipeline.

        Args:
            **metadata: Key-value pairs of metadata

        Returns:
            Self for method chaining
        """
        self._metadata.update(metadata)
        return self

    def build(self) -> Pipeline:
        """Build the final pipeline.

        Returns:
            Immutable Pipeline instance
        """
        return Pipeline(
            name=self.name,
            steps=tuple(self._steps),
            error_handler=self._error_handler,
            metadata=self._metadata.copy(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize pipeline to dictionary.

        Returns:
            Dictionary representation of the pipeline
        """
        return {
            "name": self.name,
            "steps": [self._step_to_dict(s) for s in self._steps],
            "error_handler": self._tool_step_to_dict(self._error_handler)
            if self._error_handler
            else None,
            "metadata": self._metadata,
        }

    def to_json(self) -> str:
        """Serialize pipeline to JSON string.

        Returns:
            JSON representation of the pipeline
        """
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PipelineBuilder:
        """Deserialize pipeline from dictionary.

        Args:
            data: Dictionary representation of a pipeline

        Returns:
            PipelineBuilder instance
        """
        builder = PipelineBuilder(data["name"])
        builder._metadata = data.get("metadata", {})

        for step_data in data.get("steps", []):
            step_type = StepType(step_data["step_type"])

            if step_type == StepType.SEQUENTIAL:
                tool_step = step_data["tool_step"]
                step = PipelineStep(
                    step_type=step_type,
                    tool_step=ToolStep(
                        tool_name=tool_step["tool_name"],
                        params=tool_step.get("params", {}),
                        step_id=tool_step.get("step_id"),
                    ),
                    retry_count=step_data.get("retry_count", 0),
                    timeout_seconds=step_data.get("timeout_seconds"),
                )
            elif step_type == StepType.PARALLEL:
                parallel_steps = [
                    ToolStep(
                        tool_name=ts["tool_name"],
                        params=ts.get("params", {}),
                        step_id=ts.get("step_id"),
                    )
                    for ts in step_data["parallel_steps"]
                ]
                step = PipelineStep(
                    step_type=step_type,
                    parallel_steps=parallel_steps,
                )
            elif step_type == StepType.CONDITIONAL:
                when_true_data = step_data["when_true"]
                when_true = ToolStep(
                    tool_name=when_true_data["tool_name"],
                    params=when_true_data.get("params", {}),
                    step_id=when_true_data.get("step_id"),
                )
                when_false = None
                if step_data.get("when_false"):
                    when_false_data = step_data["when_false"]
                    when_false = ToolStep(
                        tool_name=when_false_data["tool_name"],
                        params=when_false_data.get("params", {}),
                        step_id=when_false_data.get("step_id"),
                    )
                step = PipelineStep(
                    step_type=step_type,
                    condition=step_data["condition"],
                    when_true=when_true,
                    when_false=when_false,
                )
            else:
                continue

            builder._steps.append(step)

        if data.get("error_handler"):
            eh = data["error_handler"]
            builder._error_handler = ToolStep(
                tool_name=eh["tool_name"],
                params=eh.get("params", {}),
                step_id=eh.get("step_id"),
            )

        return builder

    @staticmethod
    def from_json(json_str: str) -> PipelineBuilder:
        """Deserialize pipeline from JSON string.

        Args:
            json_str: JSON representation of a pipeline

        Returns:
            PipelineBuilder instance
        """
        data = json.loads(json_str)
        return PipelineBuilder.from_dict(data)

    @staticmethod
    def _step_to_dict(step: PipelineStep) -> dict[str, Any]:
        """Convert PipelineStep to dictionary."""
        result: dict[str, Any] = {
            "step_type": step.step_type.value,
        }

        if step.tool_step:
            result["tool_step"] = PipelineBuilder._tool_step_to_dict(step.tool_step)

        if step.parallel_steps:
            result["parallel_steps"] = [
                PipelineBuilder._tool_step_to_dict(ts) for ts in step.parallel_steps
            ]

        if step.condition:
            result["condition"] = step.condition

        if step.when_true:
            result["when_true"] = PipelineBuilder._tool_step_to_dict(step.when_true)

        if step.when_false:
            result["when_false"] = PipelineBuilder._tool_step_to_dict(step.when_false)

        if step.retry_count > 0:
            result["retry_count"] = step.retry_count

        if step.timeout_seconds is not None:
            result["timeout_seconds"] = step.timeout_seconds

        return result

    @staticmethod
    def _tool_step_to_dict(tool_step: ToolStep) -> dict[str, Any]:
        """Convert ToolStep to dictionary."""
        return {
            "tool_name": tool_step.tool_name,
            "params": tool_step.params,
            "step_id": tool_step.step_id,
        }


@dataclass(frozen=True)
class Pipeline:
    """Immutable pipeline definition.

    This is the result of calling build() on a PipelineBuilder.
    """

    name: str
    steps: tuple[PipelineStep, ...]
    error_handler: ToolStep | None
    metadata: dict[str, Any]

    @property
    def step_count(self) -> int:
        """Get the total number of steps in the pipeline."""
        return len(self.steps)


__all__ = [
    "Pipeline",
    "PipelineBuilder",
    "PipelineStep",
    "StepType",
    "ToolStep",
]
