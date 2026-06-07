"""
Full-duplex voice handler -- simultaneous listen + speak with barge-in.

Implements the turn-taking state machine for full-duplex spoken dialogue.
Unlike cascaded half-duplex pipelines (listen -> think -> speak), the
full-duplex handler supports overlapping speech, barge-in, and semantic
endpointing.

The state machine has four states:

    LISTENING -> THINKING -> SPEAKING -> LISTENING ...
                                  |
                                  v
                              INTERRUPTED

Barge-in detection combines Voice Activity Detection (VAD) with **semantic
endpointing** (Smart Turn V3 pattern from Pipecat), distinguishing genuine
interruptions from noise, coughs, or filled pauses.

Echo cancellation stubs integrate WebRTC Acoustic Echo Cancellation (AEC)
at the capture stage, preventing the assistant's own speech from being
re-transcribed.

References:
    - Moshi (arXiv:2410.00037v2): Full-duplex multi-stream (17 streams),
      acoustic delay tau=1-2 for barge-in stability, 0.257 s interruption
      latency.
    - Full-Duplex-Bench (arXiv:2503.04721v3): 4-axis evaluation including
      Smooth Turn-Taking (TOR+Latency) and User Interruption
      (TOR+GPT-4o Score+Latency).
    - Full-Duplex-Bench-v3 (arXiv:2604.04847v1): 100 real-human recordings,
      5 disfluency categories, cascaded 100% turn-take reliability.
    - Pipecat (BSD 2-Clause): InterruptionFrame, Smart Turn V3 endpointing,
      UninterruptibleFrame marker.
"""

from __future__ import annotations

import asyncio
import structlog
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VAD_FRAME_MS: int = 20
"""Duration of each VAD analysis frame in milliseconds (Silero default)."""

VAD_HYSTERESIS_ENTRY: float = 0.5
"""VAD probability threshold to enter speech state (Silero default)."""

VAD_HYSTERESIS_EXIT: float = 0.35
"""VAD probability threshold to exit speech state."""

SEMANTIC_ENDPOINTING_TIMEOUT_MS: float = 300.0
"""Timeout in milliseconds for semantic endpointing after VAD silence."""

ECHO_CANCELLATION_FILTER_LENGTH_MS: int = 100
"""Default AEC filter length in milliseconds (WebRTC AEC spec)."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DuplexError(Exception):
    """Raised when the full-duplex handler encounters a runtime error."""


class BargeInError(DuplexError):
    """Raised when barge-in handling fails (e.g. buffer corruption)."""


class EchoCancellationError(DuplexError):
    """Raised when AEC processing fails."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TurnState(Enum):
    """Turn-taking state machine states.

    The normal cycle is: LISTENING -> THINKING -> SPEAKING -> LISTENING.

    INTERRUPTED is entered when the user barges in during SPEAKING.
    """

    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    INTERRUPTED = auto()


class BargeInType(Enum):
    """Classification of a barge-in event."""

    GENUINE = "genuine"
    """Intentional user interruption to correct, redirect, or take the floor."""

    NOISE = "noise"
    """Environmental noise (cough, door slam, etc.) that triggered VAD."""

    FILLED_PAUSE = "filled_pause"
    """User hesitation marker ("um", "uh", "like") that should not interrupt."""

    SELF_CORRECTION = "self_correction"
    """User self-correcting mid-utterance ("actually", "wait", "I mean...")."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioFrame:
    """A single 20 ms audio frame with optional VAD decision.

    Attributes:
        data: 16-bit mono PCM audio bytes.
        sample_rate: Sample rate in Hz (default 16000).
        timestamp_ms: Monotonic timestamp when captured.
        vad_probability: VAD speech probability (0.0 - 1.0), or -1 if
            VAD has not been applied yet.
        is_speech: Whether VAD classifies this as speech (based on
            hysteresis thresholds).
    """

    data: bytes
    sample_rate: int = 16000
    timestamp_ms: float = 0.0
    vad_probability: float = -1.0
    is_speech: bool = False


@dataclass(frozen=True)
class BargeInEvent:
    """Represents a detected barge-in event.

    Attributes:
        barge_in_type: Classification of the interruption.
        overlap_ms: Estimated duration of the overlap between assistant
            speech and user speech.
        user_audio: Captured audio of the user's interruption.
        assistant_stopped_at_ms: Wall-clock time when assistant speech
            was stopped.
        semantic_score: Semantic endpointing score (0.0 = noise,
            1.0 = definite user interruption).
    """

    barge_in_type: BargeInType
    overlap_ms: float = 0.0
    user_audio: bytes = b""
    assistant_stopped_at_ms: float = 0.0
    semantic_score: float = 0.0


@dataclass(frozen=True)
class TurnRecord:
    """Record of a complete turn in the dialogue.

    Attributes:
        state: The turn state when this record was created.
        user_text: Transcribed user utterance (if any).
        assistant_text: Assistant response text (if any).
        turn_start_ms: Monotonic timestamp when the turn started.
        turn_end_ms: Monotonic timestamp when the turn ended.
        interrupted: Whether the assistant's turn was interrupted.
        barge_in: The barge-in event, if interrupted.
        latency_ms: End-to-end latency for this turn.
    """

    state: TurnState
    user_text: str = ""
    assistant_text: str = ""
    turn_start_ms: float = 0.0
    turn_end_ms: float = 0.0
    interrupted: bool = False
    barge_in: BargeInEvent | None = None
    latency_ms: float = 0.0


@dataclass
class DuplexStats:
    """Aggregate statistics for the full-duplex handler.

    Attributes:
        total_turns: Total number of dialogue turns processed.
        total_interruptions: Number of barge-in events detected.
        genuine_interruptions: Number classified as GENUINE.
        noise_triggers: Number classified as NOISE (false positives).
        total_speech_ms: Total milliseconds of user speech processed.
        total_silence_ms: Total milliseconds of silence processed.
        turn_take_reliability: Ratio of successful turn transitions
            (excludes dropped turns due to errors).
    """

    total_turns: int = 0
    total_interruptions: int = 0
    genuine_interruptions: int = 0
    noise_triggers: int = 0
    total_speech_ms: float = 0.0
    total_silence_ms: float = 0.0
    turn_take_reliability: float = 1.0


# ---------------------------------------------------------------------------
# Echo Cancellation Stub
# ---------------------------------------------------------------------------


class AECProcessor:
    """WebRTC-style Acoustic Echo Cancellation stub.

    In production, this wraps ``webrtcvad`` + ``AudioProcessing`` from the
    WebRTC library.  The AEC filter removes the assistant's own audio
    output from the microphone input stream, preventing echo-based
    transcription loops.

    References:
        - WebRTC AudioProcessing spec:
          https://webrtc.googlesource.com/src/+/main/modules/audio_processing/
        - Moshi (arXiv:2410.00037v2): tau=1-2 acoustic delay prevents
          collapse during full-duplex operation.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        filter_length_ms: int = ECHO_CANCELLATION_FILTER_LENGTH_MS,
    ) -> None:
        """Initialise the AEC processor.

        Args:
            sample_rate: System sample rate in Hz.
            filter_length_ms: AEC filter length in milliseconds.
        """
        self._sample_rate = sample_rate
        self._filter_length = int(sample_rate * filter_length_ms / 1000)
        self._reference_buffer: list[bytes] = []

    def add_reference(self, audio_data: bytes) -> None:
        """Add assistant audio output as a reference for echo cancellation.

        The AEC uses this reference to subtract the known output signal
        from the microphone input.

        Args:
            audio_data: 16-bit mono PCM audio bytes of assistant output.
        """
        self._reference_buffer.append(audio_data)
        # Keep only the most recent filter-length worth of reference
        max_frames = max(1, self._filter_length // VAD_FRAME_MS)
        if len(self._reference_buffer) > max_frames * 2:
            self._reference_buffer = self._reference_buffer[-max_frames:]

    def process(self, mic_audio: bytes) -> bytes:
        """Apply AEC to microphone audio.

        In this stub implementation, the signal passes through unchanged.
        The production version will perform adaptive LMS-based echo
        subtraction using the reference buffer.

        Args:
            mic_audio: Raw microphone audio bytes (16-bit mono PCM).

        Returns:
            Echo-cancelled audio bytes.

        Raises:
            EchoCancellationError: If AEC processing fails.
        """
        if not mic_audio:
            raise EchoCancellationError("Empty mic audio provided to AEC")

        # Stub: pass through unchanged.  In production, this would:
        #   1. Align reference buffer with mic signal.
        #   2. Apply adaptive NLMS filter.
        #   3. Subtract estimated echo from mic signal.
        #   4. Apply residual echo suppression (RES).
        return mic_audio

    def reset(self) -> None:
        """Reset the AEC state (e.g. on device change)."""
        self._reference_buffer.clear()


# ---------------------------------------------------------------------------
# Semantic Endpointer
# ---------------------------------------------------------------------------


class SemanticEndpointer:
    """Smart Turn V3-style semantic endpointing.

    Distinguishes genuine turn-taking signals from noise, filled pauses,
    and self-corrections.  Uses a combination of:
      - VAD silence detection (hardware-level).
      - Semantic scoring (classifier that distinguishes interruption types).
      - Temporal context (pause duration, speaking rate, prosodic cues).

    References:
        - Pipecat (BSD 2-Clause): Smart Turn V3 endpointing.
        - Full-Duplex-Bench (arXiv:2503.04721v3): TOR metrics for
          turn-taking reliability.
    """

    def __init__(
        self,
        silence_timeout_ms: float = SEMANTIC_ENDPOINTING_TIMEOUT_MS,
    ) -> None:
        """Initialise the semantic endpointer.

        Args:
            silence_timeout_ms: Silence duration threshold for endpointing.
        """
        self._silence_timeout_ms = silence_timeout_ms
        self._silence_start_ms: float | None = None

    def classify_barge_in(
        self,
        user_audio: bytes,
        vad_probability: float,
        pause_duration_ms: float,
        text_prefix: str | None = None,
    ) -> BargeInEvent:
        """Classify a potential barge-in event.

        Args:
            user_audio: Captured user audio bytes.
            vad_probability: VAD speech probability for this segment.
            pause_duration_ms: Duration of silence before the interruption.
            text_prefix: Optional partial ASR text for semantic analysis.

        Returns:
            A ``BargeInEvent`` with the classified type and semantic score.
        """
        # Determine barge-in type based on available signals
        now_ms = time.monotonic() * 1000

        if text_prefix:
            barge_in_type = self._classify_by_text(text_prefix)
        elif pause_duration_ms < 200:
            # Very short silence before VAD trigger -- likely filled pause
            # or self-correction rather than a genuine turn-take
            barge_in_type = BargeInType.FILLED_PAUSE
        elif vad_probability < VAD_HYSTERESIS_ENTRY:
            barge_in_type = BargeInType.NOISE
        else:
            barge_in_type = BargeInType.GENUINE

        # Semantic score: heuristic based on features
        semantic_score = self._compute_semantic_score(
            barge_in_type, vad_probability, pause_duration_ms, text_prefix
        )

        return BargeInEvent(
            barge_in_type=barge_in_type,
            overlap_ms=now_ms,  # placeholder; real impl uses cross-correlation
            user_audio=user_audio,
            assistant_stopped_at_ms=now_ms,
            semantic_score=semantic_score,
        )

    def on_silence_start(self, timestamp_ms: float) -> None:
        """Record the start of a silence period.

        Args:
            timestamp_ms: Monotonic timestamp when silence began.
        """
        self._silence_start_ms = timestamp_ms

    def on_silence_ended(self, timestamp_ms: float) -> float:
        """Record the end of a silence period and return its duration.

        Args:
            timestamp_ms: Monotonic timestamp when silence ended.

        Returns:
            Silence duration in milliseconds.
        """
        if self._silence_start_ms is not None:
            duration = timestamp_ms - self._silence_start_ms
            self._silence_start_ms = None
            return duration
        return 0.0

    def should_end_turn(self, silence_duration_ms: float) -> bool:
        """Determine whether the current turn should end.

        Args:
            silence_duration_ms: Duration of the current silence period.

        Returns:
            ``True`` if silence exceeds the timeout threshold.
        """
        return silence_duration_ms >= self._silence_timeout_ms

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_by_text(self, text: str) -> BargeInType:
        """Classify barge-in type based on partial ASR text.

        Examines the partial transcript for keywords that indicate
        self-correction ("actually", "wait", "I mean"), filled pauses
        ("um", "uh"), or genuine interruption (full intent-bearing words).
        """
        lower = text.lower().strip()

        # Self-correction keywords (FDB-v3 categories)
        self_correction_markers = {
            "actually", "wait", "no", "i mean", "correction",
            "rather", "instead", "let me", "hold on",
        }
        if any(marker in lower for marker in self_correction_markers):
            return BargeInType.SELF_CORRECTION

        # Filled pause markers
        filled_pause_markers = {"um", "uh", "er", "ah", "like", "hmm", "mm"}
        words = lower.split()
        if any(marker in words for marker in filled_pause_markers):
            return BargeInType.FILLED_PAUSE

        # Short utterances are likely noise or non-intentional
        if len(words) <= 1 and len(lower) < 5:
            return BargeInType.NOISE

        return BargeInType.GENUINE

    def _compute_semantic_score(
        self,
        barge_type: BargeInType,
        vad_prob: float,
        pause_ms: float,
        text_prefix: str | None,
    ) -> float:
        """Compute a semantic endpointing score (0.0 - 1.0).

        Higher scores indicate higher confidence that this is a genuine
        interruption requiring a turn transition.
        """
        # Base score from classification
        base_scores = {
            BargeInType.GENUINE: 0.85,
            BargeInType.SELF_CORRECTION: 0.60,
            BargeInType.FILLED_PAUSE: 0.30,
            BargeInType.NOISE: 0.05,
        }
        score = base_scores.get(barge_type, 0.0)

        # Modulate by VAD confidence
        score *= min(1.0, max(0.0, vad_prob))

        # Modulate by pause duration -- very short pauses suggest continuation
        if pause_ms < 100:
            score *= 0.5
        elif pause_ms > 500:
            score *= 1.2  # Longer pause = more likely genuine turn attempt

        # Text-based boost
        if text_prefix and len(text_prefix.strip()) > 10:
            score = min(1.0, score * 1.3)

        return min(1.0, max(0.0, score))


# ---------------------------------------------------------------------------
# FullDuplexHandler
# ---------------------------------------------------------------------------


class FullDuplexHandler:
    """Full-duplex handler with simultaneous listen + speak.

    Manages the turn-taking state machine and coordinates:
      - Audio capture and VAD.
      - AEC (echo cancellation).
      - Semantic endpointing.
      - Barge-in detection and handling.
      - Turn state transitions.

    Usage::

        handler = FullDuplexHandler()
        async for turn in handler.run_loop():
            if turn.state == TurnState.LISTENING:
                await process_user_input(turn.user_text)
            elif turn.state == TurnState.SPEAKING:
                await play_assistant_response(turn.assistant_text)

    References:
        - Moshi (arXiv:2410.00037v2): Acoustic delay tau=1-2 for
          full-duplex stability, 0.257 s interruption latency.
        - FDB-v3 (arXiv:2604.04847v1): 100% turn-take reliability for
          cascaded pipelines, 96% for GPT-Realtime.
        - Pipecat (BSD 2-Clause): InterruptionFrame, Smart Turn V3
          endpointing, UninterruptibleFrame marker.
    """

    def __init__(
        self,
        aec: AECProcessor | None = None,
        endpointer: SemanticEndpointer | None = None,
        vad_provider: Callable[[bytes], float] | None = None,
        on_state_change: Callable[[TurnState], None] | None = None,
    ) -> None:
        """Initialise the full-duplex handler.

        Args:
            aec: Echo cancellation processor.  If ``None``, a default
                ``AECProcessor`` is created.
            endpointer: Semantic endpointer.  If ``None``, a default
                ``SemanticEndpointer`` is created.
            vad_provider: Optional VAD function that takes raw audio bytes
                and returns a speech probability (0.0 - 1.0).
            on_state_change: Optional callback invoked on every state
                transition (useful for logging or UI updates).
        """
        self._aec = aec or AECProcessor()
        self._endpointer = endpointer or SemanticEndpointer()
        self._vad_provider = vad_provider or self._default_vad
        self._on_state_change = on_state_change

        # State machine
        self._state: TurnState = TurnState.LISTENING
        self._stats = DuplexStats()
        self._current_turn: TurnRecord | None = None
        self._turn_history: list[TurnRecord] = []

        # Buffers
        self._user_buffer: list[bytes] = []
        self._silence_duration_ms: float = 0.0
        self._last_frame_time_ms: float = 0.0

        # Assistant speech control
        self._assistant_speaking: bool = False
        self._interrupt_requested: bool = False

        logger.info("duplex.handler.started", state=self._state.name)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> TurnState:
        """Current turn-taking state."""
        return self._state

    @property
    def stats(self) -> DuplexStats:
        """Aggregate handler statistics."""
        return self._stats

    @property
    def turn_history(self) -> list[TurnRecord]:
        """History of completed turning records."""
        return list(self._turn_history)

    # ------------------------------------------------------------------
    # State machine transitions
    # ------------------------------------------------------------------

    def transition_to(self, new_state: TurnState) -> None:
        """Transition the state machine to *new_state*.

        Args:
            new_state: The target state.

        Raises:
            DuplexError: If the transition is invalid from the current state.
        """
        old_state = self._state
        self._validate_transition(old_state, new_state)
        self._state = new_state
        logger.debug(
            "duplex.state_transition",
            old=old_state.name,
            new=new_state.name,
        )

        # Create or update turn record
        now_ms = time.monotonic() * 1000
        if self._current_turn is not None:
            # noqa: SIM113 -- explicit field update for frozen dataclass
            self._turn_history.append(
                TurnRecord(
                    state=old_state,
                    user_text=self._current_turn.user_text,
                    assistant_text=self._current_turn.assistant_text,
                    turn_start_ms=self._current_turn.turn_start_ms,
                    turn_end_ms=now_ms,
                    interrupted=self._current_turn.interrupted,
                    barge_in=self._current_turn.barge_in,
                    latency_ms=now_ms - self._current_turn.turn_start_ms,
                )
            )

        self._current_turn = TurnRecord(
            state=new_state,
            turn_start_ms=now_ms,
        )

        if new_state == TurnState.LISTENING:
            self._stats.total_turns += 1
            self._assistant_speaking = False
            self._interrupt_requested = False

        if self._on_state_change:
            self._on_state_change(new_state)

    @staticmethod
    def _validate_transition(current: TurnState, target: TurnState) -> None:
        """Validate a state transition.

        Valid transitions:
          - LISTENING -> THINKING  (user finished speaking)
          - THINKING  -> SPEAKING  (assistant response ready)
          - SPEAKING  -> LISTENING (assistant finished)
          - SPEAKING  -> INTERRUPTED (user barged in)
          - INTERRUPTED -> LISTENING (handling complete)
          - Any -> same state (no-op transition)
        """
        if current == target:
            return

        allowed: dict[TurnState, set[TurnState]] = {
            TurnState.LISTENING: {TurnState.THINKING},
            TurnState.THINKING: {TurnState.SPEAKING},
            TurnState.SPEAKING: {TurnState.LISTENING, TurnState.INTERRUPTED},
            TurnState.INTERRUPTED: {TurnState.LISTENING},
        }

        valid_targets = allowed.get(current, set())
        if target not in valid_targets:
            raise DuplexError(
                f"Invalid state transition: {current.name} -> {target.name}. "
                f"Allowed from {current.name}: "
                f"{[s.name for s in valid_targets] or '(none)'}"
            )

    # ------------------------------------------------------------------
    # VAD helper
    # ------------------------------------------------------------------

    @staticmethod
    def _default_vad(audio_data: bytes) -> float:
        """Minimal VAD heuristic for when no real VAD is configured.

        Returns a speech probability based on RMS energy, which is a
        rough proxy for VAD.  In production, use Silero VAD or WebRTC VAD.
        """
        if not audio_data or len(audio_data) < 2:
            return 0.0

        import struct

        # Compute RMS of 16-bit PCM samples
        sample_count = len(audio_data) // 2
        total = 0.0
        for i in range(sample_count):
            sample = struct.unpack_from("<h", audio_data, i * 2)[0]
            total += sample * sample

        rms = (total / max(1, sample_count)) ** 0.5
        # Normalise to 0.0 - 1.0 based on typical 16-bit range
        return min(1.0, rms / 8000.0)

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    async def feed_audio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
    ) -> None:
        """Feed an incoming audio frame into the handler.

        This is the primary tick method.  VAD and semantic endpointing
        run synchronously on each frame.

        Args:
            audio_data: 16-bit mono PCM audio bytes (typically 20 ms
                frame).
            sample_rate: Audio sample rate in Hz.

        Raises:
            DuplexError: If the handler is not in a listening state.
        """
        if self._state not in (TurnState.LISTENING, TurnState.SPEAKING):
            return  # No-op when thinking

        now_ms = time.monotonic() * 1000

        # Apply AEC if assistant is speaking
        if self._assistant_speaking:
            audio_data = self._aec.process(audio_data)

        # Run VAD
        vad_prob = self._vad_provider(audio_data)
        is_speech = vad_prob >= VAD_HYSTERESIS_ENTRY

        # Track speech/silence durations
        if is_speech:
            self._stats.total_speech_ms += VAD_FRAME_MS
            self._silence_duration_ms = 0.0
        else:
            self._stats.total_silence_ms += VAD_FRAME_MS
            self._silence_duration_ms += VAD_FRAME_MS

        # Handle barge-in detection during assistant speech
        if self._state == TurnState.SPEAKING and is_speech:
            self._user_buffer.append(audio_data)
            # Check if this is a genuine barge-in
            if self._silence_duration_ms < 100:
                barge_event = self._endpointer.classify_barge_in(
                    user_audio=b"".join(self._user_buffer),
                    vad_probability=vad_prob,
                    pause_duration_ms=self._silence_duration_ms,
                )
                if barge_event.barge_in_type in (
                    BargeInType.GENUINE,
                    BargeInType.SELF_CORRECTION,
                ):
                    self._on_barge_in(barge_event)

        # Buffer user speech during LISTENING
        if self._state == TurnState.LISTENING and is_speech:
            self._user_buffer.append(audio_data)

        # Handle silence during LISTENING (end-of-turn detection)
        if self._state == TurnState.LISTENING and not is_speech:
            if self._user_buffer and self._silence_duration_ms >= 200:
                if self._endpointer.should_end_turn(self._silence_duration_ms):
                    # Wait for ASR before transitioning, but signal readiness
                    pass  # Transition happens in handle_user_speech()

    def _on_barge_in(self, event: BargeInEvent) -> None:
        """Handle a detected barge-in event.

        Args:
            event: The classified barge-in event.
        """
        self._interrupt_requested = True
        self._stats.total_interruptions += 1

        if event.barge_in_type == BargeInType.GENUINE:
            self._stats.genuine_interruptions += 1
        else:
            self._stats.noise_triggers += 1

        logger.info(
            "duplex.barge_in",
            barge_type=event.barge_in_type.value,
            semantic_score=round(event.semantic_score, 3),
        )

        # Transition to INTERRUPTED
        self.transition_to(TurnState.INTERRUPTED)

        # Transfer user buffer to current turn record
        if self._current_turn is not None:
            self._turn_history.append(
                TurnRecord(
                    state=TurnState.INTERRUPTED,
                    user_text=event.barge_in_type.value,
                    turn_start_ms=self._current_turn.turn_start_ms,
                    turn_end_ms=event.assistant_stopped_at_ms,
                    interrupted=True,
                    barge_in=event,
                    latency_ms=event.assistant_stopped_at_ms
                    - self._current_turn.turn_start_ms,
                )
            )

        # Resume listening
        self._state = TurnState.LISTENING

    def request_interruption(self) -> None:
        """Request an interruption of assistant speech.

        Can be called externally (e.g. from a VAD callback) to trigger
        barge-in without going through the audio feed path.
        """
        if self._state != TurnState.SPEAKING:
            return
        self._interrupt_requested = True

        event = BargeInEvent(
            barge_in_type=BargeInType.GENUINE,
            assistant_stopped_at_ms=time.monotonic() * 1000,
            semantic_score=0.9,
        )
        self._on_barge_in(event)

    async def handle_user_speech(
        self,
        transcription_result: str,
    ) -> None:
        """Handle a completed user utterance after transcription.

        Should be called by the pipeline when ASR produces a final
        transcription for the buffered user audio.

        Args:
            transcription_result: The transcribed user text.

        Raises:
            DuplexError: If called in the wrong state.
        """
        if self._state != TurnState.LISTENING:
            raise DuplexError(
                f"Cannot handle user speech in {self._state.name} state; "
                f"expected LISTENING"
            )

        # Flush the user buffer
        user_audio = b"".join(self._user_buffer)
        self._user_buffer.clear()

        # Emit the speaking signal
        self._assistant_speaking = True

        # Record transcription in current turn
        if self._current_turn is not None:
            self._turn_history.append(
                TurnRecord(
                    state=TurnState.LISTENING,
                    user_text=transcription_result,
                    turn_start_ms=self._current_turn.turn_start_ms,
                    turn_end_ms=time.monotonic() * 1000,
                    latency_ms=(time.monotonic() * 1000)
                    - self._current_turn.turn_start_ms,
                )
            )

    async def start_assistant_speech(self) -> None:
        """Signal that the assistant has started speaking.

        Should be called by the pipeline when TTS playback begins.
        """
        self.transition_to(TurnState.SPEAKING)

    async def end_assistant_speech(self) -> None:
        """Signal that the assistant has finished speaking.

        Should be called by the pipeline when TTS playback completes.
        """
        self._assistant_speaking = False
        self.transition_to(TurnState.LISTENING)

    def should_interrupt(self) -> bool:
        """Check whether assistant speech should be interrupted.

        Returns:
            ``True`` if a barge-in has been detected and the assistant
            should stop speaking.
        """
        return self._interrupt_requested

    def reset(self) -> None:
        """Reset the handler to its initial state."""
        self._state = TurnState.LISTENING
        self._stats = DuplexStats()
        self._current_turn = None
        self._user_buffer.clear()
        self._silence_duration_ms = 0.0
        self._assistant_speaking = False
        self._interrupt_requested = False
        self._aec.reset()
        logger.info("duplex.handler.reset")

    # ------------------------------------------------------------------
    # Async run loop
    # ------------------------------------------------------------------

    async def run_loop(self) -> AsyncIterator[TurnRecord]:
        """Run the full-duplex handler as an async generator.

        Yields ``TurnRecord`` instances as turns complete.  The caller
        processes each turn and feeds new audio via ``feed_audio()``.

        Example::

            handler = FullDuplexHandler()
            async for turn in handler.run_loop():
                if turn.state == TurnState.SPEAKING:
                    await tts_provider.synthesize(turn.assistant_text)
        """
        # This loop is intentionally simple -- the real processing happens
        # in the pipeline which calls feed_audio(), handle_user_speech(),
        # and start_assistant_speech().
        #
        # The async generator pattern allows the pipeline to yield turns
        # as they complete without requiring an external queue.
        while True:
            if self._turn_history:
                turn = self._turn_history.pop(0)
                yield turn
            else:
                await asyncio.sleep(0.01)
