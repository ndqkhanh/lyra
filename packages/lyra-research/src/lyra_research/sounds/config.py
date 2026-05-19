"""
Sound Configuration

Configuration management for sound system.
"""

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Optional


@dataclass
class SoundConfig:
    """Sound system configuration"""
    enabled: bool = True
    theme: str = "warcraft"
    volume: float = 0.5
    adaptive_volume: bool = False
    context_aware: bool = False
    productivity_mode: bool = False

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".lyra" / "sounds_config.json"
        self.enabled = True
        self.theme = "warcraft"
        self.volume = 0.5
        self.adaptive_volume = False
        self.context_aware = False
        self.productivity_mode = False

        if self.config_path.exists():
            self._load()

    def _load(self):
        """Load config from file"""
        with open(self.config_path) as f:
            data = json.load(f)
            self.enabled = data.get("enabled", True)
            self.theme = data.get("theme", "warcraft")
            self.volume = data.get("volume", 0.5)
            self.adaptive_volume = data.get("adaptive_volume", False)
            self.context_aware = data.get("context_aware", False)
            self.productivity_mode = data.get("productivity_mode", False)

    def save(self):
        """Save config to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({
                "enabled": self.enabled,
                "theme": self.theme,
                "volume": self.volume,
                "adaptive_volume": self.adaptive_volume,
                "context_aware": self.context_aware,
                "productivity_mode": self.productivity_mode
            }, f, indent=2)
