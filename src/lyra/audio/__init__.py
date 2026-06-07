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

from lyra.audio.adaptive_volume import AdaptiveVolumeController
from lyra.audio.audio_player import AudioPlayer
from lyra.audio.audio_suppression import (
    AudioSuppression,
    SilentHours,
    SuppressionConfig,
    SuppressionReason,
    SuppressionResult,
    create_default_suppression,
)
from lyra.audio.cesp_engine import (
    HOOK_TO_CESP,
    CespCategory,
    CespEngine,
    PackSelectionLayer,
    PlaybackRecord,
    SelectionResult,
)
from lyra.audio.event_hooks import EventHookSystem, LyraEvent
from lyra.audio.productivity_mode import ProductivityModeController
from lyra.audio.sound_cli import SoundPackCLI
from lyra.audio.sound_manager import SoundManager
from lyra.audio.sound_pack import SoundPack, SoundPackLoader, SoundPackMetadata
from lyra.audio.time_behavior import TimeBehaviorController

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
    # CESP Engine
    "CespCategory",
    "CespEngine",
    "HOOK_TO_CESP",
    "PackSelectionLayer",
    "PlaybackRecord",
    "SelectionResult",
    # Audio Suppression
    "AudioSuppression",
    "SilentHours",
    "SuppressionConfig",
    "SuppressionReason",
    "SuppressionResult",
    "create_default_suppression",
    # Advanced Features
    "AdaptiveVolumeController",
    "TimeBehaviorController",
    "ProductivityModeController",
    # CLI
    "SoundPackCLI",
]
