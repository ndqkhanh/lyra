"""
Desktop Voice Surface -- push-to-talk button, waveform visualiser, live
transcript panel, and voice activity indicator for the Lyra desktop UI.

Provides the UI-facing components that bridge the voice pipeline to the
desktop chat interface:

  - DesktopVoiceSurface: push-to-talk button in desktop UI.
  - WaveformVisualizer: real-time audio waveform display.
  - TranscriptPanel: live transcription with speaker labels.
  - VoiceActivityIndicator: glowing mic button when listening.

Usage::

    surface = DesktopVoiceSurface(
        waveform=WaveformVisualizer(),
        transcript=TranscriptPanel(),
        activity=VoiceActivityIndicator(),
    )

    # When pipeline state changes
    surface.on_state_change(ConversationState.LISTENING)
    surface.on_transcript_update("user", "Hello, Lyra")
    surface.on_audio_level(0.75)
"""

from __future__ import annotations

import math
import structlog
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WAVEFORM_HISTORY_SIZE: int = 80
"""Number of audio level samples kept in the waveform history."""

TRANSCRIPT_MAX_LINES: int = 200
"""Maximum number of transcript lines before truncation."""

GLOW_THRESHOLD: float = 0.05
"""Minimum audio level to trigger the voice activity glow effect."""

GLOW_FADE_MS: float = 300.0
"""Time in ms for the glow to fade after speech stops."""

DEFAULT_WAVEFORM_WIDTH: int = 300
"""Default waveform visualisation width in pixels."""

DEFAULT_WAVEFORM_HEIGHT: int = 80
"""Default waveform visualisation height in pixels."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SpeakerLabel(Enum):
    """Speaker label for transcript entries."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class VoiceSurfaceState(Enum):
    """Visual state of the voice surface component."""

    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    INTERRUPTED = auto()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptEntry:
    """A single line in the live transcript.

    Attributes:
        speaker: Who spoke this line.
        text: The transcribed text.
        timestamp_ms: Monotonic timestamp when the utterance was captured.
        confidence: Transcription confidence (0.0 - 1.0).
        is_partial: Whether this is a partial (streaming) or final transcript.
    """

    speaker: SpeakerLabel
    text: str
    timestamp_ms: float = 0.0
    confidence: float = 1.0
    is_partial: bool = False


@dataclass(frozen=True)
class AudioLevelSample:
    """A single audio level sample for the waveform.

    Attributes:
        level: RMS level normalised to 0.0 - 1.0.
        timestamp_ms: Monotonic timestamp.
        is_speech: Whether VAD considers this speech.
    """

    level: float
    timestamp_ms: float = 0.0
    is_speech: bool = False


# ---------------------------------------------------------------------------
# Waveform Visualizer
# ---------------------------------------------------------------------------


class WaveformVisualizer:
    """Real-time audio waveform display for the desktop voice surface.

    Maintains a ring buffer of audio level samples and can render them as
    a simple bar waveform or return the data for a custom UI renderer.

    Supports:
      - Ring buffer of normalised RMS samples (0.0 - 1.0).
      - Speech/non-speech colour indication.
      - Configurable history size and dimensions.
      - Sample export for external rendering (e.g. canvas, WebView).
    """

    def __init__(
        self,
        history_size: int = WAVEFORM_HISTORY_SIZE,
        width: int = DEFAULT_WAVEFORM_WIDTH,
        height: int = DEFAULT_WAVEFORM_HEIGHT,
    ) -> None:
        """Initialise the waveform visualiser.

        Args:
            history_size: Number of samples to retain in history.
            width: Visualisation width in "pixels" (for bar rendering).
            height: Visualisation height in "pixels".
        """
        self._history: list[AudioLevelSample] = []
        self._max_samples = history_size
        self._width = width
        self._height = height
        self._last_speech_time_ms: float = 0.0

    @property
    def history(self) -> list[AudioLevelSample]:
        """Current waveform history (copy)."""
        return list(self._history)

    @property
    def width(self) -> int:
        """Visualisation width."""
        return self._width

    @property
    def height(self) -> int:
        """Visualisation height."""
        return self._height

    def push_sample(
        self,
        level: float,
        is_speech: bool = False,
    ) -> None:
        """Add a new audio level sample to the waveform history.

        Args:
            level: Normalised RMS level (0.0 - 1.0).
            is_speech: Whether VAD considers this speech.
        """
        now_ms = time.monotonic() * 1000
        sample = AudioLevelSample(
            level=max(0.0, min(1.0, level)),
            timestamp_ms=now_ms,
            is_speech=is_speech,
        )

        self._history.append(sample)
        if len(self._history) > self._max_samples:
            self._history.pop(0)

        if is_speech:
            self._last_speech_time_ms = now_ms

    def get_recent(self, count: int = 40) -> list[float]:
        """Get the N most recent level values as a flat list.

        Args:
            count: Number of recent samples to return.

        Returns:
            List of normalised level values (0.0 - 1.0), most recent last.
        """
        recent = self._history[-count:] if count > 0 else self._history
        return [s.level for s in recent]

    def render_bars(self, width: int | None = None, height: int | None = None) -> list[int]:
        """Render the waveform as a list of bar heights.

        Each element represents the height of a bar in the visualisation,
        scaled to the given dimensions.

        Args:
            width: Number of bars to render (defaults to instance width).
            height: Maximum bar height in "pixels" (defaults to instance
                height).

        Returns:
            List of bar heights, one per sample.
        """
        w = width or self._width
        h = height or self._height

        # Decimate samples to match the desired bar count
        samples = self._history[-w:] if len(self._history) >= w else self._history
        if not samples:
            return [0] * w

        bars: list[int] = []
        for i in range(w):
            if i < len(samples):
                bar_height = int(samples[i].level * h)
                bars.append(min(bar_height, h))
            else:
                bars.append(0)

        return bars

    def reset(self) -> None:
        """Clear the waveform history."""
        self._history.clear()
        self._last_speech_time_ms = 0.0


# ---------------------------------------------------------------------------
# Transcript Panel
# ---------------------------------------------------------------------------


class TranscriptPanel:
    """Live transcription display with speaker labels.

    Maintains a list of transcript entries, supports partial updates
    (streaming ASR), and provides full text export.
    """

    def __init__(self, max_lines: int = TRANSCRIPT_MAX_LINES) -> None:
        """Initialise the transcript panel.

        Args:
            max_lines: Maximum number of lines before oldest entries
                are evicted.
        """
        self._entries: list[TranscriptEntry] = []
        self._max_lines = max_lines
        self._on_new_entry: Callable[[TranscriptEntry], None] | None = None

    @property
    def entries(self) -> list[TranscriptEntry]:
        """All transcript entries (copy)."""
        return list(self._entries)

    @property
    def max_lines(self) -> int:
        """Maximum number of lines."""
        return self._max_lines

    def set_on_new_entry(self, callback: Callable[[TranscriptEntry], None] | None) -> None:
        """Register a callback for new transcript entries.

        The callback receives the new ``TranscriptEntry`` each time one is
        added.  Useful for UI frameworks that need real-time updates.

        Args:
            callback: Callable taking a ``TranscriptEntry``, or ``None``
                to clear.
        """
        self._on_new_entry = callback

    def add_entry(
        self,
        speaker: SpeakerLabel | str,
        text: str,
        confidence: float = 1.0,
        is_partial: bool = False,
    ) -> TranscriptEntry:
        """Add a new transcript entry.

        Args:
            speaker: Speaker label (enum or string).
            text: Transcribed text.
            confidence: Transcription confidence (0.0 - 1.0).
            is_partial: Whether this is a partial (streaming) result.

        Returns:
            The created ``TranscriptEntry``.
        """
        if isinstance(speaker, str):
            try:
                speaker = SpeakerLabel(speaker.lower())
            except ValueError:
                speaker = SpeakerLabel.SYSTEM

        entry = TranscriptEntry(
            speaker=speaker,
            text=text,
            timestamp_ms=time.monotonic() * 1000,
            confidence=confidence,
            is_partial=is_partial,
        )

        self._entries.append(entry)

        # Enforce max lines
        if len(self._entries) > self._max_lines:
            self._entries = self._entries[-self._max_lines:]

        # Notify callback
        if self._on_new_entry is not None:
            try:
                self._on_new_entry(entry)
            except Exception as exc:
                logger.warning("transcript.callback_failed", error=str(exc))

        return entry

    def update_last(self, text: str, confidence: float | None = None) -> None:
        """Update the text of the most recent entry (for streaming updates).

        Args:
            text: New text for the most recent entry.
            confidence: Optional updated confidence.
        """
        if not self._entries:
            return

        last = self._entries[-1]
        entry = TranscriptEntry(
            speaker=last.speaker,
            text=text,
            timestamp_ms=last.timestamp_ms,
            confidence=confidence if confidence is not None else last.confidence,
            is_partial=True,
        )
        self._entries[-1] = entry

    def get_formatted(self, include_timestamps: bool = False) -> str:
        """Get the transcript as a formatted string.

        Args:
            include_timestamps: Whether to prepend timestamps to each line.

        Returns:
            A formatted transcript string.
        """
        lines: list[str] = []
        for entry in self._entries:
            speaker_name = entry.speaker.value.capitalize()
            text = entry.text

            if include_timestamps:
                ts = entry.timestamp_ms / 1000.0
                prefix = f"[{ts:.1f}s] {speaker_name}: "
            else:
                prefix = f"{speaker_name}: "

            if entry.is_partial:
                text = f"{text} [...]"

            lines.append(f"{prefix}{text}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all transcript entries."""
        self._entries.clear()

    def export_json(self) -> list[dict[str, Any]]:
        """Export transcript entries as a list of JSON-compatible dicts.

        Returns:
            List of dicts with speaker, text, timestamp, and confidence.
        """
        return [
            {
                "speaker": e.speaker.value,
                "text": e.text,
                "timestamp_ms": e.timestamp_ms,
                "confidence": e.confidence,
                "is_partial": e.is_partial,
            }
            for e in self._entries
        ]


# ---------------------------------------------------------------------------
# Voice Activity Indicator
# ---------------------------------------------------------------------------


class VoiceActivityIndicator:
    """Glowing microphone button that lights up when listening.

    Provides a visual feedback mechanism for the voice surface:
      - Glow/brightness level based on audio RMS.
      - Fade-out effect after speech stops.
      - State colours for idle, listening, processing, and speaking.
    """

    def __init__(
        self,
        glow_threshold: float = GLOW_THRESHOLD,
        fade_ms: float = GLOW_FADE_MS,
    ) -> None:
        """Initialise the voice activity indicator.

        Args:
            glow_threshold: Minimum audio level to trigger the glow.
            fade_ms: Time in ms for the glow to fully fade.
        """
        self._glow_threshold = glow_threshold
        self._fade_ms = fade_ms
        self._last_speech_time_ms: float = 0.0
        self._last_audio_level: float = 0.0
        self._surface_state: VoiceSurfaceState = VoiceSurfaceState.IDLE

    @property
    def surface_state(self) -> VoiceSurfaceState:
        """Current visual surface state."""
        return self._surface_state

    @property
    def glow_intensity(self) -> float:
        """Compute the current glow intensity (0.0 - 1.0).

        Returns a value based on the current audio level, speech state,
        and fade-out timing.
        """
        now_ms = time.monotonic() * 1000

        # If we have recent speech, glow based on audio level
        if self._last_audio_level > self._glow_threshold:
            return min(1.0, self._last_audio_level * 1.5)

        # Fade out after speech stops
        if self._last_speech_time_ms > 0:
            elapsed = now_ms - self._last_speech_time_ms
            if elapsed < self._fade_ms:
                fade_progress = elapsed / self._fade_ms
                return max(0.0, 1.0 - fade_progress)

        # Base glow based on surface state
        state_glow = {
            VoiceSurfaceState.LISTENING: 0.3,
            VoiceSurfaceState.SPEAKING: 0.2,
            VoiceSurfaceState.PROCESSING: 0.15,
            VoiceSurfaceState.INTERRUPTED: 0.5,
            VoiceSurfaceState.IDLE: 0.0,
        }
        return state_glow.get(self._surface_state, 0.0)

    def on_audio_level(self, level: float, is_speech: bool = False) -> None:
        """Update the audio level for glow computation.

        Args:
            level: Normalised RMS audio level (0.0 - 1.0).
            is_speech: Whether VAD considers this speech.
        """
        self._last_audio_level = max(0.0, min(1.0, level))
        if is_speech:
            self._last_speech_time_ms = time.monotonic() * 1000

    def on_state_change(self, state: VoiceSurfaceState) -> None:
        """Update the surface state.

        Args:
            state: New visual surface state.
        """
        self._surface_state = state
        self._last_audio_level = 0.0

    def is_glowing(self) -> bool:
        """Check whether the indicator is currently glowing.

        Returns:
            ``True`` if the glow intensity exceeds the threshold.
        """
        return self.glow_intensity > self._glow_threshold

    def get_color(self) -> str:
        """Get the current indicator colour based on state.

        Returns:
            A CSS-compatible colour string (hex or name).
        """
        colors = {
            VoiceSurfaceState.IDLE: "#666666",
            VoiceSurfaceState.LISTENING: "#00cc66",
            VoiceSurfaceState.PROCESSING: "#ffaa00",
            VoiceSurfaceState.SPEAKING: "#3399ff",
            VoiceSurfaceState.INTERRUPTED: "#ff4444",
        }
        return colors.get(self._surface_state, "#666666")

    def reset(self) -> None:
        """Reset the indicator to idle state."""
        self._last_speech_time_ms = 0.0
        self._last_audio_level = 0.0
        self._surface_state = VoiceSurfaceState.IDLE


# ---------------------------------------------------------------------------
# Desktop Voice Surface (orchestrator)
# ---------------------------------------------------------------------------


class DesktopVoiceSurface:
    """Push-to-talk button and voice status widget for the desktop UI.

    Orchestrates:
      - Waveform visualizer (real-time audio display).
      - Transcript panel (live transcription).
      - Voice activity indicator (glowing mic button).

    Exposes a simple API that the voice pipeline calls to update the UI,
    and that the desktop UI framework calls to read the current state.
    """

    def __init__(
        self,
        waveform: WaveformVisualizer | None = None,
        transcript: TranscriptPanel | None = None,
        activity: VoiceActivityIndicator | None = None,
    ) -> None:
        """Initialise the desktop voice surface.

        Args:
            waveform: Waveform visualizer.  Created with defaults if
                ``None``.
            transcript: Transcript panel.  Created with defaults if
                ``None``.
            activity: Voice activity indicator.  Created with defaults
                if ``None``.
        """
        self._waveform = waveform or WaveformVisualizer()
        self._transcript = transcript or TranscriptPanel()
        self._activity = activity or VoiceActivityIndicator()
        self._is_pressed: bool = False
        self._on_toggle: Callable[[bool], None] | None = None

    # ------------------------------------------------------------------
    # Sub-components
    # ------------------------------------------------------------------

    @property
    def waveform(self) -> WaveformVisualizer:
        """Waveform visualizer sub-component."""
        return self._waveform

    @property
    def transcript(self) -> TranscriptPanel:
        """Transcript panel sub-component."""
        return self._transcript

    @property
    def activity(self) -> VoiceActivityIndicator:
        """Voice activity indicator sub-component."""
        return self._activity

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_pressed(self) -> bool:
        """Whether the push-to-talk button is currently pressed."""
        return self._is_pressed

    @property
    def surface_state(self) -> VoiceSurfaceState:
        """Current visual surface state."""
        return self._activity.surface_state

    # ------------------------------------------------------------------
    # Button events
    # ------------------------------------------------------------------

    def set_on_toggle(self, callback: Callable[[bool], None] | None) -> None:
        """Register a callback for push-to-talk button toggle.

        Args:
            callback: Called with ``True`` when pressed, ``False`` when
                released.
        """
        self._on_toggle = callback

    def press(self) -> None:
        """Press the push-to-talk button (start listening)."""
        if self._is_pressed:
            return
        self._is_pressed = True
        self._activity.on_state_change(VoiceSurfaceState.LISTENING)
        logger.debug("voice_surface.pressed")

        if self._on_toggle:
            try:
                self._on_toggle(True)
            except Exception as exc:
                logger.warning("voice_surface.toggle_callback_failed", error=str(exc))

    def release(self) -> None:
        """Release the push-to-talk button (stop listening)."""
        if not self._is_pressed:
            return
        self._is_pressed = False
        self._activity.on_state_change(VoiceSurfaceState.PROCESSING)
        logger.debug("voice_surface.released")

        if self._on_toggle:
            try:
                self._on_toggle(False)
            except Exception as exc:
                logger.warning("voice_surface.toggle_callback_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Pipeline callbacks
    # ------------------------------------------------------------------

    def on_audio_level(self, level: float, is_speech: bool = False) -> None:
        """Called by the pipeline with each audio level sample.

        Args:
            level: Normalised RMS audio level (0.0 - 1.0).
            is_speech: Whether VAD classifies this as speech.
        """
        self._waveform.push_sample(level, is_speech)
        self._activity.on_audio_level(level, is_speech)

    def on_transcript_update(
        self,
        speaker: str,
        text: str,
        confidence: float = 1.0,
        is_partial: bool = False,
    ) -> None:
        """Called by the pipeline when new transcription is available.

        Args:
            speaker: Speaker label ("user", "assistant", "system").
            text: Transcribed text.
            confidence: Transcription confidence.
            is_partial: Whether this is a partial (streaming) result.
        """
        self._transcript.add_entry(speaker, text, confidence, is_partial)

    def on_state_change(self, state: VoiceSurfaceState) -> None:
        """Called by the pipeline when the conversation state changes.

        Args:
            state: New surface state.
        """
        self._activity.on_state_change(state)

    # ------------------------------------------------------------------
    # State export
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Export the full voice surface state for UI rendering.

        Returns:
            Dict with waveform data, transcript, and indicator state.
        """
        return {
            "is_pressed": self._is_pressed,
            "surface_state": self._surface_state.name if hasattr(self, "_surface_state") else "IDLE",
            "glow_intensity": self._activity.glow_intensity,
            "glow_color": self._activity.get_color(),
            "is_glowing": self._activity.is_glowing(),
            "waveform": {
                "bars": self._waveform.render_bars(),
                "history_count": len(self._waveform.history),
            },
            "transcript": {
                "entry_count": len(self._transcript.entries),
                "entries": self._transcript.export_json()[-10:],  # Last 10
            },
        }

    def reset(self) -> None:
        """Reset all voice surface components to idle state."""
        self._is_pressed = False
        self._waveform.reset()
        self._transcript.clear()
        self._activity.reset()
        logger.info("voice_surface.reset")
