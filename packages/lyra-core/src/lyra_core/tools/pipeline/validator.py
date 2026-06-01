"""Pipeline validator for checking pipeline correctness before execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lyra_core.tools.pipeline.builder import Pipeline, PipelineStep, StepType


class ValidationError(Exception):
    """Raised when pipeline validation fails."""

    pass


@dataclass(frozen=True)
class ValidationResult:
    """Result of pipeline validation."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def has_errors(self) -> bool:
        """Check if validation found errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if validation found warnings."""
        return len(self.warnings) > 0


class PipelineValidator:
    """Validates pipeline definitions for correctness.

    Checks:
    - Variable references are valid
    - Tool names are not empty
    - Conditional steps have required fields
    - Parallel steps have at least one tool
    - No circular dependencies
    """

    def __init__(self, tool_registry: dict[str, Any] | None = None) -> None:
        """Initialize validator.

        Args:
            tool_registry: Optional registry of available tools for validation
        """
        self.tool_registry = tool_registry or {}

    def validate(self, pipeline: Pipeline) -> ValidationResult:
        """Validate a pipeline.

        Args:
            pipeline: Pipeline to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check pipeline name
        if not pipeline.name or not pipeline.name.strip():
            errors.append("Pipeline name cannot be empty")

        # Check steps
        if len(pipeline.steps) == 0:
            warnings.append("Pipeline has no steps")

        # Validate each step
        available_vars = {"input"}
        for idx, step in enumerate(pipeline.steps):
            step_errors, step_warnings, new_vars = self._validate_step(
                step,
                idx,
                available_vars,
            )
            errors.extend(step_errors)
            warnings.extend(step_warnings)
            available_vars.update(new_vars)

        # Validate error handler
        if pipeline.error_handler:
            handler_errors, handler_warnings = self._validate_tool_step(
                pipeline.error_handler,
                "error_handler",
                available_vars | {"error"},
            )
            errors.extend(handler_errors)
            warnings.extend(handler_warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def validate_or_raise(self, pipeline: Pipeline) -> None:
        """Validate a pipeline and raise ValidationError if invalid.

        Args:
            pipeline: Pipeline to validate

        Raises:
            ValidationError: If pipeline is invalid
        """
        result = self.validate(pipeline)
        if not result.valid:
            error_msg = "\n".join(result.errors)
            raise ValidationError(f"Pipeline validation failed:\n{error_msg}")

    def _validate_step(
        self,
        step: PipelineStep,
        step_index: int,
        available_vars: set[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Validate a single step.

        Args:
            step: Step to validate
            step_index: Index of the step
            available_vars: Set of available variable names

        Returns:
            Tuple of (errors, warnings, new_variables)
        """
        errors: list[str] = []
        warnings: list[str] = []
        new_vars: set[str] = set()

        step_prefix = f"Step {step_index}"

        if step.step_type == StepType.SEQUENTIAL:
            if step.tool_step is None:
                errors.append(f"{step_prefix}: Sequential step missing tool_step")
            else:
                tool_errors, tool_warnings = self._validate_tool_step(
                    step.tool_step,
                    step_prefix,
                    available_vars,
                )
                errors.extend(tool_errors)
                warnings.extend(tool_warnings)
                # Add both the base tool name and numbered version
                new_vars.add(step.tool_step.tool_name)
                new_vars.add(f"{step.tool_step.tool_name}_{step_index + 1}")

            if step.retry_count < 0:
                errors.append(f"{step_prefix}: retry_count cannot be negative")

            if step.timeout_seconds is not None and step.timeout_seconds <= 0:
                errors.append(f"{step_prefix}: timeout_seconds must be positive")

        elif step.step_type == StepType.PARALLEL:
            if not step.parallel_steps:
                errors.append(f"{step_prefix}: Parallel step has no tools")
            else:
                for tool_step in step.parallel_steps:
                    tool_errors, tool_warnings = self._validate_tool_step(
                        tool_step,
                        f"{step_prefix}.{tool_step.tool_name}",
                        available_vars,
                    )
                    errors.extend(tool_errors)
                    warnings.extend(tool_warnings)
                    new_vars.add(tool_step.tool_name)

        elif step.step_type == StepType.CONDITIONAL:
            if not step.condition:
                errors.append(f"{step_prefix}: Conditional step missing condition")
            else:
                cond_errors = self._validate_condition(
                    step.condition,
                    available_vars,
                )
                errors.extend([f"{step_prefix}: {e}" for e in cond_errors])

            if step.when_true is None:
                errors.append(f"{step_prefix}: Conditional step missing when_true")
            else:
                tool_errors, tool_warnings = self._validate_tool_step(
                    step.when_true,
                    f"{step_prefix}.then",
                    available_vars,
                )
                errors.extend(tool_errors)
                warnings.extend(tool_warnings)
                new_vars.add(step.when_true.tool_name)

            if step.when_false:
                tool_errors, tool_warnings = self._validate_tool_step(
                    step.when_false,
                    f"{step_prefix}.else",
                    available_vars,
                )
                errors.extend(tool_errors)
                warnings.extend(tool_warnings)
                new_vars.add(step.when_false.tool_name)

        return errors, warnings, new_vars

    def _validate_tool_step(
        self,
        tool_step: Any,
        context: str,
        available_vars: set[str],
    ) -> tuple[list[str], list[str]]:
        """Validate a tool step.

        Args:
            tool_step: Tool step to validate
            context: Context string for error messages
            available_vars: Set of available variable names

        Returns:
            Tuple of (errors, warnings)
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not tool_step.tool_name or not tool_step.tool_name.strip():
            errors.append(f"{context}: Tool name cannot be empty")

        # Check if tool exists in registry
        if self.tool_registry and tool_step.tool_name not in self.tool_registry:
            warnings.append(
                f"{context}: Tool '{tool_step.tool_name}' not found in registry"
            )

        # Validate variable references in parameters
        param_errors = self._validate_params(
            tool_step.params,
            available_vars,
            context,
        )
        errors.extend(param_errors)

        return errors, warnings

    def _validate_params(
        self,
        params: dict[str, Any],
        available_vars: set[str],
        context: str,
    ) -> list[str]:
        """Validate parameters for variable references.

        Args:
            params: Parameters to validate
            available_vars: Set of available variable names
            context: Context string for error messages

        Returns:
            List of error messages
        """
        errors: list[str] = []

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                var_errors = self._validate_variable_reference(
                    value,
                    available_vars,
                )
                errors.extend([f"{context}.{key}: {e}" for e in var_errors])
            elif isinstance(value, dict):
                errors.extend(
                    self._validate_params(value, available_vars, f"{context}.{key}")
                )
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, str) and item.startswith("$"):
                        var_errors = self._validate_variable_reference(
                            item,
                            available_vars,
                        )
                        errors.extend(
                            [f"{context}.{key}[{idx}]: {e}" for e in var_errors]
                        )

        return errors

    def _validate_variable_reference(
        self,
        var_ref: str,
        available_vars: set[str],
    ) -> list[str]:
        """Validate a variable reference.

        Args:
            var_ref: Variable reference (e.g., "$input.file_path")
            available_vars: Set of available variable names

        Returns:
            List of error messages
        """
        errors: list[str] = []

        if not var_ref.startswith("$"):
            return errors

        # Remove $ prefix
        path = var_ref[1:]
        if not path:
            errors.append("Empty variable reference")
            return errors

        # Get base variable name
        base_var = path.split(".", 1)[0]

        if base_var not in available_vars:
            errors.append(
                f"Variable '{base_var}' not available. "
                f"Available: {', '.join(sorted(available_vars))}"
            )

        return errors

    def _validate_condition(
        self,
        condition: str,
        available_vars: set[str],
    ) -> list[str]:
        """Validate a condition expression.

        Args:
            condition: Condition string
            available_vars: Set of available variable names

        Returns:
            List of error messages
        """
        errors: list[str] = []

        if not condition or not condition.strip():
            errors.append("Empty condition")
            return errors

        # Extract variable references from condition
        import re

        var_pattern = r"\$[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*"
        var_refs = re.findall(var_pattern, condition)

        for var_ref in var_refs:
            var_errors = self._validate_variable_reference(var_ref, available_vars)
            errors.extend(var_errors)

        return errors


__all__ = [
    "PipelineValidator",
    "ValidationError",
    "ValidationResult",
]
