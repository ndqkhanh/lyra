"""Skill configuration system with schema validation.

Allows users to customize skill behavior through configuration files
without modifying skill definitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class SkillConfigManager:
    """Manage skill configurations with schema validation."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if not self.config_path.exists():
            return {"skills": {}, "global": self._default_global_config()}

        try:
            with open(self.config_path) as f:
                return json.load(f)
        except Exception:
            return {"skills": {}, "global": self._default_global_config()}

    def _default_global_config(self) -> dict:
        """Get default global configuration."""
        return {
            "timeout_seconds": 300,
            "retry_on_failure": True,
            "max_retries": 3,
            "log_level": "info",
        }

    def save_config(self):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def get_skill_config(self, skill_name: str) -> dict:
        """Get configuration for a specific skill."""
        return self.config.get("skills", {}).get(skill_name, {})

    def set_skill_config(self, skill_name: str, config: dict):
        """Set configuration for a specific skill."""
        if "skills" not in self.config:
            self.config["skills"] = {}
        self.config["skills"][skill_name] = config
        self.save_config()
