"""
Lyra Audio - Audio system and sound effects.

This package provides:
- Cross-platform audio playback
- Sound effect management
- Event-driven audio
- Theme support
"""

from lyra_audio.audio_player import AudioPlayer
from lyra_audio.event_hooks import EventHookSystem, LyraEvent
from lyra_audio.sound_manager import SoundManager

__version__ = "0.1.0"

__all__ = [
    # Audio Player
    "AudioPlayer",
    # Sound Manager
    "SoundManager",
    # Event Hooks
    "EventHookSystem",
    "LyraEvent",
]
