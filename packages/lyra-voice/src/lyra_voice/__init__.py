"""
Lyra Voice — Voice interface layer for Lyra.

This package provides:
- Wake word detection (Porcupine, Snowboy, etc.)
- Voice activity detection (VAD) via energy threshold
- Voice command parsing and routing
- Voice session management
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import struct
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VoiceCommandAction(str, Enum):
    """High-level voice command action types.

    Parameters
    ----------
    EXECUTE : str
        Execute a task or program.
    SEARCH : str
        Search for information.
    NAVIGATE : str
        Navigate to a location or resource.
    CREATE : str
        Create a new resource.
    EDIT : str
        Modify an existing resource.
    DELETE : str
        Remove a resource.
    QUERY : str
        Ask a question or request data.
    CANCEL : str
        Cancel the current operation.
    HELP : str
        Request assistance.
    PAUSE : str
        Pause the current operation.
    RESUME : str
        Resume a paused operation.
    """

    EXECUTE = "EXECUTE"
    SEARCH = "SEARCH"
    NAVIGATE = "NAVIGATE"
    CREATE = "CREATE"
    EDIT = "EDIT"
    DELETE = "DELETE"
    QUERY = "QUERY"
    CANCEL = "CANCEL"
    HELP = "HELP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"


class WakeWordModel(str, Enum):
    """Supported wake word detection engines.

    Parameters
    ----------
    PORCUPINE : str
        Porcupine wake word engine (Picovoice).
    SNOWBOY : str
        Snowboy hotword detection.
    OPENWAKEWORD : str
        openWakeWord engine.
    CUSTOM : str
        Custom wake word implementation.
    NONE : str
        No wake word detection.
    """

    PORCUPINE = "PORCUPINE"
    SNOWBOY = "SNOWBOY"
    OPENWAKEWORD = "OPENWAKEWORD"
    CUSTOM = "CUSTOM"
    NONE = "NONE"


class VADMode(str, Enum):
    """Voice Activity Detection strategies.

    Parameters
    ----------
    ENERGY_THRESHOLD : str
        Simple energy-level based VAD.
    WEBRTC : str
        WebRTC VAD (Google Voice Activity Detector).
    SILERO : str
        Silero VAD (neural network based).
    HYBRID : str
        Combination of multiple VAD methods.
    """

    ENERGY_THRESHOLD = "ENERGY_THRESHOLD"
    WEBRTC = "WEBRTC"
    SILERO = "SILERO"
    HYBRID = "HYBRID"


# ---------------------------------------------------------------------------
# Data transfer objects (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WakeWordConfig:
    """Configuration for wake word detection.

    Parameters
    ----------
    model : str
        Wake word model identifier. Defaults to ``"PORCUPINE"``.
    sensitivity : float
        Detection sensitivity (0.0 — 1.0). Defaults to ``0.5``.
    custom_keywords : tuple[str, ...]
        Custom wake word phrases. Defaults to ``("hey lyra",)``.
    require_confirmation : bool
        Whether to require confirmation before acting on a wake word.
        Defaults to ``True``.
    cooldown_ms : int
        Minimum time (ms) between consecutive wake word detections.
        Defaults to ``2000``.
    """

    model: str = "PORCUPINE"
    sensitivity: float = 0.5
    custom_keywords: tuple[str, ...] = ("hey lyra",)
    require_confirmation: bool = True
    cooldown_ms: int = 2000


@dataclass(frozen=True)
class VoiceCommand:
    """A fully processed voice command with parsed action and parameters.

    Parameters
    ----------
    command_id : str
        Unique identifier for this command.
    raw_text : str
        The raw transcribed text of the command.
    action : str
        The detected voice command action.
    confidence : float
        Confidence score of the parsed command (0.0 — 1.0).
    params : tuple[tuple[str, str], ...]
        Extracted parameters as ``(key, value)`` pairs.
    context : str
        Optional contextual information for the command. Defaults to ``""``.
    timestamp : float
        Unix timestamp when the command was issued. Defaults to ``0.0``.
    """

    command_id: str
    raw_text: str
    action: str
    confidence: float
    params: tuple[tuple[str, str], ...]
    context: str = ""
    timestamp: float = 0.0


@dataclass(frozen=True)
class ParsedCommand:
    """Result of parsing a natural language voice command.

    Parameters
    ----------
    original_text : str
        The original input text.
    action : str
        The classified action label.
    intent : str
        The primary intent extracted from the command.
    entities : tuple[tuple[str, str], ...]
        Extracted entities as ``(entity_type, value)`` pairs.
    confidence : float
        Parsing confidence score (0.0 — 1.0).
    alternative_actions : tuple[str, ...]
        Alternative possible actions ranked by relevance.
    """

    original_text: str
    action: str
    intent: str
    entities: tuple[tuple[str, str], ...]
    confidence: float
    alternative_actions: tuple[str, ...]


@dataclass(frozen=True)
class VADResult:
    """Result of voice activity detection on an audio segment.

    Parameters
    ----------
    is_speech : bool
        Whether speech was detected.
    confidence : float
        Confidence of the VAD decision (0.0 — 1.0).
    energy_level : float
        Normalized energy level of the audio segment (0.0 — 1.0).
    duration_ms : float
        Duration of the analyzed audio segment in milliseconds.
    segment_start_ms : float
        Start time of the segment relative to the stream. Defaults to ``0.0``.
    segment_end_ms : float
        End time of the segment. Defaults to ``0.0``.
    """

    is_speech: bool
    confidence: float
    energy_level: float
    duration_ms: float
    segment_start_ms: float = 0.0
    segment_end_ms: float = 0.0


@dataclass(frozen=True)
class VoiceSession:
    """Represents an active or completed voice interaction session.

    Parameters
    ----------
    session_id : str
        Unique identifier for the session.
    start_time : float
        Unix timestamp when the session started.
    is_active : bool
        Whether the session is currently active.
    command_count : int
        Number of commands processed in this session.
    last_command : str
        Raw text of the most recent command.
    total_audio_processed_ms : float
        Total audio processed in milliseconds.
    """

    session_id: str
    start_time: float
    is_active: bool
    command_count: int
    last_command: str
    total_audio_processed_ms: float


@dataclass(frozen=True)
class VoiceConfig:
    """Configuration for the ``VoiceInterface``.

    Parameters
    ----------
    vad_mode : str
        Voice activity detection mode. Defaults to ``"ENERGY_THRESHOLD"``.
    vad_sensitivity : float
        VAD sensitivity (0.0 — 1.0). Defaults to ``0.5``.
    wake_word_enabled : bool
        Enable wake word detection. Defaults to ``True``.
    auto_punctuate : bool
        Automatically punctuate transcribed text. Defaults to ``True``.
    max_command_length : int
        Maximum allowed command text length. Defaults to ``500``.
    language : str
        Language code for speech processing. Defaults to ``"en"``.
    echo_cancellation : bool
        Enable echo cancellation. Defaults to ``True``.
    """

    vad_mode: str = "ENERGY_THRESHOLD"
    vad_sensitivity: float = 0.5
    wake_word_enabled: bool = True
    auto_punctuate: bool = True
    max_command_length: int = 500
    language: str = "en"
    echo_cancellation: bool = True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_rms(audio_chunk: bytes) -> float:
    """Compute the root-mean-square energy of raw 16-bit PCM audio data.

    Parameters
    ----------
    audio_chunk : bytes
        Raw 16-bit signed PCM audio bytes.

    Returns
    -------
    float
        RMS energy value. Returns ``0.0`` for empty or too-short input.
    """
    if not audio_chunk or len(audio_chunk) < 2:
        return 0.0

    # Truncate to an even number of bytes for 16-bit samples
    usable = audio_chunk[: len(audio_chunk) & ~1]
    count = len(usable) // 2
    samples = struct.unpack(f"<{count}h", usable)

    sum_sq = sum(s * s for s in samples)
    return math.sqrt(sum_sq / count)


# ---------------------------------------------------------------------------
# Action handler stubs (mapping for execute_command)
# ---------------------------------------------------------------------------

_ACTION_HANDLERS: dict[str, str] = {
    "EXECUTE": "Executing requested task",
    "SEARCH": "Searching for requested information",
    "NAVIGATE": "Navigating to requested location",
    "CREATE": "Creating requested resource",
    "EDIT": "Editing requested resource",
    "DELETE": "Deleting requested resource",
    "QUERY": "Querying requested information",
    "CANCEL": "Cancelling current operation",
    "HELP": "Providing assistance",
    "PAUSE": "Pausing current operation",
    "RESUME": "Resuming paused operation",
}


# ---------------------------------------------------------------------------
# VoiceInterface
# ---------------------------------------------------------------------------


class VoiceInterface:
    """Voice interface layer for Lyra.

    Provides wake word detection, voice activity detection, command parsing,
    command execution, and session management. The implementation uses stub
    heuristics (energy threshold, keyword matching) that can be replaced with
    production models.

    Parameters
    ----------
    config : VoiceConfig | None
        Voice processing configuration. A default ``VoiceConfig`` is used
        when ``None``.
    wake_word_config : WakeWordConfig | None
        Wake word configuration. A default ``WakeWordConfig`` is used when
        ``None``.
    """

    def __init__(
        self,
        config: VoiceConfig | None = None,
        wake_word_config: WakeWordConfig | None = None,
    ) -> None:
        self._config = config if config is not None else VoiceConfig()
        self._wake_word_config = (
            wake_word_config if wake_word_config is not None else WakeWordConfig()
        )
        self._active_session: VoiceSession | None = None
        self._last_wake_word_time: float = 0.0
        self._total_sessions: int = 0
        self._total_commands: int = 0
        self._total_wake_words_detected: int = 0
        self._total_speech_segments: int = 0
        logger.info("VoiceInterface initialized with config=%s ww_config=%s",
                     self._config, self._wake_word_config)

    # -- Wake Word Detection --------------------------------------------------

    def detect_wake_word(self, audio_chunk: bytes, _sample_rate: int = 16000) -> bool:
        """Detect a wake word in an audio chunk.

        Stub implementation using energy threshold and zero-crossing rate
        heuristics. In production this would use Porcupine, Snowboy, or a
        custom wake word model.

        Parameters
        ----------
        audio_chunk : bytes
            Raw 16-bit mono PCM audio data.
        sample_rate : int
            Sample rate of the audio in Hz. Defaults to 16000.

        Returns
        -------
        bool
            ``True`` if a wake word was detected, ``False`` otherwise.
        """
        if not self._config.wake_word_enabled:
            return False

        if not audio_chunk or len(audio_chunk) < 64:
            return False

        # Cooldown check
        now = time.time()
        if now - self._last_wake_word_time < self._wake_word_config.cooldown_ms / 1000.0:
            return False

        # Compute RMS energy
        rms = _compute_rms(audio_chunk)
        if rms < 50:
            return False

        # Normalize RMS to [0, 1] for threshold comparison
        # 16-bit max RMS is ~32767, speech typically 200-5000
        normalized_rms = min(1.0, rms / 5000.0)

        # Sensitivity-adjusted threshold (lower sensitivity = higher bar)
        if normalized_rms < (1.0 - self._wake_word_config.sensitivity) * 0.6:
            return False

        # Zero-crossing rate check — speech typically has ZCR in [0.01, 0.20]
        count = len(audio_chunk) // 2
        samples = struct.unpack(f"<{count}h", audio_chunk[:count * 2])
        zero_crossings = sum(
            1 for i in range(1, count)
            if (samples[i - 1] >= 0) != (samples[i] >= 0)
        )
        zcr = zero_crossings / max(1, count - 1)

        if not (0.005 < zcr < 0.25):
            return False

        self._last_wake_word_time = now
        self._total_wake_words_detected += 1
        logger.debug("Wake word detected (rms=%.2f, zcr=%.4f)", rms, zcr)
        return True

    # -- Voice Activity Detection ---------------------------------------------

    def detect_voice_activity(
        self, audio_chunk: bytes, sample_rate: int = 16000
    ) -> VADResult:
        """Detect voice activity in an audio chunk.

        Stub implementation using energy threshold VAD. Computes RMS energy
        of the audio and classifies as speech when the energy exceeds an
        adaptive threshold.

        Parameters
        ----------
        audio_chunk : bytes
            Raw 16-bit mono PCM audio data.
        sample_rate : int
            Sample rate of the audio in Hz. Defaults to 16000.

        Returns
        -------
        VADResult
            Voice activity detection result with energy level and confidence.
        """
        if not audio_chunk or len(audio_chunk) < 2:
            return VADResult(
                is_speech=False,
                confidence=0.0,
                energy_level=0.0,
                duration_ms=0.0,
            )

        # Compute duration in milliseconds
        bytes_per_sample = 2  # 16-bit
        num_samples = len(audio_chunk) // bytes_per_sample
        duration_ms = (num_samples / sample_rate) * 1000.0

        # Compute RMS energy
        rms = _compute_rms(audio_chunk)

        # Normalize energy to [0, 1] — typical speech RMS is 200-5000
        energy_level = min(1.0, rms / 5000.0)

        # Determine speech threshold from sensitivity
        # Higher sensitivity = lower threshold (easier to detect)
        threshold = max(0.0, 0.3 * (1.0 - self._config.vad_sensitivity))
        is_speech = energy_level > threshold

        # Confidence proportional to how far above/below the threshold
        if is_speech:
            confidence = min(1.0, 0.5 + (energy_level - threshold))
        else:
            confidence = min(1.0, 0.5 + (threshold - energy_level))

        if is_speech:
            self._total_speech_segments += 1

        return VADResult(
            is_speech=is_speech,
            confidence=round(confidence, 4),
            energy_level=round(energy_level, 4),
            duration_ms=round(duration_ms, 2),
        )

    # -- Command Parsing ------------------------------------------------------

    def parse_command(self, text: str, context: str = "") -> ParsedCommand:
        """Parse a natural language voice command into a structured command.

        Uses keyword matching to detect the action type, extract intent,
        and identify entities from the text.

        Parameters
        ----------
        text : str
            The raw transcribed voice command text.
        context : str
            Optional context from the current session. Defaults to ``""``.

        Returns
        -------
        ParsedCommand
            Structured command with detected action, intent, and entities.
        """
        if not text or not text.strip():
            return ParsedCommand(
                original_text=text or "",
                action="QUERY",
                intent="unknown",
                entities=(),
                confidence=0.0,
                alternative_actions=("HELP",),
            )

        text_lower = text.lower().strip()

        # Truncate if too long
        if len(text_lower) > self._config.max_command_length:
            text_lower = text_lower[: self._config.max_command_length]

        # Action keyword mapping (ordered by priority)
        action_keywords: list[tuple[str, tuple[str, ...]]] = [
            ("EXECUTE", ("execute", "run ", "launch ", "start ")),
            ("SEARCH", ("search", "find ", "lookup", "look for", "locate")),
            ("NAVIGATE", ("navigate", "go to", "open ", "go ", "show ")),
            ("CREATE", ("create", "make ", "new ", "build ", "generate")),
            ("EDIT", ("edit", "change ", "modify ", "update ", "rewrite")),
            ("DELETE", ("delete", "remove ", "erase ", "destroy")),
            ("CANCEL", ("cancel", "stop ", "abort ", "halt")),
            ("HELP", ("help", "what can you")),
            ("PAUSE", ("pause", "hold on")),
            ("RESUME", ("resume", "continue ", "unpause")),
            ("QUERY", ("query", "ask ", "what ", "how ", "why ",
                       "when ", "where ", "who ", "which ", "tell me")),
        ]

        detected_action = "QUERY"
        for action, keywords in action_keywords:
            if any(kw in text_lower for kw in keywords):
                detected_action = action
                break

        # Extract intent — text after the matched action keyword
        intent = text_lower
        for _, keywords in action_keywords:
            for kw in keywords:
                if kw in text_lower:
                    idx = text_lower.index(kw) + len(kw)
                    rest = text_lower[idx:].strip()
                    # Strip trailing filler words
                    for filler in (" for", " with", " using", " to"):
                        if filler in rest:
                            rest = rest[: rest.index(filler)]
                    if rest:
                        intent = rest[:80]
                    break

        # Extract entities
        entities: list[tuple[str, str]] = []
        seen_targets: set[str] = set()

        # "to TARGET", "for TARGET", "with TARGET"
        for marker in (" to ", " for ", " with ", " using "):
            if marker in text_lower:
                parts = text_lower.split(marker, 1)
                target = parts[1].split(" and ")[0].strip().rstrip(".")
                if target and target not in seen_targets:
                    entities.append(("target", target))
                    seen_targets.add(target)

        # Numbers as quantities
        numbers = re.findall(r"\d+", text)
        for num in numbers:
            if num not in seen_targets:
                entities.append(("quantity", num))
                seen_targets.add(num)

        # Location patterns
        location_match = re.search(r"(?:in|at|near|to)\s+([A-Za-z\s]+?)(?:\s|$|\.|,)", text)
        if location_match:
            loc = location_match.group(1).strip()
            if loc and loc not in seen_targets:
                entities.append(("location", loc))
                seen_targets.add(loc)

        # Confidence scoring
        confidence = 0.3
        if detected_action != "QUERY":
            confidence = 0.6
        if len(text_lower) > 8:
            confidence += 0.15
        if entities:
            confidence += 0.1
        if context:
            confidence += 0.05
        confidence = round(min(1.0, confidence), 2)

        # Alternative actions
        all_actions = ["EXECUTE", "SEARCH", "NAVIGATE", "CREATE", "EDIT",
                       "DELETE", "QUERY", "CANCEL", "HELP", "PAUSE", "RESUME"]
        alternatives = tuple(
            a for a in all_actions if a != detected_action
        )

        return ParsedCommand(
            original_text=text,
            action=detected_action,
            intent=intent if intent != text_lower else intent[:60],
            entities=tuple(entities),
            confidence=confidence,
            alternative_actions=alternatives,
        )

    # -- Command Execution ----------------------------------------------------

    def execute_command(self, command: ParsedCommand) -> dict[str, Any]:
        """Route a parsed command to the appropriate action handler.

        Stub implementation that returns a confirmation dictionary. In
        production this would invoke actual system actions.

        Parameters
        ----------
        command : ParsedCommand
            The parsed command to execute.

        Returns
        -------
        dict[str, Any]
            Execution result with ``status``, ``action``, and ``message`` keys.
        """
        message = _ACTION_HANDLERS.get(command.action, _ACTION_HANDLERS["QUERY"])
        result: dict[str, Any] = {
            "status": "ok",
            "action": command.action,
            "intent": command.intent,
            "message": f"{message}: {command.intent}",
            "confidence": command.confidence,
            "entities": list(command.entities),
            "executed": True,
        }

        if command.action == "SEARCH":
            result["results"] = []
        elif command.action == "CREATE":
            result["resource_id"] = str(uuid.uuid4())[:8]
        elif command.action == "CANCEL":
            result["cancelled"] = True

        self._total_commands += 1
        if self._active_session is not None:
            self._active_session = VoiceSession(
                session_id=self._active_session.session_id,
                start_time=self._active_session.start_time,
                is_active=self._active_session.is_active,
                command_count=self._active_session.command_count + 1,
                last_command=command.original_text,
                total_audio_processed_ms=self._active_session.total_audio_processed_ms,
            )
        logger.debug("Executed command: action=%s intent=%s",
                     command.action, command.intent)
        return result

    # -- Session Management ---------------------------------------------------

    def start_session(self) -> VoiceSession:
        """Start a new voice interaction session.

        Returns
        -------
        VoiceSession
            A new active session record.
        """
        session = VoiceSession(
            session_id=str(uuid.uuid4())[:8],
            start_time=time.time(),
            is_active=True,
            command_count=0,
            last_command="",
            total_audio_processed_ms=0.0,
        )
        self._active_session = session
        self._total_sessions += 1
        logger.info("Voice session started: %s", session.session_id)
        return session

    def end_session(self) -> VoiceSession:
        """End the currently active voice session.

        Returns
        -------
        VoiceSession
            The final session record with ``is_active=False``.

        Raises
        ------
        RuntimeError
            If there is no active session to end.
        """
        if self._active_session is None:
            raise RuntimeError("No active session to end")

        final = VoiceSession(
            session_id=self._active_session.session_id,
            start_time=self._active_session.start_time,
            is_active=False,
            command_count=self._active_session.command_count,
            last_command=self._active_session.last_command,
            total_audio_processed_ms=self._active_session.total_audio_processed_ms,
        )
        logger.info("Voice session ended: %s (commands=%d)",
                     final.session_id, final.command_count)
        self._active_session = None
        return final

    # -- Audio Stream Processing ----------------------------------------------

    def process_audio_stream(
        self, audio_chunks: list[bytes], sample_rate: int = 16000
    ) -> list[VoiceCommand]:
        """Process a stream of audio chunks through the full voice pipeline.

        Pipeline: wake word detection -> voice activity detection -> stub
        transcription -> command parsing -> command execution.

        Parameters
        ----------
        audio_chunks : list[bytes]
            Ordered list of raw 16-bit mono PCM audio chunks.
        sample_rate : int
            Sample rate of the audio in Hz. Defaults to 16000.

        Returns
        -------
        list[VoiceCommand]
            List of successfully parsed voice commands from the stream.
        """
        voice_commands: list[VoiceCommand] = []
        speech_buffer: list[bytes] = []
        wake_detected = False

        for chunk in audio_chunks:
            # Update session audio tracking
            if self._active_session is not None:
                chunk_ms = (len(chunk) / 2 / sample_rate) * 1000.0
                self._active_session = VoiceSession(
                    session_id=self._active_session.session_id,
                    start_time=self._active_session.start_time,
                    is_active=self._active_session.is_active,
                    command_count=self._active_session.command_count,
                    last_command=self._active_session.last_command,
                    total_audio_processed_ms=(
                        self._active_session.total_audio_processed_ms + chunk_ms
                    ),
                )

            # Wake word detection
            if not wake_detected and self._config.wake_word_enabled:
                wake_detected = self.detect_wake_word(chunk, sample_rate)

            # Voice activity detection
            vad = self.detect_voice_activity(chunk, sample_rate)

            if vad.is_speech:
                speech_buffer.append(chunk)

                # When wake word + speech accumulated, produce a command
                if wake_detected and speech_buffer:
                    combined = b"".join(speech_buffer)
                    text = self._stub_transcribe(combined)
                    if text:
                        voice_cmd = self._build_voice_command(text)
                        voice_commands.append(voice_cmd)
                        # Execute the command
                        parsed = self.parse_command(text)
                        self.execute_command(parsed)
                    wake_detected = False
                    speech_buffer = []
            else:
                # Flush speech buffer on silence (non-speech segment)
                if wake_detected and speech_buffer:
                    combined = b"".join(speech_buffer)
                    text = self._stub_transcribe(combined)
                    if text:
                        voice_cmd = self._build_voice_command(text)
                        voice_commands.append(voice_cmd)
                        parsed = self.parse_command(text)
                        self.execute_command(parsed)
                    wake_detected = False
                    speech_buffer = []

        return voice_commands

    def _stub_transcribe(self, audio_chunk: bytes) -> str:
        """Stub speech-to-text transcription based on audio characteristics.

        Uses a deterministic hash of the audio content to select a plausible
        transcription. In production this would call a real STT engine.

        Parameters
        ----------
        audio_chunk : bytes
            Raw 16-bit mono PCM audio data.

        Returns
        -------
        str
            A stub transcription string. Empty string for silent or invalid
            input.
        """
        if not audio_chunk or len(audio_chunk) < 32:
            return ""

        rms = _compute_rms(audio_chunk)
        if rms < 100:
            return ""

        # Deterministic selection based on audio content hash
        sample = audio_chunk[: min(512, len(audio_chunk))]
        digest = int(hashlib.md5(sample).hexdigest()[:8], 16)

        phrases = (
            "search for documents",
            "navigate to home",
            "create a new file",
            "edit the current file",
            "delete the selected item",
            "query the database",
            "cancel the operation",
            "help me with this",
            "pause the recording",
            "resume the process",
        )
        return phrases[digest % len(phrases)]

    def _build_voice_command(self, text: str) -> VoiceCommand:
        """Build a ``VoiceCommand`` from transcribed text.

        Parameters
        ----------
        text : str
            Transcribed text to convert into a command.

        Returns
        -------
        VoiceCommand
            A structured voice command with parsed action and parameters.
        """
        parsed = self.parse_command(text)

        return VoiceCommand(
            command_id=str(uuid.uuid4())[:8],
            raw_text=text,
            action=parsed.action,
            confidence=parsed.confidence,
            params=parsed.entities,
            context="",
            timestamp=time.time(),
        )

    # -- Statistics -----------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return cumulative usage statistics.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys ``total_sessions``, ``total_commands``,
            ``total_wake_words_detected``, and ``total_speech_segments``.
        """
        return {
            "total_sessions": self._total_sessions,
            "total_commands": self._total_commands,
            "total_wake_words_detected": self._total_wake_words_detected,
            "total_speech_segments": self._total_speech_segments,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

from lyra_voice.providers import (
    EnergyVAD,
    GapBasedTurn,
    KokoroTTS,
    SileroVAD,
    SmartTurn,
    STTConfig,
    STTProvider,
    STTProviderKind,
    STTResult,
    TTSConfig,
    TTSProvider,
    TTSProviderKind,
    TurnConfig,
    TurnDecision,
    TurnTakingKind,
    TurnTakingProvider,
    VADConfig,
    VADProvider,
    VADProviderKind,
    VADSegment,
    VoiceLanguage,
    VoicePipelineConfig,
    VoiceProviderRegistry,
    WhisperSTT,
)
from lyra_voice.pipeline import (
    InteractionMode,
    PipelineEvent,
    PipelineState,
    VoicePipeline,
    VoicePipelineStats,
    VoiceTurn,
)
from lyra_voice.sfx import (
    BUILTIN_PACKS,
    HOOK_TO_SFX,
    SFXAsset,
    SFXCategory,
    SFXManager,
    VoicePack,
)
from lyra_voice.voice_hooks import (
    DEFAULT_HOOK_MAPPINGS,
    HookEvent,
    PlaybackMode,
    VoiceHookManager,
    VoiceHookMapping,
    VoiceHookStats,
)

__version__ = "0.1.0"

__all__ = [
    # Enums
    "HookEvent",
    "PlaybackMode",
    "SFXCategory",
    "VADMode",
    "VoiceCommandAction",
    "WakeWordModel",
    # Data types
    "SFXAsset",
    "VoiceCommand",
    "VoiceConfig",
    "VoiceHookMapping",
    "VoiceHookStats",
    "VoicePack",
    "VoiceSession",
    "WakeWordConfig",
    # SFX
    "BUILTIN_PACKS",
    "HOOK_TO_SFX",
    "SFXManager",
    # Voice Hooks
    "DEFAULT_HOOK_MAPPINGS",
    "VoiceHookManager",
    # Main module
    "VoiceInterface",
    # Provider abstractions
    "EnergyVAD",
    "GapBasedTurn",
    "KokoroTTS",
    "SileroVAD",
    "SmartTurn",
    "STTProvider",
    "TTSProvider",
    "TurnTakingProvider",
    "VADProvider",
    "VoiceProviderRegistry",
    "WhisperSTT",
    # Pipeline
    "InteractionMode",
    "PipelineEvent",
    "PipelineState",
    "VoicePipeline",
    "VoicePipelineConfig",
    "VoicePipelineStats",
    "VoiceTurn",
    # Provider types
    "STTConfig",
    "STTProviderKind",
    "STTResult",
    "TTSConfig",
    "TTSProviderKind",
    "TurnConfig",
    "TurnDecision",
    "TurnTakingKind",
    "VADConfig",
    "VADProviderKind",
    "VADSegment",
    "VoiceLanguage",
]
