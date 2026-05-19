"""
Model router for task-based model selection.

Routes tasks to appropriate models based on role and complexity,
with fallback support for reliability.
"""

from typing import Dict, Literal

RoleType = Literal["discovery", "analysis", "synthesis", "review", "curator"]
ComplexityType = Literal["low", "medium", "high"]


class ModelRouter:
    """Routes tasks to appropriate models based on role and complexity."""

    def __init__(self):
        """Initialize model router with default configurations."""
        self.model_configs: Dict[str, Dict[str, str]] = {
            "discovery": {
                "primary": "claude-haiku-4-5",
                "fallback": "gpt-4o-mini"
            },
            "analysis": {
                "primary": "claude-sonnet-4-6",
                "fallback": "gpt-4o"
            },
            "synthesis": {
                "primary": "claude-opus-4-7",
                "fallback": "gpt-4o"
            },
            "review": {
                "primary": "gpt-4o-mini",
                "fallback": "claude-sonnet-4-6"
            },
            "curator": {
                "primary": "claude-opus-4-7",
                "fallback": "gpt-4o"
            }
        }

        # Complexity-based overrides
        self.complexity_overrides: Dict[ComplexityType, Dict[str, str]] = {
            "low": {
                "analysis": "claude-haiku-4-5",
                "synthesis": "claude-sonnet-4-6"
            },
            "high": {
                "discovery": "claude-sonnet-4-6",
                "review": "claude-sonnet-4-6"
            }
        }

    def route(self, role: str, task_complexity: str = "medium") -> str:
        """
        Route to appropriate model based on role and complexity.

        Args:
            role: The role performing the task
            task_complexity: Task complexity level (low, medium, high)

        Returns:
            Model identifier string

        Raises:
            ValueError: If role is not recognized
        """
        if role not in self.model_configs:
            raise ValueError(f"Unknown role: {role}")

        # Check for complexity override
        if task_complexity in self.complexity_overrides:
            overrides = self.complexity_overrides[task_complexity]
            if role in overrides:
                return overrides[role]

        # Return primary model for role
        return self.model_configs[role]["primary"]

    def get_fallback(self, role: str) -> str:
        """
        Get fallback model if primary fails.

        Args:
            role: The role performing the task

        Returns:
            Fallback model identifier string

        Raises:
            ValueError: If role is not recognized
        """
        if role not in self.model_configs:
            raise ValueError(f"Unknown role: {role}")

        return self.model_configs[role]["fallback"]

    def get_model_family(self, model: str) -> str:
        """
        Get model family (claude or gpt) from model identifier.

        Args:
            model: Model identifier string

        Returns:
            Model family name ("claude" or "gpt")
        """
        if model.startswith("claude-"):
            return "claude"
        elif model.startswith("gpt-"):
            return "gpt"
        else:
            return "unknown"

    def update_config(self, role: str, primary: str, fallback: str) -> None:
        """
        Update model configuration for a role.

        Args:
            role: The role to update
            primary: New primary model
            fallback: New fallback model
        """
        self.model_configs[role] = {
            "primary": primary,
            "fallback": fallback
        }
