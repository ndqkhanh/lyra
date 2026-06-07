"""
Voice Commander -- hold-to-talk fleet steering via voice commands.

Provides the ``VoiceCommander`` class that enables voice-only control of fleet
operations: route to an agent, query status, approve/deny actions, and
interrupt running tasks.

Voice input is bilingual (VI + EN) with automatic language detection via
the existing ``HeuristicLanguageDetector``. Transcribed text is parsed into
structured ``Command`` objects for downstream execution by a
``FleetOrchestrator`` or similar controller.

Voice packs from ``lyra.voice.sound_effects`` provide pre-built sound effect
collections for audio feedback (success, error, thinking, alert).

Usage::

    commander = VoiceCommander(stt=my_stt, tts=my_tts, fleet=my_fleet)

    # Hold-to-talk listen
    text = await commander.listen(timeout=5.0)

    # Parse as a command
    cmd = await commander.command(text)

    # Execute against fleet
    match cmd.type:
        case CommandType.ROUTE_TO_AGENT:
            fleet.spawn_agent(...)
        case CommandType.QUERY_STATUS:
            status = fleet.fleet_status()
            await commander.speak(str(status))
"""

from __future__ import annotations

import asyncio
import re
import structlog
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from lyra.voice.bilingual import HeuristicLanguageDetector, Language, LanguageResult
from lyra.voice.capture import AudioCapture, record_utterance
from lyra.voice.sound_effects import HookEvent, SoundEffectEngine, VoicePack
from lyra.voice.stt import STTProvider, STTError, TranscriptionResult
from lyra.voice.tts import TTSProvider, TTSError

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SILENCE_TIMEOUT: float = 1.5
"""Default seconds of silence before an utterance is considered complete."""

MAX_UTTERANCE_DURATION: float = 30.0
"""Maximum recording duration per utterance in seconds."""

LISTEN_SAMPLE_RATE: int = 16000
"""Sample rate used for voice capture."""

COMMAND_AGENT_NAME_RE: re.Pattern = re.compile(
    r"(?:go to|route to|switch to|connect to|open)\s+([\w-]+)",
    re.IGNORECASE,
)
"""Regex for extracting the target agent name from a route-to-agent command."""

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CommandType(Enum):
    """Structured voice command types that the fleet can execute.

    * ``ROUTE_TO_AGENT`` -- navigate the voice interface to a specific agent.
    * ``QUERY_STATUS`` -- request fleet or agent status information.
    * ``APPROVE_ACTION`` -- approve a pending agent action.
    * ``DENY_ACTION`` -- reject a pending agent action.
    * ``INTERRUPT`` -- interrupt the currently running operation.
    * ``UNKNOWN`` -- the utterance was not recognised as a command.
    """

    ROUTE_TO_AGENT = "route_to_agent"
    QUERY_STATUS = "query_status"
    APPROVE_ACTION = "approve_action"
    DENY_ACTION = "deny_action"
    INTERRUPT = "interrupt"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    """A parsed voice command ready for execution.

    Attributes:
        type: The classified command type.
        text: The original transcribed utterance.
        confidence: Confidence of the command classification (0.0 - 1.0).
        language: Detected language of the utterance.
        target: Optional target identifier (e.g. agent name for route).
        args: Additional extracted arguments from the utterance.
    """

    type: CommandType
    text: str
    confidence: float = 1.0
    language: Language = Language.EN
    target: str | None = None
    args: dict[str, str] = field(default_factory=dict)


@dataclass
class CommanderStats:
    """Aggregate statistics for the VoiceCommander.

    Attributes:
        total_commands: Total commands processed.
        total_listen_calls: Total ``listen()`` invocations.
        total_speak_calls: Total ``speak()`` invocations.
        recognised_count: Number of commands classified as recognised types
            (not UNKNOWN).
        unknown_count: Number of utterances classified as UNKNOWN.
        en_count: Number of English utterances.
        vi_count: Number of Vietnamese utterances.
        failures: Number of failures (STT, TTS, or parsing errors).
        total_listen_duration_ms: Cumulative time spent listening.
        total_parse_latency_ms: Cumulative time spent parsing commands.
    """

    total_commands: int = 0
    total_listen_calls: int = 0
    total_speak_calls: int = 0
    recognised_count: int = 0
    unknown_count: int = 0
    en_count: int = 0
    vi_count: int = 0
    failures: int = 0
    total_listen_duration_ms: float = 0.0
    total_parse_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Voice Commander
# ---------------------------------------------------------------------------


class VoiceCommander:
    """Hold-to-talk voice interface for fleet steering.

    Wraps STT, TTS, language detection, and command parsing into a single
    class that provides ``listen``, ``speak``, and ``command`` methods.

    Usage::

        commander = VoiceCommander(stt=my_stt, tts=my_tts)
        text = await commander.listen(timeout=5.0)
        cmd = await commander.command(text)

        if cmd.type == CommandType.ROUTE_TO_AGENT:
            await commander.speak(f"Routing to agent {cmd.target}")
    """

    def __init__(
        self,
        stt: STTProvider,
        tts: TTSProvider,
        capture: AudioCapture | None = None,
        language_detector: HeuristicLanguageDetector | None = None,
        sound_engine: SoundEffectEngine | None = None,
        fleet_notify: Callable[[Command], Any] | None = None,
    ) -> None:
        """Initialise the VoiceCommander.

        Args:
            stt: A speech-to-text provider for transcribing voice input.
            tts: A text-to-speech provider for voice output.
            capture: An ``AudioCapture`` instance. If ``None``, a default
                capture is created.
            language_detector: Language detector for VI+EN bilingual support.
                If ``None``, a ``HeuristicLanguageDetector`` with default
                thresholds is used.
            sound_engine: Optional ``SoundEffectEngine`` for playing voice
                pack sounds during listen/speak cycles. If ``None``, no
                sounds are played.
            fleet_notify: Optional callback invoked after every successful
                command parse. Receives the parsed ``Command``. This is the
                integration point for fleet orchestration.
        """
        self._stt = stt
        self._tts = tts
        self._capture = capture or AudioCapture(
            sample_rate=LISTEN_SAMPLE_RATE,
            use_vad=True,
        )
        self._detector = language_detector or HeuristicLanguageDetector()
        self._sound_engine = sound_engine
        self._fleet_notify = fleet_notify

        self._stats = CommanderStats()
        self._running = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def stats(self) -> CommanderStats:
        """Aggregate commander statistics."""
        return self._stats

    @property
    def is_running(self) -> bool:
        """``True`` while the commander's capture is active."""
        return self._running

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def listen(self, timeout: float = SILENCE_TIMEOUT) -> str:
        """Capture a single utterance from the microphone and transcribe it.

        This is the "hold-to-talk" entry point: records audio until silence
        (or *timeout*), then transcribes via the configured STT provider.

        Args:
            timeout: Seconds of silence before the utterance is considered
                complete (default 1.5). Pass 0.0 for manual controlled
                segment boundaries.

        Returns:
            The transcribed text string. An empty string is returned if no
            speech was detected or transcription produced an empty result.

        Raises:
            RuntimeError: If the capture is not running and starting it fails.
        """
        listen_start = time.monotonic()
        self._stats.total_listen_calls += 1

        # Ensure capture is running
        if not self._capture.is_running:
            try:
                self._capture.start()
                self._running = True
            except Exception as exc:
                self._stats.failures += 1
                raise RuntimeError(f"Failed to start audio capture: {exc}") from exc

        # Play "listening" sound if engine is configured
        if self._sound_engine is not None:
            self._sound_engine.on_event(HookEvent.AGENT_PAUSED)

        # Record utterance
        try:
            audio_data = record_utterance(
                self._capture,
                max_duration=MAX_UTTERANCE_DURATION,
                silence_timeout=timeout,
            )
        except Exception as exc:
            self._stats.failures += 1
            logger.warning("listen.capture_failed", error=str(exc))
            return ""

        if audio_data is None or len(audio_data) == 0:
            logger.debug("listen.no_speech_detected")
            return ""

        # Transcribe
        try:
            result: TranscriptionResult = await self._stt.transcribe(
                bytes(audio_data),
                sample_rate=LISTEN_SAMPLE_RATE,
            )
        except STTError as exc:
            self._stats.failures += 1
            logger.warning("listen.stt_failed", error=str(exc))
            return ""

        listen_duration_ms = (time.monotonic() - listen_start) * 1000
        self._stats.total_listen_duration_ms += listen_duration_ms

        logger.info(
            "listen.complete",
            text=result.text,
            language=result.language,
            latency_ms=round(listen_duration_ms, 1),
        )

        return result.text.strip()

    async def speak(
        self,
        text: str,
        voice_pack: str | None = None,
    ) -> None:
        """Synthesise and play back speech via TTS.

        Optionally plays voice pack sounds before and after the speech
        (e.g. a "thinking" chime before, a "success" chime after).

        Args:
            text: The text to speak aloud.
            voice_pack: Optional voice pack name to use for framing sounds.
                If ``None``, the active pack from the sound engine is used
                (or no sounds if no engine is configured).

        Raises:
            TTSError: If TTS synthesis fails.
        """
        self._stats.total_speak_calls += 1

        # Switch voice pack if requested
        if voice_pack is not None and self._sound_engine is not None:
            try:
                self._sound_engine.set_pack(voice_pack)
            except ValueError:
                logger.warning("speak.unknown_voice_pack", pack=voice_pack)

        # Optionally play "thinking" sound before speaking
        if self._sound_engine is not None:
            self._sound_engine.on_event(HookEvent.TOOL_CALL)

        # Synthesise
        try:
            tts_result = await self._tts.synthesize(text)
        except TTSError as exc:
            self._stats.failures += 1
            logger.warning("speak.tts_failed", error=str(exc))
            return

        # Play back the audio
        self._play_audio(tts_result)

        # Optionally play "complete" sound after speaking
        if self._sound_engine is not None:
            self._sound_engine.on_event(HookEvent.ANSWER_COMPLETE)

        logger.debug(
            "speak.complete",
            text_len=len(text),
            audio_len=len(tts_result.audio_data),
        )

    async def command(self, text: str) -> Command:
        """Parse a transcribed utterance into a structured ``Command``.

        Performs bilingual language detection, keyword matching, and
        argument extraction to classify the utterance as one of the
        recognised ``CommandType`` values.

        Args:
            text: The transcribed utterance text (may be VI, EN, or mixed).

        Returns:
            A ``Command`` with the parsed type, confidence, and extracted
            arguments.

        Raises:
            ValueError: If *text* is empty or whitespace-only.
        """
        if not text or not text.strip():
            raise ValueError("Cannot parse command from empty text")

        parse_start = time.monotonic()
        self._stats.total_commands += 1

        # 1. Detect language
        lang_result: LanguageResult = await self._detector.classify(text)
        language = lang_result.language

        if language == Language.VI:
            self._stats.vi_count += 1
        else:
            self._stats.en_count += 1

        # 2. Classify command type
        cmd_type, confidence, target, args = self._classify(text, language)

        if cmd_type != CommandType.UNKNOWN:
            self._stats.recognised_count += 1
        else:
            self._stats.unknown_count += 1

        command = Command(
            type=cmd_type,
            text=text,
            confidence=confidence,
            language=language,
            target=target,
            args=args,
        )

        parse_latency_ms = (time.monotonic() - parse_start) * 1000
        self._stats.total_parse_latency_ms += parse_latency_ms

        # Notify fleet callback if registered
        if self._fleet_notify is not None:
            try:
                self._fleet_notify(command)
            except Exception as exc:
                logger.warning("command.fleet_notify_failed", error=str(exc))

        logger.info(
            "command.parsed",
            type=cmd_type.value,
            language=language.value,
            confidence=round(confidence, 3),
            target=target,
            latency_ms=round(parse_latency_ms, 1),
        )

        return command

    def reset_stats(self) -> None:
        """Reset all commander statistics to zero."""
        self._stats = CommanderStats()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify(
        self,
        text: str,
        language: Language,
    ) -> tuple[CommandType, float, str | None, dict[str, str]]:
        """Classify a transcribed utterance into a ``CommandType``.

        Uses keyword matching against predefined command patterns.
        The matching is case-insensitive and supports Vietnamese command
        equivalents.

        Args:
            text: The utterance text.
            language: Detected language of the utterance.

        Returns:
            A tuple of ``(command_type, confidence, target, args)``.
        """
        lower = text.lower().strip()
        args: dict[str, str] = {}

        # Try each command keyword pattern in order of specificity.
        # Route-like commands: extract target agent name.
        agent_match = COMMAND_AGENT_NAME_RE.search(lower)
        if agent_match:
            target = agent_match.group(1)
            args["target_agent"] = target
            return CommandType.ROUTE_TO_AGENT, 0.85, target, args

        # Vietnamese equivalents for route commands.
        vi_route_patterns = [
            r"chuyển đến\s+([\w-]+)",
            r"đi đến\s+([\w-]+)",
            r"kết nối với\s+([\w-]+)",
            r"mở\s+([\w-]+)",
        ]
        for pattern in vi_route_patterns:
            m = re.search(pattern, lower)
            if m:
                target = m.group(1)
                args["target_agent"] = target
                return CommandType.ROUTE_TO_AGENT, 0.80, target, args

        # Status queries.
        status_keywords_en = {"status", "progress", "how are", "what's up", "what is the status"}
        status_keywords_vi = {"trạng thái", "tiến độ", "thế nào", "tình hình"}
        all_status = status_keywords_en | status_keywords_vi
        if any(kw in lower for kw in all_status):
            return CommandType.QUERY_STATUS, 0.70, None, args

        # Approval commands.
        approve_keywords_en = {"yes", "approve", "confirm", "do it", "go ahead", "proceed"}
        approve_keywords_vi = {"có", "đồng ý", "xác nhận", "tiến hành", "được"}
        if any(kw in lower for kw in approve_keywords_en | approve_keywords_vi):
            return CommandType.APPROVE_ACTION, 0.75, None, args

        # Denial commands.
        # Use word-boundary matching to prevent false positives
        # (e.g. "no" matching inside "enough").
        deny_keywords_en = {"no", "deny", "reject", "decline", "don't"}
        deny_keywords_vi = {"không", "từ chối"}
        for kw in deny_keywords_en | deny_keywords_vi:
            if re.search(rf"\b{re.escape(kw)}\b", lower):
                return CommandType.DENY_ACTION, 0.75, None, args

        # Interruption commands.
        interrupt_keywords_en = {"stop", "cancel", "interrupt", "halt", "abort", "pause", "enough"}
        interrupt_keywords_vi = {"dừng", "dừng lại", "hủy", "ngừng", "đủ rồi", "kết thúc"}
        if any(kw in lower for kw in interrupt_keywords_en | interrupt_keywords_vi):
            return CommandType.INTERRUPT, 0.80, None, args

        # No match found.
        return CommandType.UNKNOWN, 0.0, None, args

    def _play_audio(self, tts_result: Any) -> None:
        """Play back TTS audio data through the system speaker.

        Args:
            tts_result: A ``TTSResult`` with ``audio_data`` and
                ``sample_rate`` attributes.
        """
        try:
            import sounddevice as sd  # noqa: F811

            sd.play(
                tts_result.audio_data,
                samplerate=tts_result.sample_rate,
                blocking=True,
            )
        except ImportError:
            logger.warning("playback.sounddevice_not_available")
        except Exception as exc:
            logger.warning("playback.failed", error=str(exc))

    def __repr__(self) -> str:
        return (
            f"VoiceCommander(stt={type(self._stt).__name__}, "
            f"tts={type(self._tts).__name__}, "
            f"cmds={self._stats.total_commands})"
        )
