"""Pipeline executor with variable interpolation and async support."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from lyra_core.tools.pipeline.builder import Pipeline, PipelineStep, StepType, ToolStep


class ExecutionStatus(Enum):
    """Status of pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class StepResult:
    """Result from executing a single step."""

    step_index: int
    tool_name: str
    status: ExecutionStatus
    output: Any
    error: str | None
    duration_ms: float
    attempt: int


@dataclass(frozen=True)
class PipelineResult:
    """Result from executing a complete pipeline."""

    pipeline_name: str
    status: ExecutionStatus
    step_results: tuple[StepResult, ...]
    final_output: Any
    total_duration_ms: float
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if pipeline executed successfully."""
        return self.status == ExecutionStatus.COMPLETED

    @property
    def failed_steps(self) -> list[StepResult]:
        """Get list of failed steps."""
        return [
            r for r in self.step_results if r.status == ExecutionStatus.FAILED
        ]


@dataclass
class PipelineContext:
    """Execution context for a pipeline.

    Stores input data and results from each step for variable interpolation.
    """

    input_data: dict[str, Any] = field(default_factory=dict)
    step_outputs: dict[str, Any] = field(default_factory=dict)
    _step_counter: int = 0

    def set_step_output(self, step_name: str, output: Any) -> None:
        """Store output from a step.

        Args:
            step_name: Name of the step
            output: Output data from the step
        """
        self.step_outputs[step_name] = output

    def get_variable(self, var_path: str) -> Any:
        """Resolve a variable path like $input.file_path or $read_file.content.

        Args:
            var_path: Variable path to resolve

        Returns:
            Resolved value

        Raises:
            KeyError: If variable path cannot be resolved
        """
        if not var_path.startswith("$"):
            return var_path

        # Remove $ prefix
        path = var_path[1:]
        parts = path.split(".", 1)

        if parts[0] == "input":
            if len(parts) == 1:
                return self.input_data
            return self._get_nested(self.input_data, parts[1])

        # Step output reference
        if parts[0] in self.step_outputs:
            if len(parts) == 1:
                return self.step_outputs[parts[0]]
            return self._get_nested(self.step_outputs[parts[0]], parts[1])

        raise KeyError(f"Variable not found: {var_path}")

    def interpolate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Interpolate variables in parameters.

        Args:
            params: Parameters with potential variable references

        Returns:
            Parameters with variables resolved
        """
        result = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                try:
                    result[key] = self.get_variable(value)
                except KeyError:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.interpolate_params(value)
            elif isinstance(value, list):
                result[key] = [
                    self.get_variable(v) if isinstance(v, str) and v.startswith("$") else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    def next_step_name(self, tool_name: str) -> str:
        """Generate a unique step name.

        Args:
            tool_name: Base tool name

        Returns:
            Unique step name
        """
        self._step_counter += 1
        return f"{tool_name}_{self._step_counter}"

    @staticmethod
    def _get_nested(data: Any, path: str) -> Any:
        """Get nested value from data using dot notation.

        Args:
            data: Data structure to traverse
            path: Dot-separated path

        Returns:
            Value at the path

        Raises:
            KeyError: If path cannot be resolved
        """
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    raise KeyError(f"Key not found: {part}")
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Cannot access: {part}")

        return current


class PipelineExecutor:
    """Executes pipelines with tool registry and async support.

    Example:
        >>> executor = PipelineExecutor(tool_registry)
        >>> result = executor.execute(pipeline, {"file_path": "src/app.py"})
    """

    def __init__(
        self,
        tool_registry: dict[str, Callable[..., Any]],
        default_timeout: float = 30.0,
    ) -> None:
        """Initialize executor.

        Args:
            tool_registry: Mapping of tool names to callable functions
            default_timeout: Default timeout in seconds for steps
        """
        self.tool_registry = tool_registry
        self.default_timeout = default_timeout

    def execute(
        self,
        pipeline: Pipeline,
        input_data: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """Execute a pipeline synchronously.

        Args:
            pipeline: Pipeline to execute
            input_data: Input data for the pipeline

        Returns:
            PipelineResult with execution details
        """
        return asyncio.run(self.execute_async(pipeline, input_data))

    async def execute_async(
        self,
        pipeline: Pipeline,
        input_data: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """Execute a pipeline asynchronously.

        Args:
            pipeline: Pipeline to execute
            input_data: Input data for the pipeline

        Returns:
            PipelineResult with execution details
        """
        context = PipelineContext(input_data=input_data or {})
        step_results: list[StepResult] = []
        start_time = time.time()
        overall_status = ExecutionStatus.COMPLETED
        final_output: Any = None
        error_message: str | None = None

        try:
            for idx, step in enumerate(pipeline.steps):
                result = await self._execute_step(step, context, idx)
                step_results.append(result)

                if result.status == ExecutionStatus.FAILED:
                    overall_status = ExecutionStatus.FAILED
                    error_message = result.error

                    # Execute error handler if present
                    if pipeline.error_handler:
                        await self._execute_error_handler(
                            pipeline.error_handler,
                            context,
                            result.error,
                        )

                    # Skip remaining steps
                    for remaining_idx in range(idx + 1, len(pipeline.steps)):
                        step_results.append(
                            StepResult(
                                step_index=remaining_idx,
                                tool_name="skipped",
                                status=ExecutionStatus.SKIPPED,
                                output=None,
                                error="Previous step failed",
                                duration_ms=0.0,
                                attempt=0,
                            )
                        )
                    break

                final_output = result.output

        except Exception as e:
            overall_status = ExecutionStatus.FAILED
            error_message = str(e)

            # Execute error handler if present
            if pipeline.error_handler:
                await self._execute_error_handler(
                    pipeline.error_handler,
                    context,
                    str(e),
                )

        total_duration = (time.time() - start_time) * 1000

        return PipelineResult(
            pipeline_name=pipeline.name,
            status=overall_status,
            step_results=tuple(step_results),
            final_output=final_output,
            total_duration_ms=round(total_duration, 2),
            error=error_message,
        )

    async def _execute_step(
        self,
        step: PipelineStep,
        context: PipelineContext,
        step_index: int,
    ) -> StepResult:
        """Execute a single pipeline step.

        Args:
            step: Step to execute
            context: Execution context
            step_index: Index of the step

        Returns:
            StepResult with execution details
        """
        start_time = time.time()

        try:
            if step.step_type == StepType.SEQUENTIAL:
                if step.tool_step is None:
                    raise ValueError("Sequential step missing tool_step")

                output = await self._execute_tool_step(
                    step.tool_step,
                    context,
                    step.retry_count,
                    step.timeout_seconds or self.default_timeout,
                )

                duration = (time.time() - start_time) * 1000
                return StepResult(
                    step_index=step_index,
                    tool_name=step.tool_step.tool_name,
                    status=ExecutionStatus.COMPLETED,
                    output=output,
                    error=None,
                    duration_ms=round(duration, 2),
                    attempt=1,
                )

            elif step.step_type == StepType.PARALLEL:
                outputs = await self._execute_parallel(
                    step.parallel_steps,
                    context,
                    step.timeout_seconds or self.default_timeout,
                )

                duration = (time.time() - start_time) * 1000
                return StepResult(
                    step_index=step_index,
                    tool_name="parallel",
                    status=ExecutionStatus.COMPLETED,
                    output=outputs,
                    error=None,
                    duration_ms=round(duration, 2),
                    attempt=1,
                )

            elif step.step_type == StepType.CONDITIONAL:
                if step.condition is None:
                    raise ValueError("Conditional step missing condition")

                condition_result = self._evaluate_condition(step.condition, context)
                tool_step = step.when_true if condition_result else step.when_false

                if tool_step is None:
                    duration = (time.time() - start_time) * 1000
                    return StepResult(
                        step_index=step_index,
                        tool_name="conditional",
                        status=ExecutionStatus.SKIPPED,
                        output=None,
                        error=None,
                        duration_ms=round(duration, 2),
                        attempt=0,
                    )

                output = await self._execute_tool_step(
                    tool_step,
                    context,
                    0,
                    step.timeout_seconds or self.default_timeout,
                )

                duration = (time.time() - start_time) * 1000
                return StepResult(
                    step_index=step_index,
                    tool_name=tool_step.tool_name,
                    status=ExecutionStatus.COMPLETED,
                    output=output,
                    error=None,
                    duration_ms=round(duration, 2),
                    attempt=1,
                )

            else:
                raise ValueError(f"Unknown step type: {step.step_type}")

        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            return StepResult(
                step_index=step_index,
                tool_name=step.tool_step.tool_name if step.tool_step else "unknown",
                status=ExecutionStatus.TIMEOUT,
                output=None,
                error="Step execution timed out",
                duration_ms=round(duration, 2),
                attempt=1,
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return StepResult(
                step_index=step_index,
                tool_name=step.tool_step.tool_name if step.tool_step else "unknown",
                status=ExecutionStatus.FAILED,
                output=None,
                error=str(e),
                duration_ms=round(duration, 2),
                attempt=1,
            )

    async def _execute_tool_step(
        self,
        tool_step: ToolStep,
        context: PipelineContext,
        retry_count: int,
        timeout: float,
    ) -> Any:
        """Execute a single tool step with retry logic.

        Args:
            tool_step: Tool step to execute
            context: Execution context
            retry_count: Number of retries
            timeout: Timeout in seconds

        Returns:
            Tool output

        Raises:
            Exception: If tool execution fails after all retries
        """
        tool_fn = self.tool_registry.get(tool_step.tool_name)
        if tool_fn is None:
            raise ValueError(f"Tool not found: {tool_step.tool_name}")

        params = context.interpolate_params(tool_step.params)
        last_error: Exception | None = None

        for attempt in range(retry_count + 1):
            try:
                # Execute with timeout
                output = await asyncio.wait_for(
                    self._call_tool(tool_fn, params),
                    timeout=timeout,
                )

                # Store output in context
                step_name = context.next_step_name(tool_step.tool_name)
                context.set_step_output(step_name, output)

                return output

            except Exception as e:
                last_error = e
                if attempt < retry_count:
                    await asyncio.sleep(0.5 * (attempt + 1))

        if last_error:
            raise last_error
        raise RuntimeError("Tool execution failed")

    async def _execute_parallel(
        self,
        steps: list[ToolStep],
        context: PipelineContext,
        timeout: float,
    ) -> dict[str, Any]:
        """Execute multiple steps in parallel.

        Args:
            steps: List of tool steps to execute
            context: Execution context
            timeout: Timeout in seconds

        Returns:
            Dictionary mapping step names to outputs
        """
        tasks = [
            self._execute_tool_step(step, context, 0, timeout)
            for step in steps
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs = {}
        for step, result in zip(steps, results):
            if isinstance(result, Exception):
                raise result
            outputs[step.tool_name] = result

        return outputs

    async def _execute_error_handler(
        self,
        error_handler: ToolStep,
        context: PipelineContext,
        error: str | None,
    ) -> None:
        """Execute error handler step.

        Args:
            error_handler: Error handler tool step
            context: Execution context
            error: Error message
        """
        try:
            # Add error to context
            context.set_step_output("error", {"message": error})

            await self._execute_tool_step(
                error_handler,
                context,
                0,
                self.default_timeout,
            )
        except Exception:
            # Silently ignore error handler failures
            pass

    @staticmethod
    async def _call_tool(tool_fn: Callable[..., Any], params: dict[str, Any]) -> Any:
        """Call a tool function, handling both sync and async functions.

        Args:
            tool_fn: Tool function to call
            params: Parameters to pass

        Returns:
            Tool output
        """
        if asyncio.iscoroutinefunction(tool_fn):
            return await tool_fn(**params)
        return tool_fn(**params)

    @staticmethod
    def _evaluate_condition(condition: str, context: PipelineContext) -> bool:
        """Evaluate a condition expression.

        Args:
            condition: Condition string (e.g., "$ast_analyze.has_errors")
            context: Execution context

        Returns:
            Boolean result
        """
        # Simple condition evaluation
        # Supports: $var, $var.field, $var == value, $var != value
        condition = condition.strip()

        # Check for comparison operators
        if " == " in condition:
            left, right = condition.split(" == ", 1)
            left_val = context.get_variable(left.strip())
            right_val = right.strip().strip('"\'')
            return str(left_val) == right_val

        if " != " in condition:
            left, right = condition.split(" != ", 1)
            left_val = context.get_variable(left.strip())
            right_val = right.strip().strip('"\'')
            return str(left_val) != right_val

        # Simple truthiness check
        try:
            value = context.get_variable(condition)
            return bool(value)
        except KeyError:
            return False


__all__ = [
    "ExecutionStatus",
    "PipelineContext",
    "PipelineExecutor",
    "PipelineResult",
    "StepResult",
]
