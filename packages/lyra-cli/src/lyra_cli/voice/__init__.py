"""🧬 Lyra Voice Integration System (US-014) — STT, TTS, audio management,
sound notifications, and voice session management.

Provides speech-to-text, text-to-speech, audio device management,
sound notifications for agent lifecycle, and full-duplex voice sessions
with wake-word detection. Graceful degradation when backends are unavailable.

Sub-modules
-----------
tts_engine       — Text-to-Speech with multiple backends + factory
stt_engine       — Speech-to-Text with multiple backends + confidence scoring
audio_manager    — Audio device enumeration, selection, volume, format config
sound_notifications — Sound effects for agent states (system beep fallback)
voice_session    — Wake word detection, conversation state, command routing
"""

from __future__ import annotations

from .audio_manager import AudioConfig, AudioDevice, AudioError, AudioManager
from .sound_notifications import (
    AgentState,
    SoundConfig,
    SoundNotifier,
    get_sound_notifier,
)
from .stt_engine import (
    STTBackend,
    STTError,
    STTResult,
    SpeechRecognitionBackend,
    WhisperBackend,
    transcribe_audio,
)
from .tts_engine import (
    EdgeTTSBackend,
    Pyttsx3Backend,
    SystemSayBackend,
    TTSBackend,
    TTSConfig,
    TTSError,
    VoiceConfig,
    get_tts_engine,
    synthesize_speech,
)
from .voice_session import (
    SessionConfig,
    VoiceSession,
    WakeWordDetector,
    WakeWordResult,
)

# ── Voice personality engine ──────────────────────────────────────
from .personality_engine import PersonalityEngine, PersonalityRegistry
from .personalities import (
    ButlerPersonality,
    CowboyPersonality,
    DrillSergeantPersonality,
    PersonalityBase,
    PersonalityTrait,
    PiratePersonality,
    RobotPersonality,
    VoiceResponse,
    ZenMasterPersonality,
)

# Re-export from legacy modules for backward compatibility
from .stt import STTBackend as LegacySTTBackend  # noqa: F811
from .stt import STTError as LegacySTTError  # noqa: F811
from .stt import transcribe_audio as legacy_transcribe_audio  # noqa: F811
from .tts import TTSBackend as LegacyTTSBackend  # noqa: F811
from .tts import TTSError as LegacyTTSError  # noqa: F811
from .tts import synthesise_speech  # noqa: F401

__all__ = [
    # TTS
    "TTSConfig",
    "VoiceConfig",
    "TTSBackend",
    "SystemSayBackend",
    "Pyttsx3Backend",
    "EdgeTTSBackend",
    "TTSError",
    "get_tts_engine",
    "synthesize_speech",
    # STT
    "STTResult",
    "STTBackend",
    "WhisperBackend",
    "SpeechRecognitionBackend",
    "STTError",
    "transcribe_audio",
    # Audio
    "AudioDevice",
    "AudioConfig",
    "AudioError",
    "AudioManager",
    # Sound notifications
    "AgentState",
    "SoundConfig",
    "SoundNotifier",
    "get_sound_notifier",
    # Voice session
    "SessionConfig",
    "WakeWordDetector",
    "WakeWordResult",
    "VoiceSession",
    # Legacy
    "LegacySTTBackend",
    "LegacySTTError",
    "LegacyTTSBackend",
    "LegacyTTSError",
    "legacy_transcribe_audio",
    "synthesise_speech",
]
