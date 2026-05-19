"""
Configuration Manager - Configuration file management.

Features:
- Configuration loading and saving
- Default configuration
- Configuration validation
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigurationManager:
    """
    Configuration manager for audio system.

    Features:
    - Load/save configuration
    - Default values
    - Validation
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        if config_path:
            self.config_path = Path(config_path).expanduser()
        else:
            self.config_path = Path("~/.lyra/audio_config.json").expanduser()

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._default_config()
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "enabled": True,
            "theme": "warcraft",
            "volume": 0.7,
            "adaptive_volume": {
                "enabled": True,
                "base_volume": 0.7,
                "boost_amount": 0.3,
                "inactivity_threshold": 30.0,
            },
            "time_behavior": {
                "enabled": True,
                "ridiculous_start_hour": 17,
                "ridiculous_boost": 0.2,
            },
            "productivity_mode": {
                "enabled": False,
                "focus_mode": False,
                "deadline_threshold_hours": 2.0,
            },
        }

    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Set configuration value."""
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        self.save()

    def reset(self):
        """Reset to default configuration."""
        self.config = self._default_config()
        self.save()

    def export(self, path: str):
        """Export configuration to file."""
        export_path = Path(path).expanduser()
        try:
            with open(export_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            pass

    def import_config(self, path: str):
        """Import configuration from file."""
        import_path = Path(path).expanduser()
        if import_path.exists():
            try:
                with open(import_path, "r") as f:
                    self.config = json.load(f)
                self.save()
            except (json.JSONDecodeError, IOError):
                pass
