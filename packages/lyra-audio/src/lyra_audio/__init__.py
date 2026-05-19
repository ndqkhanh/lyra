"""
Lyra Audio - Audio system and sound effects.

This package provides:
- Cross-platform audio playback
- Sound effect management
- Event-driven audio
- Theme support
- Sound pack library
- Advanced features (adaptive volume, time behavior, productivity mode)
- CLI interface for sound pack management
"""

from lyra_audio.adaptive_volume import AdaptiveVolumeController
from lyra_audio.audio_player import AudioPlayer
from lyra_audio.event_hooks import EventHookSystem, LyraEvent
from lyra_audio.productivity_mode import ProductivityModeController
from lyra_audio.sound_cli import SoundPackCLI
from lyra_audio.sound_manager import SoundManager
from lyra_audio.sound_pack import SoundPack, SoundPackLoader, SoundPackMetadata
from lyra_audio.time_behavior import TimeBehaviorController

__version__ = "0.1.0"

__all__ = [
    # Audio Player
    "AudioPlayer",
    # Sound Manager
    "SoundManager",
    # Event Hooks
    "EventHookSystem",
    "LyraEvent",
    # Sound Pack
    "SoundPack",
    "SoundPackLoader",
    "SoundPackMetadata",
    # Advanced Features
    "AdaptiveVolumeController",
    "TimeBehaviorController",
    "ProductivityModeController",
    # CLI
    "SoundPackCLI",
]
