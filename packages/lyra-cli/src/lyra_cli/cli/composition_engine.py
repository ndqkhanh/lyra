"""Composition Engine for executing multi-stage skill workflows.

Enables skills to invoke other skills in sequence, passing data between stages.
Supports variable interpolation and context management.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class StageResult:
    """Result from executing a composition stage."""

    name: str
    output: Any
    success: bool
    error: Optional[str] = None


class CompositionEngine:
    """Execute multi-stage skill compositions."""

    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
        self.context: dict[str, Any] = {}

    def execute(self, composition: dict, user_input: str) -> StageResult:
        """Execute a skill composition.

        Args:
            composition: Composition definition from skill JSON
            user_input: User-provided arguments

        Returns:
            Final stage result
        """
        self.context = {"input": user_input}
        stages = composition.get("stages", [])

        for stage in stages:
            result = self._execute_stage(stage)
            if not result.success:
                return result

            # Store stage output in context
            output_var = stage.get("output")
            if output_var:
                self.context[output_var] = result.output

        # Return final result
        return_expr = composition.get("return", "${output}")
        final_output = self._interpolate(return_expr)

        return StageResult(name="composition", output=final_output, success=True)

    def _execute_stage(self, stage: dict) -> StageResult:
        """Execute a single stage."""
        skill_name = stage["skill"]
        args_template = stage.get("args", "")

        # Interpolate arguments
        if isinstance(args_template, str):
            args = self._interpolate(args_template)
        elif isinstance(args_template, dict):
            args = {k: self._interpolate(v) for k, v in args_template.items()}
        else:
            args = args_template

        # Execute skill
        try:
            skill = self.skill_manager.skills.get(skill_name)
            if not skill:
                return StageResult(
                    name=stage["name"],
                    output=None,
                    success=False,
                    error=f"Skill '{skill_name}' not found",
                )

            # Execute skill (simplified - actual implementation would use session)
            output = self._execute_skill(skill, args)

            return StageResult(name=stage["name"], output=output, success=True)
        except Exception as e:
            return StageResult(
                name=stage["name"], output=None, success=False, error=str(e)
            )

    def _interpolate(self, template: str) -> str:
        """Interpolate variables in template string."""
        if not isinstance(template, str):
            return template

        # Replace ${var} with context values
        def replace_var(match):
            var_path = match.group(1)
            return str(self._resolve_path(var_path))

        return re.sub(r"\$\{([^}]+)\}", replace_var, template)

    def _resolve_path(self, path: str) -> Any:
        """Resolve dotted path in context."""
        parts = path.split(".")
        value = self.context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _execute_skill(self, skill: dict, args: Any) -> Any:
        """Execute a skill and return output."""
        # Convert dict args to string for skill execution
        if isinstance(args, dict):
            import json
            args_str = json.dumps(args)
        else:
            args_str = str(args)

        # Call skill_manager's execute_skill method
        return self.skill_manager.execute_skill(skill['name'], args_str)
