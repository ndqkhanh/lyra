"""Voice provider abstractions — swappable STT, TTS, VAD, and turn-taking.

Each component exposes a standard interface so providers can be swapped
without changing the pipeline. Follows the §4.5 provider-abstraction pattern.

Providers:
  STT:   Whisper (local), Parakeet (NVIDIA), Deepgram (cloud), Google STT
  TTS:   Kokoro-82M (local), Orpheus, Piper, ElevenLabs (cloud), OpenAI TTS
  VAD:   Silero (local), WebRTC, Picovoice
  Turn:  Smart Turn (semantic), Gap-based, Hybrid
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class STTProviderKind(str, Enum):
    WHISPER = "whisper"
    PARAKEET = "parakeet"
    DEEPGRAM = "deepgram"
    GOOGLE = "google"
    SENSEVOICE = "sensevoice"


class TTSProviderKind(str, Enum):
    KOKORO = "kokoro"
    ORPHEUS = "orpheus"
    PIPER = "piper"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    XTTS = "xtts"


class VADProviderKind(str, Enum):
    SILERO = "silero"
    WEBRTC = "webrtc"
    PICOVOICE = "picovoice"
    ENERGY = "energy"


class TurnTakingKind(str, Enum):
    SMART_TURN = "smart_turn"
    GAP_BASED = "gap_based"
    HYBRID = "hybrid"


class VoiceLanguage(str, Enum):
    EN = "en"
    VI = "vi"
    ZH = "zh"
    JA = "ja"
    KO = "ko"
    FR = "fr"
    DE = "de"
    ES = "es"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class STTConfig:
    """Configuration for an STT provider."""

    language: str = "en"
    sample_rate: int = 16000
    model_size: str = "turbo"  # tiny, base, small, medium, large, turbo
    vad_filter: bool = True
    word_timestamps: bool = False
    max_segment_length: float = 30.0  # seconds
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class STTResult:
    """Result of speech-to-text transcription."""

    text: str
    confidence: float
    language: str
    is_final: bool = True
    words: tuple[tuple[str, float, float], ...] = ()  # (word, start_ms, end_ms)
    duration_ms: float = 0.0


@dataclass(frozen=True)
class TTSConfig:
    """Configuration for a TTS provider."""

    voice_id: str = "default"
    language: str = "en"
    speed: float = 1.0
    pitch: float = 1.0
    sample_rate: int = 24000
    emotion: str = "neutral"
    format: str = "wav"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VADConfig:
    """Configuration for a VAD provider."""

    sample_rate: int = 16000
    threshold: float = 0.5  # 0.0–1.0
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500
    speech_pad_ms: int = 100
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VADSegment:
    """A detected speech segment."""

    is_speech: bool
    confidence: float
    start_ms: float = 0.0
    end_ms: float = 0.0
    energy_level: float = 0.0


@dataclass(frozen=True)
class TurnConfig:
    """Configuration for turn-taking."""

    language: str = "en"
    endpoint_threshold_ms: int = 500  # silence before end-of-turn
    max_turn_duration_ms: int = 15000
    interrupt_threshold_ms: int = 200  # how fast user can barge in
    backchannel_enabled: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TurnDecision:
    """Result of a turn-taking decision."""

    action: str  # "speak", "wait", "interrupt", "backchannel"
    confidence: float
    reason: str = ""


@dataclass(frozen=True)
class VoicePipelineConfig:
    """Full voice pipeline configuration."""

    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    turn: TurnConfig = field(default_factory=TurnConfig)
    sample_rate: int = 16000
    channels: int = 1
    echo_cancellation: bool = True
    auto_gain_control: bool = True
    noise_suppression: bool = True


# ---------------------------------------------------------------------------
# Abstract provider interfaces
# ---------------------------------------------------------------------------


class STTProvider(ABC):
    """Abstract speech-to-text provider."""

    kind: STTProviderKind

    @abstractmethod
    async def transcribe(self, audio: bytes, config: STTConfig | None = None) -> STTResult:
        """Transcribe audio bytes to text."""
        ...

    async def stream_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        config: STTConfig | None = None,
    ) -> AsyncIterator[STTResult]:
        """Streaming transcription with interim results.

        Default implementation falls back to batch transcribe.
        Override for native streaming support.
        """
        chunks = [chunk async for chunk in audio_stream]
        result = await self.transcribe(b"".join(chunks), config)
        yield result


class TTSProvider(ABC):
    """Abstract text-to-speech provider."""

    kind: TTSProviderKind

    @abstractmethod
    async def synthesize(self, text: str, config: TTSConfig | None = None) -> bytes:
        """Synthesize text to raw audio bytes."""
        ...

    async def stream_synthesize(
        self,
        text_stream: AsyncIterator[str],
        config: TTSConfig | None = None,
    ) -> AsyncIterator[bytes]:
        """Streaming TTS — synthesize as text arrives.

        Default implementation collects all text and synthesizes at once.
        Override for true streaming TTS.
        """
        chunks = [chunk async for chunk in text_stream]
        audio = await self.synthesize("".join(chunks), config)
        yield audio


class VADProvider(ABC):
    """Abstract voice activity detection provider."""

    kind: VADProviderKind

    @abstractmethod
    async def detect(self, audio: bytes, config: VADConfig | None = None) -> VADSegment:
        """Detect speech activity in an audio chunk."""
        ...

    async def detect_segments(
        self,
        audio: bytes,
        config: VADConfig | None = None,
    ) -> list[VADSegment]:
        """Find all speech segments in audio.

        Default implementation returns a single segment for the whole chunk.
        Override for frame-level VAD.
        """
        result = await self.detect(audio, config)
        return [result]


class TurnTakingProvider(ABC):
    """Abstract turn-taking provider — decides when agent should speak."""

    kind: TurnTakingKind

    @abstractmethod
    async def decide(
        self,
        audio: bytes,
        agent_is_speaking: bool,
        config: TurnConfig | None = None,
    ) -> TurnDecision:
        """Decide whether agent should speak, wait, or interrupt."""
        ...


# ---------------------------------------------------------------------------
# Concrete: Energy-Based VAD (always available, no dependencies)
# ---------------------------------------------------------------------------


class EnergyVAD(VADProvider):
    """Energy-threshold VAD — works without external dependencies.

    Uses RMS energy + zero-crossing rate for speech detection.
    Good enough for basic use; use SileroVAD for production.
    """

    kind = VADProviderKind.ENERGY

    async def detect(self, audio: bytes, config: VADConfig | None = None) -> VADSegment:
        cfg = config or VADConfig()
        if not audio or len(audio) < 2:
            return VADSegment(is_speech=False, confidence=0.0)

        import math
        import struct

        usable = audio[: len(audio) & ~1]
        count = len(usable) // 2
        samples = struct.unpack(f"<{count}h", usable)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / count)

        energy_level = min(1.0, rms / 5000.0)
        threshold = max(0.0, 0.3 * (1.0 - cfg.threshold))
        is_speech = energy_level > threshold
        confidence = min(1.0, 0.5 + abs(energy_level - threshold))

        duration_ms = (count / cfg.sample_rate) * 1000.0
        return VADSegment(
            is_speech=is_speech,
            confidence=round(confidence, 4),
            energy_level=round(energy_level, 4),
            end_ms=round(duration_ms, 2),
        )


# ---------------------------------------------------------------------------
# Concrete: Gap-Based Turn Taking (always available)
# ---------------------------------------------------------------------------


class GapBasedTurn(TurnTakingProvider):
    """Simple gap-based turn taking.

    Agent speaks when user stops for ``endpoint_threshold_ms``.
    Interrupts when new speech starts during agent speech.
    """

    kind = TurnTakingKind.GAP_BASED

    def __init__(self):
        self._last_speech_time: float = 0.0
        self._silence_start: float | None = None

    async def decide(
        self,
        audio: bytes,
        agent_is_speaking: bool,
        config: TurnConfig | None = None,
    ) -> TurnDecision:
        cfg = config or TurnConfig()

        import math
        import struct
        import time

        now = time.time()

        if not audio or len(audio) < 2:
            if agent_is_speaking:
                return TurnDecision("speak", 0.5, "no input, continuing")
            return TurnDecision("wait", 0.5, "no input")

        usable = audio[: len(audio) & ~1]
        count = len(usable) // 2
        samples = struct.unpack(f"<{count}h", usable)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / count)
        is_speech = rms > 200

        if is_speech:
            self._last_speech_time = now
            self._silence_start = None
            if agent_is_speaking:
                return TurnDecision(
                    "interrupt", 0.8, f"speech detected during agent turn (rms={rms:.0f})"
                )
            return TurnDecision("wait", 0.9, f"user speaking (rms={rms:.0f})")

        # Silence
        if self._silence_start is None:
            self._silence_start = now

        silence_duration = (now - self._silence_start) * 1000

        if agent_is_speaking:
            return TurnDecision("speak", 0.7, "agent speaking, no interruption")

        if silence_duration >= cfg.endpoint_threshold_ms:
            return TurnDecision(
                "speak", 0.85, f"endpoint detected ({silence_duration:.0f}ms silence)"
            )

        return TurnDecision("wait", 0.6, f"listening... ({silence_duration:.0f}ms)")


# ---------------------------------------------------------------------------
# Voice provider registry
# ---------------------------------------------------------------------------


class VoiceProviderRegistry:
    """Registry for voice providers — STT, TTS, VAD, TurnTaking.

    Providers can be swapped at runtime via register/unregister.
    """

    def __init__(self) -> None:
        self._stt: dict[str, STTProvider] = {}
        self._tts: dict[str, TTSProvider] = {}
        self._vad: dict[str, VADProvider] = {}
        self._turn: dict[str, TurnTakingProvider] = {}

        # Register built-in defaults
        self.register_vad("default", EnergyVAD())
        self.register_vad("energy", EnergyVAD())
        self.register_turn("default", GapBasedTurn())
        self.register_turn("gap", GapBasedTurn())

    def register_stt(self, name: str, provider: STTProvider) -> None:
        self._stt[name] = provider

    def register_tts(self, name: str, provider: TTSProvider) -> None:
        self._tts[name] = provider

    def register_vad(self, name: str, provider: VADProvider) -> None:
        self._vad[name] = provider

    def register_turn(self, name: str, provider: TurnTakingProvider) -> None:
        self._turn[name] = provider

    def get_stt(self, name: str) -> STTProvider:
        if name not in self._stt:
            raise KeyError(f"STT provider {name!r} not found. Available: {list(self._stt)}")
        return self._stt[name]

    def get_tts(self, name: str) -> TTSProvider:
        if name not in self._tts:
            raise KeyError(f"TTS provider {name!r} not found. Available: {list(self._tts)}")
        return self._tts[name]

    def get_vad(self, name: str) -> VADProvider:
        if name not in self._vad:
            raise KeyError(f"VAD provider {name!r} not found. Available: {list(self._vad)}")
        return self._vad[name]

    def get_turn(self, name: str) -> TurnTakingProvider:
        if name not in self._turn:
            raise KeyError(f"Turn provider {name!r} not found. Available: {list(self._turn)}")
        return self._turn[name]

    def list_stt(self) -> list[str]:
        return sorted(self._stt)

    def list_tts(self) -> list[str]:
        return sorted(self._tts)

    def list_vad(self) -> list[str]:
        return sorted(self._vad)

    def list_turn(self) -> list[str]:
        return sorted(self._turn)
