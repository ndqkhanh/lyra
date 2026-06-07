"""
Audio capture module -- microphone recording via ``sounddevice`` with VAD.

Provides the ``AudioCapture`` class that reads raw PCM frames from the default
microphone, passes them through a WebRTC VAD engine, and emits either raw
``AudioChunk`` or ``AudioChunkWithVad`` (speech / silence) objects.
"""

from __future__ import annotations

import logging
import queue
import struct
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AudioCaptureError(Exception):
    """Raised when audio capture fails (hardware, permission, etc.)."""


class VADError(Exception):
    """Raised when the VAD engine encounters an error."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioChunk:
    """Raw PCM audio chunk captured from the microphone.

    Attributes:
        frames: Raw 16-bit mono PCM frames (bytes).
        sample_rate: Sample rate in Hz.
        timestamp: Monotonic time of capture (seconds).
    """

    frames: bytes
    sample_rate: int
    timestamp: float


@dataclass(frozen=True)
class AudioChunkWithVad(AudioChunk):
    """Audio chunk with a VAD speech decision attached.

    Attributes:
        is_speech: ``True`` if the VAD engine considers this frame speech.
    """

    is_speech: bool


class VadMode(Enum):
    """Operating mode for ``AudioCapture``.

    * ``RAW``  — emits ``AudioChunk`` without VAD processing.
    * ``VAD``  — emits ``AudioChunkWithVad`` with speech/silence labels.
    """

    RAW = "raw"
    VAD = "vad"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_SAMPLE_RATE = 16_000  # 16 kHz (standard for VAD / STT)
_DEFAULT_FRAME_MS = 30  # 30 ms frames (webrtcvad works with 10, 20, 30 ms)
_DEFAULT_CHANNELS = 1  # mono
_DEFAULT_SILENCE_TIMEOUT = 1.5  # seconds of silence before flush
_SAMPLE_WIDTH = 2  # 16-bit PCM = 2 bytes per sample

# webrtcvad valid frame durations (ms)
_VALID_FRAME_DURATIONS = {10, 20, 30}

VAD_MODE_AGGRESSIVENESS = {
    0: 0,  # Lowest -- most sensitive (may include noise)
    1: 1,
    2: 2,
    3: 3,  # Highest -- only clear speech
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _frames_for_duration(
    sample_rate: int, duration_ms: int, sample_width: int = _SAMPLE_WIDTH
) -> int:
    """Return the number of PCM bytes expected for *duration_ms*."""
    return sample_rate * duration_ms // 1000 * sample_width


# ---------------------------------------------------------------------------
# AudioCapture
# ---------------------------------------------------------------------------


class AudioCapture:
    """Captures microphone audio and optionally applies VAD.

    Usage::

        capture = AudioCapture(sample_rate=16000, use_vad=True)
        for chunk in capture.stream():
            if chunk.is_speech:
                process(chunk.frames)
            # barge-in: chunk.is_speech after silence indicates new utterance
    """

    def __init__(
        self,
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
        frame_duration_ms: int = _DEFAULT_FRAME_MS,
        channels: int = _DEFAULT_CHANNELS,
        use_vad: bool = True,
        vad_aggressiveness: int = 3,
        silence_timeout: float = _DEFAULT_SILENCE_TIMEOUT,
        device: int | None = None,
    ) -> None:
        """Initialise the audio capture.

        Args:
            sample_rate: Sample rate in Hz (default 16000).
            frame_duration_ms: Duration of each frame in ms (10, 20, or 30).
            channels: Number of channels (default 1 for mono).
            use_vad: Enable WebRTC VAD processing.
            vad_aggressiveness: VAD aggressiveness 0-3 (3 = most aggressive).
            silence_timeout: Seconds of silence after which speech segment ends.
            device: Index of the input device, or ``None`` for the default.

        Raises:
            AudioCaptureError: If VAD is requested but ``webrtcvad`` is not
                available, or if the frame duration is invalid.
        """
        if frame_duration_ms not in _VALID_FRAME_DURATIONS:
            raise AudioCaptureError(
                f"Invalid frame duration {frame_duration_ms}ms; "
                f"valid values: {_VALID_FRAME_DURATIONS}"
            )

        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        self._channels = channels
        self._use_vad = use_vad
        self._vad_aggressiveness = min(max(vad_aggressiveness, 0), 3)
        self._silence_timeout = silence_timeout
        self._device = device

        # Internal state
        self._running = False
        self._stream: "sounddevice.RawInputStream | None" = None
        self._audio_queue: queue.Queue[bytes | None] = queue.Queue()
        self._vad = None

        if use_vad:
            self._init_vad()

    def _init_vad(self) -> None:
        """Lazily initialise the ``webrtcvad.VAD`` instance."""
        try:
            import webrtcvad  # noqa: F811
        except ImportError as exc:
            raise AudioCaptureError(
                "VAD requested but webrtcvad is not installed. "
                "Run: pip install webrtcvad"
            ) from exc

        self._vad = webrtcvad.Vad()
        self._vad.set_mode(self._vad_aggressiveness)
        logger.debug(
            "VAD initialised (aggressiveness=%d, frame=%dms)",
            self._vad_aggressiveness,
            self._frame_duration_ms,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def sample_rate(self) -> int:
        """Return the configured sample rate."""
        return self._sample_rate

    @property
    def is_running(self) -> bool:
        """``True`` while the capture stream is active."""
        return self._running

    def start(self) -> None:
        """Open the microphone input stream.

        Raises:
            AudioCaptureError: If the underlying audio device cannot be opened.
        """
        if self._running:
            logger.warning("AudioCapture already running")
            return

        import sounddevice as sd  # noqa: F811

        self._running = True

        def _callback(indata: bytes, _frames: int, _time_info, _status) -> None:
            """sounddevice raw callback -- push data into the internal queue."""
            self._audio_queue.put(bytes(indata))

        try:
            self._stream = sd.RawInputStream(
                samplerate=self._sample_rate,
                blocksize=_frames_for_duration(
                    self._sample_rate, self._frame_duration_ms
                ),
                device=self._device,
                channels=self._channels,
                dtype="int16",
                callback=_callback,
            )
            self._stream.start()
        except Exception as exc:
            self._running = False
            self._stream = None
            raise AudioCaptureError(
                f"Failed to open microphone stream: {exc}"
            ) from exc

        logger.info(
            "AudioCapture started (%d Hz, %d channels, VAD=%s)",
            self._sample_rate,
            self._channels,
            self._use_vad,
        )

    def stop(self) -> None:
        """Stop the microphone input stream."""
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                logger.exception("Error closing audio stream")
            self._stream = None

        # Drain the queue so the producer thread can join
        self._audio_queue.put(None)
        logger.info("AudioCapture stopped")

    def stream(
        self,
        mode: VadMode = VadMode.VAD,
    ) -> "AudioStreamIterator":
        """Return an iterator over captured audio chunks.

        Args:
            mode: ``VadMode.RAW`` for raw chunks, ``VadMode.VAD`` for VAD-tagged.

        Returns:
            An ``AudioStreamIterator`` that yields ``AudioChunk`` or
            ``AudioChunkWithVad``.
        """
        return AudioStreamIterator(self, mode)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _read_frame(self, timeout: float | None = 0.5) -> bytes | None:
        """Read a single frame from the internal queue (blocking with timeout).

        Returns ``None`` on timeout or when the stream has been stopped.
        """
        try:
            data = self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        return data

    def _process_frame(self, frames: bytes) -> AudioChunk:
        """Wrap raw frames into an ``AudioChunk``."""
        return AudioChunk(
            frames=frames,
            sample_rate=self._sample_rate,
            timestamp=time.monotonic(),
        )

    def _process_frame_with_vad(self, frames: bytes) -> AudioChunkWithVad:
        """Wrap raw frames into an ``AudioChunkWithVad`` after VAD check."""
        if self._vad is None:
            raise VADError("VAD not initialised")

        is_speech = self._vad.is_speech(frames, self._sample_rate)
        return AudioChunkWithVad(
            frames=frames,
            sample_rate=self._sample_rate,
            timestamp=time.monotonic(),
            is_speech=is_speech,
        )


class AudioStreamIterator:
    """Iterator over ``AudioCapture`` frames.

    Returned by ``AudioCapture.stream()``.  Supports ``__next__`` for
    synchronous use and ``__aiter__`` / ``__anext__`` for async use.
    """

    def __init__(self, capture: AudioCapture, mode: VadMode) -> None:
        self._capture = capture
        self._mode = mode
        self._silence_counter = 0.0

    def __iter__(self) -> "AudioStreamIterator":
        return self

    def __next__(self) -> AudioChunk | AudioChunkWithVad:
        while self._capture._running:
            frames = self._capture._read_frame()
            if frames is None:
                continue
            if self._mode == VadMode.VAD:
                return self._capture._process_frame_with_vad(frames)
            return self._capture._process_frame(frames)
        raise StopIteration

    async def __aiter__(self) -> "AudioStreamIterator":
        return self

    async def __anext__(self) -> AudioChunk | AudioChunkWithVad:
        try:
            return self.__next__()
        except StopIteration:
            raise StopAsyncIteration


# ---------------------------------------------------------------------------
# Convenience: record until silence
# ---------------------------------------------------------------------------


def record_utterance(
    capture: AudioCapture,
    max_duration: float = 30.0,
    silence_timeout: float = _DEFAULT_SILENCE_TIMEOUT,
) -> bytearray:
    """Record audio from *capture* until a period of silence or *max_duration*.

    Args:
        capture: An initialised ``AudioCapture`` instance.
        max_duration: Maximum recording duration in seconds.
        silence_timeout: Seconds of silence before stopping.

    Returns:
        A ``bytearray`` of concatenated 16-bit PCM frames containing speech.

    Raises:
        AudioCaptureError: If capture is not running.
    """
    if not capture.is_running:
        raise AudioCaptureError("Capture is not running. Call start() first.")

    buffer = bytearray()
    silence_start: float | None = None
    start_time = time.monotonic()

    for chunk in capture.stream(mode=VadMode.VAD):
        elapsed = time.monotonic() - start_time
        if elapsed > max_duration:
            logger.info("record_utterance: reached max_duration (%.1fs)", max_duration)
            break

        if chunk.is_speech:
            buffer.extend(chunk.frames)
            silence_start = None
        else:
            if silence_start is None:
                silence_start = chunk.timestamp
            elif (chunk.timestamp - silence_start) > silence_timeout:
                logger.info(
                    "record_utterance: silence timeout (%.1fs)", silence_timeout
                )
                break

    return buffer
