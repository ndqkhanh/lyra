"""
Sound Manager

Main sound management system with theme switching and volume control.
"""

from .audio_player import AudioPlayer
from .config import SoundConfig
from .theme_manager import ThemeManager


class SoundManager:
    """
    Main sound management system

    Features:
    - Play sounds for events
    - Theme switching
    - Volume control
    - Mute/unmute
    """

    def __init__(self, config: SoundConfig | None = None):
        self.config = config or SoundConfig()
        self.player = AudioPlayer()
        self.theme_manager = ThemeManager()
        self.muted = False

    def play_event(self, event: str, volume: float | None = None):
        """
        Play sound for event

        Args:
            event: Event name (e.g., "task_complete")
            volume: Override volume (uses config if None)
        """
        if self.muted or not self.config.enabled:
            return

        # Get sound path from current theme
        sound_path = self.theme_manager.get_sound_path(
            self.config.theme,
            event
        )

        if not sound_path or not sound_path.exists():
            return

        # Use provided volume or config volume
        vol = volume if volume is not None else self.config.volume

        # Play in background
        self.player.play(sound_path, volume=vol, background=True)

    def set_theme(self, theme_name: str):
        """Change sound theme"""
        if theme_name in self.theme_manager.list_themes():
            self.config.theme = theme_name
            self.config.save()

    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        self.config.volume = max(0.0, min(1.0, volume))
        self.config.save()

    def mute(self):
        """Mute all sounds"""
        self.muted = True

    def unmute(self):
        """Unmute sounds"""
        self.muted = False

    def toggle_mute(self) -> bool:
        """Toggle mute state"""
        self.muted = not self.muted
        return self.muted
