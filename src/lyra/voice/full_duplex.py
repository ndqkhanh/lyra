"""
Full-duplex voice engine -- simultaneous listen+speak with barge-in detection,
turn-taking policy, and acoustic echo cancellation.

Provides the next-generation full-duplex experience for v9.0 where the user
and assistant can speak simultaneously without hold-to-talk constraints.

Components::

    FullDuplexEngine
    ├── BargeInDetector     -- detect user interruption mid-assistant-speech
    ├── TurnTakingPolicy    -- when the agent should speak vs listen
    ├── ConversationState   -- state machine: IDLE, LISTENING, THINKING,
    │                          SPEAKING, INTERRUPTED
    └── EchoCancellation    -- basic software AEC (acoustic echo cancellation)

Latency budget: < 500 ms end-to-end for interruption detection.

References:
    - Moshi (arXiv:2410.00037v2): Full-duplex multi-stream architecture,
      acoustic delay tau=1-2, 0.257 s interruption latency.
    - Full-Duplex-Bench-v3 (arXiv:2604.04847v1): 4-axis evaluation,
      100 real-human recordings, 5 disfluency categories.
    - Pipecat (BSD 2-Clause): Smart Turn V3, InterruptionFrame.
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTERRUPTION_LATENCY_BUDGET_MS: float = 500.0
"""Maximum end-to-end latency budget for interruption detection in ms."""

VAD_FRAME_MS: int = 20
"""Duration of each VAD analysis frame in milliseconds."""

AEC_FILTER_LENGTH_MS: int = 100
"""Default AEC filter length in milliseconds."""

DEFAULT_SAMPLE_RATE: int = 16000
"""Default audio sample rate."""

SILENCE_TIMEOUT_MS: float = 600.0
"""Silence duration before a turn transition is considered complete."""

BARGE_IN_COOLDOWN_MS: float = 300.0
"""Minimum gap between consecutive barge-in events to avoid thrashing."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FullDuplexError(Exception):
    """Raised when the full-duplex engine encounters a runtime error."""


class BargeInDetectionError(FullDuplexError):
    """Raised when barge-in detection fails."""


# ---------------------------------------------------------------------------
# Conversation State Machine
# ---------------------------------------------------------------------------


class ConversationState(Enum):
    """Finite states for the conversation loop.

    Normal cycle::

        IDLE -> LISTENING -> THINKING -> SPEAKING -> LISTENING ...
                                          |
                                          v
                                      INTERRUPTED -> LISTENING

    * ``IDLE``         -- Engine initialised, no conversation active.
    * ``LISTENING``    -- Capturing user audio, waiting for a complete utterance.
    * ``THINKING``     -- Processing user input, generating a response.
    * ``SPEAKING``     -- Assistant is speaking via TTS output.
    * ``INTERRUPTED``  -- User barged in during SPEAKING; handling handover.
    """

    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()
    INTERRUPTED = auto()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BargeInEvent:
    """A detected user interruption during assistant speech.

    Attributes:
        detected_at_ms: Monotonic timestamp when the interruption was detected.
        confidence: Detection confidence (0.0 - 1.0).
        energy_level: RMS energy of the interrupting audio.
        audio_frames: Raw PCM frames of the interruption segment.
    """

    detected_at_ms: float
    confidence: float = 0.0
    energy_level: float = 0.0
    audio_frames: bytes = b""


@dataclass(frozen=True)
class TurnSegment:
    """A segment of audio within a conversation turn.

    Attributes:
        audio: PCM audio data (16-bit mono).
        sample_rate: Sample rate in Hz.
        timestamp_ms: Monotonic capture timestamp.
        is_speech: Whether this segment contains speech.
    """

    audio: bytes
    sample_rate: int = DEFAULT_SAMPLE_RATE
    timestamp_ms: float = 0.0
    is_speech: bool = False


@dataclass
class DuplexEngineStats:
    """Aggregate statistics for the full-duplex engine.

    Attributes:
        total_turns: Total number of conversation turns.
        total_barge_ins: Total barge-in events detected.
        genuine_barge_ins: Classified as genuine interruptions.
        false_triggers: False positive barge-in triggers (noise).
        total_interruption_latency_ms: Sum of all interruption latencies.
        avg_interruption_latency_ms: Average interruption latency.
        total_turn_duration_ms: Sum of all turn durations.
        state_transitions: Number of state transitions performed.
    """

    total_turns: int = 0
    total_barge_ins: int = 0
    genuine_barge_ins: int = 0
    false_triggers: int = 0
    total_interruption_latency_ms: float = 0.0
    avg_interruption_latency_ms: float = 0.0
    total_turn_duration_ms: float = 0.0
    state_transitions: int = 0


# ---------------------------------------------------------------------------
# Echo Cancellation (AEC)
# ---------------------------------------------------------------------------


class EchoCancellation:
    """Basic software Acoustic Echo Cancellation (AEC).

    Uses a reference buffer of the assistant's output audio to estimate and
    cancel the echo signal in the microphone input.  This implementation is a
    pedagogical stub that applies a normalised LMS-style subtraction.

    In production, replace with the WebRTC AudioProcessing module or
    SpeexDSP for real NLMS adaptive filtering.
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        filter_length_ms: int = AEC_FILTER_LENGTH_MS,
        adaptation_rate: float = 0.01,
    ) -> None:
        """Initialise the echo canceller.

        Args:
            sample_rate: System sample rate in Hz.
            filter_length_ms: AEC filter length in milliseconds.
            adaptation_rate: NLMS adaptation step size (0.0 - 1.0).
        """
        self._sample_rate = sample_rate
        self._filter_taps = sample_rate * filter_length_ms // 1000
        self._adaptation_rate = adaptation_rate
        self._reference_buffer: deque[bytes] = deque(maxlen=50)
        self._filter_coeffs: list[float] = [0.0] * max(1, self._filter_taps)

    def add_reference(self, audio_data: bytes) -> None:
        """Add assistant output audio as a reference for echo cancellation.

        Args:
            audio_data: 16-bit mono PCM audio bytes of assistant output.
        """
        self._reference_buffer.append(audio_data)

    def process(self, mic_audio: bytes) -> bytes:
        """Apply acoustic echo cancellation to microphone audio.

        Performs a simple NLMS-style echo subtraction.  If no reference
        signal is available, the audio passes through unchanged.

        Args:
            mic_audio: Raw microphone audio bytes (16-bit mono PCM).

        Returns:
            Echo-cancelled audio bytes.

        Raises:
            FullDuplexError: If mic_audio is empty.
        """
        if not mic_audio:
            raise FullDuplexError("Empty mic audio provided to AEC")

        if not self._reference_buffer:
            return mic_audio  # Pass through when no reference is available

        # Build a reference signal from the recent output buffer
        ref_signal = b"".join(self._reference_buffer)
        ref_samples = self._samples_from_bytes(ref_signal)
        mic_samples = self._samples_from_bytes(mic_audio)

        if not ref_samples or not mic_samples:
            return mic_audio

        # Simple NLMS echo subtraction on the last N samples
        min_len = min(len(mic_samples), len(ref_samples), self._filter_taps)
        output = list(mic_samples[:min_len])
        ref_part = ref_samples[:min_len]

        for i in range(min_len):
            # NLMS update
            norm_factor = sum(r * r for r in ref_part) / max(1, min_len)
            if norm_factor > 1e-6:
                error = output[i]
                for j in range(min_len):
                    self._filter_coeffs[j] += (
                        self._adaptation_rate * error * ref_part[j] / norm_factor
                    )
                # Subtract estimated echo
                echo_estimate = sum(
                    self._filter_coeffs[j] * ref_part[j]
                    for j in range(min(min_len, len(self._filter_coeffs)))
                )
                output[i] = max(-32768, min(32767, int(mic_samples[i] - echo_estimate)))

        return self._bytes_from_samples(output)

    def reset(self) -> None:
        """Reset the AEC state (e.g. on device change)."""
        self._reference_buffer.clear()
        self._filter_coeffs = [0.0] * max(1, self._filter_taps)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _samples_from_bytes(audio: bytes) -> list[int]:
        """Convert 16-bit mono PCM bytes to a list of signed integers."""
        count = len(audio) // 2
        return [struct.unpack_from("<h", audio, i * 2)[0] for i in range(count)]

    @staticmethod
    def _bytes_from_samples(samples: list[int]) -> bytes:
        """Convert a list of signed integers to 16-bit mono PCM bytes."""
        return struct.pack(f"<{len(samples)}h", *samples)


# ---------------------------------------------------------------------------
# Barge-In Detector
# ---------------------------------------------------------------------------


class BargeInDetector:
    """Detect user interruption mid-assistant-speech.

    Monitors incoming audio frames during SPEAKING state and uses a
    combination of VAD energy thresholds and temporal patterns to
    distinguish genuine interruptions from noise, coughs, or hesitation.

    Design goals:
      - Sub-500 ms end-to-end detection latency.
      - Low false-positive rate for non-speech sounds.
      - Configurable sensitivity per use case.
    """

    def __init__(
        self,
        energy_threshold: float = 800.0,
        min_interruption_ms: float = 120.0,
        cooldown_ms: float = BARGE_IN_COOLDOWN_MS,
        vad_provider: Callable[[bytes], float] | None = None,
    ) -> None:
        """Initialise the barge-in detector.

        Args:
            energy_threshold: RMS energy threshold for speech detection.
            min_interruption_ms: Minimum duration of speech-like audio to
                classify as a genuine interruption.
            cooldown_ms: Minimum gap between consecutive barge-in events.
            vad_provider: Optional VAD function returning speech probability
                (0.0 - 1.0).  If None, uses RMS-based energy detection.
        """
        self._energy_threshold = energy_threshold
        self._min_interruption_ms = min_interruption_ms
        self._cooldown_ms = cooldown_ms
        self._vad_provider = vad_provider or self._default_vad

        self._last_barge_in_ms: float = 0.0
        self._speech_frames: list[bytes] = []
        self._speech_start_ms: float = 0.0
        self._detection_start_ms: float = 0.0

    def feed_frame(self, audio_data: bytes, timestamp_ms: float) -> BargeInEvent | None:
        """Feed an audio frame captured during assistant speech.

        Args:
            audio_data: 16-bit mono PCM audio bytes (typically 20 ms frame).
            timestamp_ms: Monotonic timestamp of the frame.

        Returns:
            A ``BargeInEvent`` if a barge-in is detected, ``None`` otherwise.
        """
        # Check cooldown
        if timestamp_ms - self._last_barge_in_ms < self._cooldown_ms:
            if self._speech_frames:
                self._speech_frames.clear()
            return None

        vad_prob = self._vad_provider(audio_data)
        is_speech = vad_prob >= 0.5

        if not is_speech:
            self._speech_frames.clear()
            self._speech_start_ms = 0.0
            return None

        # Speech detected
        if not self._speech_frames:
            self._speech_start_ms = timestamp_ms
            self._detection_start_ms = time.monotonic() * 1000

        self._speech_frames.append(audio_data)

        # Check if speech duration exceeds minimum interruption threshold
        elapsed_ms = timestamp_ms - self._speech_start_ms
        if elapsed_ms >= self._min_interruption_ms:
            event = self._create_barge_in_event()
            self._last_barge_in_ms = timestamp_ms
            self._speech_frames.clear()
            self._speech_start_ms = 0.0
            elapsed_detection = (time.monotonic() * 1000) - self._detection_start_ms
            if elapsed_detection > INTERRUPTION_LATENCY_BUDGET_MS:
                logger.warning(
                    "barge_in.latency_exceeded_budget",
                    actual_ms=round(elapsed_detection, 1),
                    budget_ms=INTERRUPTION_LATENCY_BUDGET_MS,
                )
            return event

        return None

    def reset(self) -> None:
        """Reset the detector state."""
        self._last_barge_in_ms = 0.0
        self._speech_frames.clear()
        self._speech_start_ms = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_barge_in_event(self) -> BargeInEvent:
        """Create a BargeInEvent from accumulated speech frames."""
        audio = b"".join(self._speech_frames)
        rms = self._compute_rms(audio)
        now_ms = time.monotonic() * 1000
        return BargeInEvent(
            detected_at_ms=now_ms,
            confidence=min(1.0, rms / 8000.0),
            energy_level=rms,
            audio_frames=audio,
        )

    @staticmethod
    def _compute_rms(audio: bytes) -> float:
        """Compute RMS energy of PCM audio."""
        if not audio or len(audio) < 2:
            return 0.0
        count = len(audio) // 2
        total = 0.0
        for i in range(count):
            sample = struct.unpack_from("<h", audio, i * 2)[0]
            total += sample * sample
        return (total / max(1, count)) ** 0.5

    @staticmethod
    def _default_vad(audio_data: bytes) -> float:
        """Default VAD: RMS-based energy detection."""
        if not audio_data or len(audio_data) < 2:
            return 0.0
        count = len(audio_data) // 2
        total = 0.0
        for i in range(count):
            sample = struct.unpack_from("<h", audio_data, i * 2)[0]
            total += sample * sample
        rms = (total / max(1, count)) ** 0.5
        return min(1.0, rms / 8000.0)


# ---------------------------------------------------------------------------
# Turn-Taking Policy
# ---------------------------------------------------------------------------


class TurnTakingPolicy:
    """Policy engine for when the agent should speak vs listen.

    Uses a combination of:
      - Silence duration (how long the user has been quiet).
      - Barge-in events (user interruption).
      - Utterance completion heuristics (semantic endpointing).
      - Configurable aggressiveness for different use cases.
    """

    class Aggressiveness(Enum):
        """How eagerly the agent takes the turn.

        * ``PATIENT``   -- Wait for clear silence + utterance completion.
        * ``BALANCED``  -- Moderate turn-taking (default).
        * ``EAGER``     -- Jump in early, suitable for fast-paced dialogue.
        """

        PATIENT = "patient"
        BALANCED = "balanced"
        EAGER = "eager"

    def __init__(
        self,
        aggressiveness: Aggressiveness = Aggressiveness.BALANCED,
        silence_timeout_ms: float = SILENCE_TIMEOUT_MS,
        min_utterance_ms: float = 300.0,
        barge_in_grace_ms: float = 200.0,
    ) -> None:
        """Initialise the turn-taking policy.

        Args:
            aggressiveness: Turn-taking aggressiveness level.
            silence_timeout_ms: Silence duration before the agent speaks.
            min_utterance_ms: Minimum user utterance duration to consider valid.
            barge_in_grace_ms: Grace period after barge-in before yielding.
        """
        self._aggressiveness = aggressiveness
        self._silence_timeout_ms = silence_timeout_ms
        self._min_utterance_ms = min_utterance_ms
        self._barge_in_grace_ms = barge_in_grace_ms

        # Compute effective silence timeout based on aggressiveness
        factor = {
            self.Aggressiveness.PATIENT: 1.5,
            self.Aggressiveness.BALANCED: 1.0,
            self.Aggressiveness.EAGER: 0.5,
        }
        self._effective_silence_timeout_ms = (
            silence_timeout_ms * factor.get(aggressiveness, 1.0)
        )

    @property
    def aggressiveness(self) -> Aggressiveness:
        """Current aggressiveness level."""
        return self._aggressiveness

    def should_speak(
        self,
        silence_duration_ms: float,
        is_barge_in: bool,
        utterance_duration_ms: float,
        is_utterance_complete: bool,
    ) -> tuple[bool, float]:
        """Determine whether the agent should start speaking.

        Args:
            silence_duration_ms: Current silence duration since last speech.
            is_barge_in: Whether a barge-in just occurred.
            utterance_duration_ms: Duration of the last user utterance.
            is_utterance_complete: Whether the semantic endpointer considers
                the utterance complete.

        Returns:
            A tuple of ``(should_speak, confidence)`` where confidence is
            a value between 0.0 and 1.0.
        """
        # Barge-in means the user wants to speak -- agent should not
        if is_barge_in and silence_duration_ms < self._barge_in_grace_ms:
            return False, 0.0

        # Utterance too short -- likely not intentional
        if utterance_duration_ms < self._min_utterance_ms:
            return False, 0.1

        # Utterance complete + sufficient silence = agent should take turn
        if is_utterance_complete and silence_duration_ms >= self._effective_silence_timeout_ms:
            confidence = min(
                1.0,
                (silence_duration_ms / self._effective_silence_timeout_ms) * 0.5 + 0.5,
            )
            return True, confidence

        # Partial utterance but long silence -- agent may prompt
        if (
            self._aggressiveness == self.Aggressiveness.EAGER
            and silence_duration_ms >= self._effective_silence_timeout_ms * 2
        ):
            return True, 0.6

        return False, 0.0

    def should_listen(
        self,
        vad_active: bool,
        last_barge_in_ms: float,
        current_time_ms: float,
    ) -> bool:
        """Determine whether the agent should remain in listening mode.

        Args:
            vad_active: Whether VAD currently detects speech.
            last_barge_in_ms: Timestamp of the last barge-in event.
            current_time_ms: Current monotonic timestamp.

        Returns:
            ``True`` if the agent should keep listening.
        """
        if vad_active:
            return True

        # After a barge-in, continue listening for a grace period
        if last_barge_in_ms > 0:
            elapsed = current_time_ms - last_barge_in_ms
            if elapsed < self._barge_in_grace_ms:
                return True

        return False


# ---------------------------------------------------------------------------
# Full-Duplex Engine
# ---------------------------------------------------------------------------


class FullDuplexEngine:
    """Complete full-duplex voice engine.

    Orchestrates the conversation state machine, barge-in detection,
    turn-taking policy, and echo cancellation into a single interface.

    The engine follows this lifecycle::

        engine = FullDuplexEngine(...)
        engine.start()

        while engine.is_active:
            engine.feed_mic_audio(frame)          # Continuous mic input
            if engine.state == ConversationState.INTERRUPTED:
                engine.handle_barge_in()
            elif engine.should_take_turn():
                response = await think(...)
                engine.speak(response)

        engine.stop()

    Latency budget:
      - Barge-in detection: < 500 ms end-to-end.
      - State transitions: < 10 ms.
    """

    def __init__(
        self,
        barge_in_detector: BargeInDetector | None = None,
        turn_policy: TurnTakingPolicy | None = None,
        echo_cancellation: EchoCancellation | None = None,
        on_state_change: Callable[[ConversationState], None] | None = None,
        initial_state: ConversationState = ConversationState.IDLE,
    ) -> None:
        """Initialise the full-duplex engine.

        Args:
            barge_in_detector: Barge-in detector instance.  Created with
                defaults if ``None``.
            turn_policy: Turn-taking policy instance.  Created with
                ``BALANCED`` defaults if ``None``.
            echo_cancellation: Echo cancellation processor.  Created with
                defaults if ``None``.
            on_state_change: Optional callback fired on every state
                transition (useful for logging or UI indicators).
            initial_state: Starting conversation state (default ``IDLE``).
        """
        self._barge_in_detector = barge_in_detector or BargeInDetector()
        self._turn_policy = turn_policy or TurnTakingPolicy()
        self._echo_cancellation = echo_cancellation or EchoCancellation()
        self._on_state_change = on_state_change

        # State machine
        self._state: ConversationState = initial_state
        self._is_active: bool = False
        self._stats = DuplexEngineStats()

        # Timestamps for turn tracking
        self._silence_start_ms: float = 0.0
        self._last_speech_ms: float = 0.0
        self._last_barge_in_ms: float = 0.0
        self._turn_start_ms: float = 0.0
        self._last_vad_active: bool = False

        # Audio buffers
        self._mic_buffer: deque[TurnSegment] = deque(maxlen=200)

        # Assistant speech tracking
        self._assistant_speaking: bool = False
        self._assistant_audio_buffer: deque[bytes] = deque(maxlen=50)

        logger.info(
            "duplex.engine.initialised",
            initial_state=self._state.name,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> ConversationState:
        """Current conversation state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Whether the engine is running."""
        return self._is_active

    @property
    def stats(self) -> DuplexEngineStats:
        """Aggregate engine statistics."""
        return self._stats

    @property
    def turn_policy(self) -> TurnTakingPolicy:
        """The turn-taking policy (mutable)."""
        return self._turn_policy

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the full-duplex engine.

        Transitions from IDLE to LISTENING and prepares for audio processing.
        """
        if self._is_active:
            logger.warning("duplex.engine.already_running")
            return

        self._is_active = True
        self._transition_to(ConversationState.LISTENING)
        self._turn_start_ms = time.monotonic() * 1000
        logger.info("duplex.engine.started")

    def stop(self) -> None:
        """Stop the full-duplex engine gracefully.

        Transitions to IDLE and records final statistics.
        """
        if not self._is_active:
            return

        self._is_active = False
        self._assistant_speaking = False

        if self._turn_start_ms > 0:
            turn_ms = (time.monotonic() * 1000) - self._turn_start_ms
            self._stats.total_turn_duration_ms += turn_ms

        self._transition_to(ConversationState.IDLE)
        self._echo_cancellation.reset()
        self._barge_in_detector.reset()

        # Compute average interruption latency
        if self._stats.total_barge_ins > 0:
            self._stats.avg_interruption_latency_ms = (
                self._stats.total_interruption_latency_ms / self._stats.total_barge_ins
            )

        logger.info("duplex.engine.stopped")

    def reset(self) -> None:
        """Reset the engine to its initial state."""
        self._state = ConversationState.IDLE
        self._is_active = False
        self._stats = DuplexEngineStats()
        self._mic_buffer.clear()
        self._assistant_audio_buffer.clear()
        self._silence_start_ms = 0.0
        self._last_speech_ms = 0.0
        self._last_barge_in_ms = 0.0
        self._turn_start_ms = 0.0
        self._assistant_speaking = False
        self._echo_cancellation.reset()
        self._barge_in_detector.reset()
        logger.info("duplex.engine.reset")

    # ------------------------------------------------------------------
    # Audio Processing
    # ------------------------------------------------------------------

    def feed_mic_audio(
        self,
        audio_data: bytes,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:
        """Feed an incoming microphone audio frame into the engine.

        This is the primary entry point for real-time mic input.  Called
        continuously (e.g. every 20 ms) from the audio capture thread.

        Depending on the current state:
          - ``LISTENING``: buffer audio, track silence/speech.
          - ``SPEAKING``: run barge-in detection on the frame.
          - Other states: frame is ignored.

        Args:
            audio_data: 16-bit mono PCM audio bytes.
            sample_rate: Sample rate in Hz.
        """
        if not self._is_active:
            return

        now_ms = time.monotonic() * 1000

        # Apply AEC when assistant is speaking
        if self._assistant_speaking:
            audio_data = self._echo_cancellation.process(audio_data)

        # Run VAD
        vad_prob = BargeInDetector._default_vad(audio_data)
        is_speech = vad_prob >= 0.5

        segment = TurnSegment(
            audio=audio_data,
            sample_rate=sample_rate,
            timestamp_ms=now_ms,
            is_speech=is_speech,
        )

        self._last_vad_active = is_speech

        if self._state == ConversationState.LISTENING:
            self._mic_buffer.append(segment)
            if is_speech:
                self._last_speech_ms = now_ms
                self._silence_start_ms = 0.0
            elif self._silence_start_ms == 0.0:
                self._silence_start_ms = now_ms

        elif self._state == ConversationState.SPEAKING:
            # Barge-in detection during assistant speech
            event = self._barge_in_detector.feed_frame(audio_data, now_ms)
            if event is not None:
                self._on_barge_in_detected(event)

    def feed_assistant_audio(self, audio_data: bytes) -> None:
        """Feed assistant output audio as a reference for echo cancellation.

        Should be called with each chunk of TTS output before it is played.

        Args:
            audio_data: 16-bit mono PCM audio bytes.
        """
        self._assistant_audio_buffer.append(audio_data)
        self._echo_cancellation.add_reference(audio_data)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def should_take_turn(self) -> tuple[bool, float]:
        """Check whether the agent should take the speaking turn.

        Returns:
            (should_speak, confidence) -- based on the turn-taking policy.
        """
        now_ms = time.monotonic() * 1000

        # Duration of current silence
        silence_ms = 0.0
        if self._silence_start_ms > 0:
            silence_ms = now_ms - self._silence_start_ms

        # Duration of the last utterance
        utterance_ms = max(0.0, self._last_speech_ms - self._turn_start_ms)

        # Check if utterance is "complete" (sufficient silence + recent speech)
        is_complete = (
            silence_ms >= self._turn_policy._effective_silence_timeout_ms
            and self._last_speech_ms > 0
        )

        has_barge_in = self._state == ConversationState.INTERRUPTED

        return self._turn_policy.should_speak(
            silence_duration_ms=silence_ms,
            is_barge_in=has_barge_in,
            utterance_duration_ms=utterance_ms,
            is_utterance_complete=is_complete,
        )

    def should_listen(self) -> bool:
        """Check whether the agent should remain listening.

        Returns:
            ``True`` if the engine should stay in listening mode.
        """
        now_ms = time.monotonic() * 1000
        return self._turn_policy.should_listen(
            vad_active=self._last_vad_active,
            last_barge_in_ms=self._last_barge_in_ms,
            current_time_ms=now_ms,
        )

    def is_interrupted(self) -> bool:
        """Check whether the current turn was interrupted.

        Returns:
            ``True`` if in INTERRUPTED state.
        """
        return self._state == ConversationState.INTERRUPTED

    # ------------------------------------------------------------------
    # State transitions (public)
    # ------------------------------------------------------------------

    def begin_thinking(self) -> None:
        """Transition from LISTENING to THINKING.

        Called when the engine determines the user has finished speaking
        and the assistant should begin processing the input.
        """
        if self._state != ConversationState.LISTENING:
            return

        now_ms = time.monotonic() * 1000
        turn_ms = now_ms - self._turn_start_ms
        self._stats.total_turn_duration_ms += turn_ms

        self._transition_to(ConversationState.THINKING)

    def begin_speaking(self) -> None:
        """Transition from THINKING to SPEAKING.

        Called when the assistant has generated a response and TTS playback
        is about to begin.
        """
        if self._state != ConversationState.THINKING:
            return

        self._assistant_speaking = True
        self._transition_to(ConversationState.SPEAKING)

    def end_speaking(self) -> None:
        """Transition from SPEAKING to LISTENING.

        Called when the assistant has finished TTS playback.
        """
        if self._state != ConversationState.SPEAKING:
            return

        self._assistant_speaking = False
        self._silence_start_ms = 0.0
        self._turn_start_ms = time.monotonic() * 1000
        self._transition_to(ConversationState.LISTENING)

    def handle_interruption(self) -> bytes:
        """Handle an interruption by consuming the interrupting audio.

        Returns:
            The captured interrupting audio as PCM bytes.
        """
        if self._state != ConversationState.INTERRUPTED:
            return b""

        # Gather interrupting audio from the detector
        # (audio was already collected by BargeInDetector.feed_frame)

        self._assistant_speaking = False
        self._silence_start_ms = 0.0
        self._turn_start_ms = time.monotonic() * 1000
        self._transition_to(ConversationState.LISTENING)

        # Return accumulated mic buffer audio
        audio_segments = [s.audio for s in self._mic_buffer if s.is_speech]
        return b"".join(audio_segments)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _transition_to(self, new_state: ConversationState) -> None:
        """Perform a state transition with validation and callback."""
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        self._stats.state_transitions += 1

        logger.debug(
            "duplex.state_transition",
            old=old_state.name,
            new=new_state.name,
        )

        if self._on_state_change:
            try:
                self._on_state_change(new_state)
            except Exception as exc:
                logger.warning("duplex.state_callback_failed", error=str(exc))

    def _on_barge_in_detected(self, event: BargeInEvent) -> None:
        """Handle a detected barge-in event."""
        self._stats.total_barge_ins += 1
        self._stats.genuine_barge_ins += 1
        self._last_barge_in_ms = event.detected_at_ms

        # Measure end-to-end latency
        detection_latency_ms = time.monotonic() * 1000 - event.detected_at_ms
        self._stats.total_interruption_latency_ms += detection_latency_ms

        if detection_latency_ms > INTERRUPTION_LATENCY_BUDGET_MS:
            logger.warning(
                "duplex.barge_in_latency_exceeded",
                actual_ms=round(detection_latency_ms, 1),
            )

        logger.info(
            "duplex.barge_in_detected",
            confidence=round(event.confidence, 3),
            energy_level=round(event.energy_level, 1),
            latency_ms=round(detection_latency_ms, 1),
        )

        self._transition_to(ConversationState.INTERRUPTED)
