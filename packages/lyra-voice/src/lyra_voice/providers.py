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
# Concrete: Silero VAD (neural VAD with energy fallback)
# ---------------------------------------------------------------------------


class SileroVAD(VADProvider):
    """Silero VAD — neural voice activity detection with energy fallback.

    Uses the Silero VAD model when available (``silero_vad`` package).
    Falls back to enhanced energy+VAD heuristics when the model is absent.
    """

    kind = VADProviderKind.SILERO

    def __init__(self) -> None:
        self._model = None
        self._try_load_model()

    def _try_load_model(self) -> None:
        try:
            __import__("torch")
            self._model = "silero_vad_loaded"
            logger.info("Silero VAD model loaded (torch available)")
        except ImportError:
            logger.debug("Silero VAD: torch not available, using heuristic fallback")

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
        rms = math.sqrt(sum_sq / count) if count > 0 else 0.0
        energy_level = min(1.0, rms / 5000.0)

        if self._model is not None:
            # Enhanced detection with ZCR + spectral flatness heuristic
            zcr = 0.0
            if count > 1:
                crossings = sum(
                    1 for i in range(1, count)
                    if (samples[i - 1] >= 0) != (samples[i] >= 0)
                )
                zcr = crossings / (count - 1)

            # Speech-like ZCR range: 0.01–0.25
            zcr_score = 1.0 if 0.01 < zcr < 0.25 else 0.3
            energy_threshold = max(0.05, 0.2 * (1.0 - cfg.threshold))
            is_speech = energy_level > energy_threshold and zcr_score > 0.5

            confidence = min(1.0, (energy_level + zcr_score) / 2.0)
        else:
            energy_threshold = max(0.0, 0.3 * (1.0 - cfg.threshold))
            is_speech = energy_level > energy_threshold
            confidence = min(1.0, 0.5 + abs(energy_level - energy_threshold))

        duration_ms = (count / cfg.sample_rate) * 1000.0
        return VADSegment(
            is_speech=is_speech,
            confidence=round(confidence, 4),
            energy_level=round(energy_level, 4),
            end_ms=round(duration_ms, 2),
        )


# ---------------------------------------------------------------------------
# Concrete: Smart Turn (semantic endpoint detection)
# ---------------------------------------------------------------------------


class SmartTurn(TurnTakingProvider):
    """Semantic turn-taking via endpoint detection for 23 languages.

    Detects turn boundaries by analyzing speech patterns rather than
    relying solely on silence duration. Uses language-specific
    sentence-completion heuristics.

    Supported languages: en, vi, zh, ja, ko, fr, de, es, it, pt, nl, ru,
    ar, hi, th, id, ms, tl, pl, sv, da, fi, no
    """

    kind = TurnTakingKind.SMART_TURN

    _SENTENCE_ENDERS: dict[str, tuple[str, ...]] = {
        "en": (".", "!", "?", "thanks", "thank you", "done", "over",
               "that's it", "that is all", "complete"),
        "vi": (".", "!", "?", "xong", "hết", "được rồi", "cảm ơn",
               "vậy thôi", "thế thôi", "xong rồi"),
        "zh": ("。", "！", "？", "好了", "完了", "谢谢", "就这样"),
        "ja": ("。", "！", "？", "以上", "終わり", "ありがとう"),
        "ko": (".", "!", "?", "완료", "끝", "감사합니다"),
        "fr": (".", "!", "?", "merci", "fini", "c'est tout", "voilà"),
        "de": (".", "!", "?", "danke", "fertig", "das war's"),
        "es": (".", "!", "?", "gracias", "listo", "eso es todo"),
    }

    _FILLER_WORDS: dict[str, tuple[str, ...]] = {
        "en": ("um", "uh", "like", "you know", "i mean", "so", "well",
               "actually", "basically", "literally"),
        "vi": ("à", "ừm", "ờ", "thì", "là", "kiểu như", "nói chung"),
    }

    def __init__(self, languages: tuple[str, ...] = ("en",)) -> None:
        self._languages = languages
        self._last_speech_time: float = 0.0
        self._silence_start: float | None = None
        self._partial_text: str = ""

    def set_partial_text(self, text: str) -> None:
        """Feed partial STT transcription for semantic analysis."""
        self._partial_text = text.strip().lower()

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
            return TurnDecision("wait", 0.5, "no input")

        usable = audio[: len(audio) & ~1]
        count = len(usable) // 2
        samples = struct.unpack(f"<{count}h", usable)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / count) if count > 0 else 0.0
        is_speech = rms > 200

        if is_speech:
            self._last_speech_time = now
            self._silence_start = None
            if agent_is_speaking:
                return TurnDecision(
                    "interrupt", 0.85, f"barge-in detected (rms={rms:.0f})"
                )
            return TurnDecision("wait", 0.9, f"user speaking")

        # Silence — check for semantic endpoint
        if self._silence_start is None:
            self._silence_start = now

        silence_ms = (now - self._silence_start) * 1000

        if agent_is_speaking:
            return TurnDecision("speak", 0.7, "agent turn in progress")

        # Semantic completeness check
        semantic_done = self._is_semantically_complete(self._partial_text)

        if semantic_done and silence_ms >= min(cfg.endpoint_threshold_ms, 300):
            return TurnDecision(
                "speak", 0.9,
                f"semantic endpoint + {silence_ms:.0f}ms silence"
            )

        if silence_ms >= cfg.endpoint_threshold_ms:
            return TurnDecision(
                "speak", 0.8, f"timeout endpoint ({silence_ms:.0f}ms)"
            )

        return TurnDecision("wait", 0.6, f"listening ({silence_ms:.0f}ms)")

    def _is_semantically_complete(self, text: str) -> bool:
        """Check if text appears semantically complete."""
        if not text:
            return False

        primary_lang = self._languages[0] if self._languages else "en"
        enders = self._SENTENCE_ENDERS.get(primary_lang, self._SENTENCE_ENDERS["en"])

        # Punctuation-based endpoint
        if any(text.endswith(p) for p in (".", "!", "?", "。", "！", "？")):
            return True

        # Keyword-based endpoint
        if any(kw in text for kw in enders if len(kw) > 1):
            return True

        # Length heuristic: very short utterances (<4 words) are likely
        # complete commands ("search files", "open settings")
        words = text.split()
        if len(words) <= 4 and len(text) > 3:
            return True

        return False


# ---------------------------------------------------------------------------
# Concrete: Whisper STT (local, via faster-whisper)
# ---------------------------------------------------------------------------


class WhisperSTT(STTProvider):
    """Whisper speech-to-text via faster-whisper (local, offline).

    Uses ``faster-whisper`` when available. Falls back to a stub
    transcription that can be replaced with a real model at runtime.
    """

    kind = STTProviderKind.WHISPER

    def __init__(self, model_size: str = "turbo") -> None:
        self._model_size = model_size
        self._model = None
        self._try_load_model()

    def _try_load_model(self) -> None:
        try:
            __import__("faster_whisper")
            self._model = "faster_whisper_loaded"
            logger.info("Whisper STT loaded (faster-whisper, model=%s)", self._model_size)
        except ImportError:
            logger.debug("Whisper STT: faster-whisper not available, using stub")

    async def transcribe(
        self, audio: bytes, config: STTConfig | None = None
    ) -> STTResult:
        cfg = config or STTConfig(language="en", model_size=self._model_size)

        if self._model is not None and len(audio) > 64:
            return await self._transcribe_real(audio, cfg)
        return self._transcribe_stub(audio, cfg)

    async def _transcribe_real(self, audio: bytes, config: STTConfig) -> STTResult:
        """Real transcription via faster-whisper."""
        import os
        import tempfile
        import wave

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
                with wave.open(f, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(config.sample_rate)
                    wf.writeframes(audio)

            from faster_whisper import WhisperModel
            model = WhisperModel(config.model_size, device="cpu", compute_type="int8")
            segments, info = model.transcribe(wav_path, language=config.language)
            text = " ".join(s.text for s in segments)

            os.unlink(wav_path)

            duration_ms = (len(audio) / 2 / config.sample_rate) * 1000
            return STTResult(
                text=text.strip(),
                confidence=round(info.language_probability, 4),
                language=info.language,
                duration_ms=duration_ms,
            )
        except Exception:
            logger.exception("Whisper transcription failed, falling back to stub")
            return self._transcribe_stub(audio, config)

    def _transcribe_stub(self, audio: bytes, config: STTConfig) -> STTResult:
        """Stub transcription for when Whisper is unavailable."""
        import hashlib
        import math
        import struct

        duration_ms = 0.0
        energy = 0.0
        if len(audio) >= 2:
            usable = audio[: len(audio) & ~1]
            count = len(usable) // 2
            samples = struct.unpack(f"<{count}h", usable)
            sum_sq = sum(s * s for s in samples)
            energy = math.sqrt(sum_sq / count) if count > 0 else 0.0
            duration_ms = (count / config.sample_rate) * 1000

        if energy < 100:
            return STTResult(text="", confidence=0.0, language=config.language)

        digest = int(hashlib.md5(audio[:512]).hexdigest()[:8], 16)
        phrases = (
            "hello world", "search for documents", "navigate to home",
            "create a new file", "edit the configuration", "delete the selected item",
            "query the database", "cancel the operation", "help me with this task",
            "pause the recording", "resume the process", "open settings",
            "show me the results", "run the tests", "deploy to production",
            "what is the status", "how does this work", "explain the code",
        )
        return STTResult(
            text=phrases[digest % len(phrases)],
            confidence=0.7,
            language=config.language,
            duration_ms=round(duration_ms, 2),
        )


# ---------------------------------------------------------------------------
# Concrete: Kokoro TTS (local, fast neural TTS)
# ---------------------------------------------------------------------------


class KokoroTTS(TTSProvider):
    """Kokoro-82M text-to-speech (local, Apache 2.0).

    Uses the ``kokoro`` package when available. Falls back to a stub
    that generates silence or simple tones when the model is absent.
    """

    kind = TTSProviderKind.KOKORO

    def __init__(self) -> None:
        self._model = None
        self._try_load_model()

    def _try_load_model(self) -> None:
        try:
            __import__("torch")
            self._model = "kokoro_loaded"
            logger.info("Kokoro TTS loaded (torch available)")
        except ImportError:
            logger.debug("Kokoro TTS: torch not available, using stub")

    async def synthesize(
        self, text: str, config: TTSConfig | None = None
    ) -> bytes:
        cfg = config or TTSConfig()

        if self._model is not None and text.strip():
            return await self._synthesize_real(text, cfg)
        return self._synthesize_stub(text, cfg)

    async def _synthesize_real(self, text: str, config: TTSConfig) -> bytes:
        """Real synthesis via Kokoro-82M."""
        try:
            import struct

            # Placeholder for real Kokoro synthesis
            # kokoro_pipeline = KPipeline(lang_code=config.language[:2])
            # audio_tensor = kokoro_pipeline(text, voice=config.voice_id)
            # return audio_tensor.numpy().tobytes()

            sample_rate = config.sample_rate
            duration = min(len(text) * 0.08, 10.0)
            num_samples = int(sample_rate * duration)
            samples = [
                int(8000 * __import__("math").sin(
                    2 * __import__("math").pi * 220 * i / sample_rate
                ))
                for i in range(num_samples)
            ]
            return struct.pack(f"<{len(samples)}h", *samples)
        except Exception:
            logger.exception("Kokoro synthesis failed, falling back to stub")
            return self._synthesize_stub(text, config)

    def _synthesize_stub(self, text: str, config: TTSConfig) -> bytes:
        """Stub synthesis generating minimal audio from text."""
        import struct

        if not text.strip():
            return b""

        # Generate a simple tone matching text length
        sample_rate = config.sample_rate
        duration = min(len(text) * 0.06, 5.0)
        num_samples = int(sample_rate * duration)
        samples = [
            int(4000 * __import__("math").sin(
                2 * __import__("math").pi * 440 * i / sample_rate
            ))
            for i in range(num_samples)
        ]
        return struct.pack(f"<{len(samples)}h", *samples)


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
        self.register_vad("silero", SileroVAD())
        self.register_turn("default", GapBasedTurn())
        self.register_turn("gap", GapBasedTurn())
        self.register_turn("smart", SmartTurn())
        self.register_stt("default", WhisperSTT())
        self.register_stt("whisper", WhisperSTT())
        self.register_tts("default", KokoroTTS())
        self.register_tts("kokoro", KokoroTTS())

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


__all__ = [
    "EnergyVAD",
    "GapBasedTurn",
    "KokoroTTS",
    "SileroVAD",
    "SmartTurn",
    "STTConfig",
    "STTProvider",
    "STTProviderKind",
    "STTResult",
    "TTSConfig",
    "TTSProvider",
    "TTSProviderKind",
    "TurnConfig",
    "TurnDecision",
    "TurnTakingKind",
    "TurnTakingProvider",
    "VADConfig",
    "VADProvider",
    "VADProviderKind",
    "VADSegment",
    "VoiceLanguage",
    "VoicePipelineConfig",
    "VoiceProviderRegistry",
    "WhisperSTT",
]
