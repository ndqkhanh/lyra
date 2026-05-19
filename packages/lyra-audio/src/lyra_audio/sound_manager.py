"""
Sound Manager - Sound effect management.

Features:
- Event-to-sound mapping
- Theme management
- Sound file loading
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from lyra_audio.audio_player import AudioPlayer


class SoundManager:
    """
    Sound effect manager.

    Features:
    - Event-to-sound mapping
    - Theme switching
    - Sound file management
    """

    def __init__(self, sounds_dir: Optional[str] = None):
        """Initialize sound manager."""
        if sounds_dir:
            self.sounds_dir = Path(sounds_dir).expanduser()
        else:
            self.sounds_dir = Path("~/.lyra/sounds").expanduser()

        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        self.player = AudioPlayer()
        self.config = self._load_config()
        self.current_theme = self.config.get("theme", "default")
        self.enabled = self.config.get("enabled", True)
        self.volume = self.config.get("volume", 0.7)

    def _load_config(self) -> Dict[str, Any]:
        """Load audio configuration."""
        config_path = Path("~/.lyra/audio.json").expanduser()

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._default_config()
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "enabled": True,
            "theme": "default",
            "volume": 0.7,
            "soundsDir": str(self.sounds_dir),
        }

    def _save_config(self):
        """Save configuration."""
        config_path = Path("~/.lyra/audio.json").expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            pass

    def play_event(self, event: str):
        """
        Play sound for event.

        Args:
            event: Event name
        """
        if not self.enabled:
            return

        if not self.player.is_available():
            return

        sound_file = self._get_sound_for_event(event)
        if sound_file and sound_file.exists():
            self.player.play_async(str(sound_file), volume=self.volume)

    def _get_sound_for_event(self, event: str) -> Optional[Path]:
        """
        Get sound file for event.

        Args:
            event: Event name

        Returns:
            Path to sound file or None
        """
        theme_dir = self.sounds_dir / self.current_theme

        if not theme_dir.exists():
            return None

        # Try to find sound file
        for ext in [".mp3", ".wav", ".ogg"]:
            sound_file = theme_dir / f"{event}{ext}"
            if sound_file.exists():
                return sound_file

        return None

    def set_theme(self, theme: str):
        """
        Set current theme.

        Args:
            theme: Theme name
        """
        theme_dir = self.sounds_dir / theme
        if theme_dir.exists():
            self.current_theme = theme
            self.config["theme"] = theme
            self._save_config()

    def get_theme(self) -> str:
        """Get current theme."""
        return self.current_theme

    def list_themes(self) -> List[str]:
        """List available themes."""
        if not self.sounds_dir.exists():
            return []

        themes = []
        for item in self.sounds_dir.iterdir():
            if item.is_dir():
                themes.append(item.name)

        return sorted(themes)

    def enable(self):
        """Enable sound effects."""
        self.enabled = True
        self.config["enabled"] = True
        self._save_config()

    def disable(self):
        """Disable sound effects."""
        self.enabled = False
        self.config["enabled"] = False
        self._save_config()

    def is_enabled(self) -> bool:
        """Check if sound effects are enabled."""
        return self.enabled

    def set_volume(self, volume: float):
        """
        Set volume level.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        self.config["volume"] = self.volume
        self._save_config()

    def get_volume(self) -> float:
        """Get current volume level."""
        return self.volume
