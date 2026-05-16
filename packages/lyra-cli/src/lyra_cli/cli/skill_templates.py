"""Skill template system for quick skill creation.

Provides built-in templates and rendering engine for creating new skills
from predefined patterns.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class TemplateVariable:
    """Variable definition for template."""

    name: str
    prompt: str
    required: bool
    pattern: Optional[str] = None
    choices: Optional[list[str]] = None
    multiline: bool = False
    default: Optional[str] = None


class SkillTemplateEngine:
    """Render skill templates with variable substitution."""

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.templates = self._load_templates()

    def _load_templates(self) -> dict[str, dict]:
        """Load all template definitions."""
        templates = {}

        if not self.templates_dir.exists():
            return self._get_builtin_templates()

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file) as f:
                    template_data = json.load(f)
                    templates[template_data["name"]] = template_data
            except Exception:
                pass

        # Merge with built-in templates
        templates.update(self._get_builtin_templates())

        return templates

    def _get_builtin_templates(self) -> dict[str, dict]:
        """Get built-in skill templates."""
        return {
            "prompt-skill": {
                "name": "prompt-skill",
                "description": "Simple prompt-based skill for single-turn interactions",
                "category": "template",
                "variables": [
                    {
                        "name": "skill_name",
                        "prompt": "Skill name (kebab-case)",
                        "required": True,
                        "pattern": "^[a-z][a-z0-9-]*$",
                    },
                    {
                        "name": "description",
                        "prompt": "Brief description",
                        "required": True,
                    },
                    {
                        "name": "category",
                        "prompt": "Category",
                        "required": True,
                        "choices": [
                            "research",
                            "development",
                            "testing",
                            "documentation",
                            "analysis",
                        ],
                    },
                    {
                        "name": "keywords",
                        "prompt": "Trigger keywords (comma-separated)",
                        "required": False,
                    },
                    {
                        "name": "system_prompt",
                        "prompt": "System prompt",
                        "required": True,
                        "multiline": True,
                    },
                ],
                "template": {
                    "name": "{{skill_name}}",
                    "version": "1.0.0",
                    "description": "{{description}}",
                    "category": "{{category}}",
                    "execution": {"type": "prompt"},
                    "trigger": {
                        "keywords": "{{keywords|split(',')}}",
                        "patterns": [],
                    },
                    "args": {"required": True, "hint": "input"},
                    "system_prompt": "{{system_prompt}}",
                },
            },
        }

    def render(self, template_name: str, variables: dict[str, str]) -> dict:
        """Render a template with provided variables.

        Args:
            template_name: Name of template to render
            variables: Dict of variable_name -> value

        Returns:
            Rendered skill definition
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")

        template = self.templates[template_name]
        template_def = template["template"]

        # Render template recursively
        return self._render_value(template_def, variables)

    def _render_value(self, value: Any, variables: dict[str, str]) -> Any:
        """Recursively render template values."""
        if isinstance(value, str):
            return self._render_string(value, variables)
        elif isinstance(value, dict):
            return {k: self._render_value(v, variables) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._render_value(item, variables) for item in value]
        else:
            return value

    def _render_string(self, template: str, variables: dict[str, str]) -> str:
        """Render a template string with variable substitution."""

        def replace_var(match):
            var_expr = match.group(1)

            # Handle filters (e.g., {{keywords|split(',')}})
            if "|" in var_expr:
                var_name, filter_expr = var_expr.split("|", 1)
                var_name = var_name.strip()
                filter_name = filter_expr.strip()

                value = variables.get(var_name, "")

                # Apply filter
                if filter_name.startswith("split("):
                    delimiter = filter_name[7:-2]
                    return str([s.strip() for s in value.split(delimiter) if s.strip()])
                else:
                    return value
            else:
                var_name = var_expr.strip()
                return variables.get(var_name, "")

        return re.sub(r"\{\{([^}]+)\}\}", replace_var, template)

    def list_templates(self) -> list[dict]:
        """List all available templates."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "category": t.get("category", "custom"),
            }
            for t in self.templates.values()
        ]

