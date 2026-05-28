"""Configuration management for Lyra"""

import json
from pathlib import Path
from typing import Any


class ConfigManager:
    """Manages Lyra configuration"""

    def __init__(self, config_file: str | None = None):
        if config_file:
            self.config_file = Path(config_file)
        else:
            self.config_file = Path.home() / ".lyra" / "config.json"

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
        else:
            # Default configuration
            self.config = {
                "model": "opus",
                "verbose": False,
                "hooks_enabled": True,
                "learning_enabled": True,
                "mcp_enabled": True,
            }
            self.save()

        return self.config

    def save(self):
        """Save configuration to file"""
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save()

    def update(self, updates: dict[str, Any]):
        """Update multiple configuration values"""
        self.config.update(updates)
        self.save()


# Global config manager
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get or create global config manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load()
    return _config_manager
