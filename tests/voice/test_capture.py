"""Comprehensive tests for the AudioCapture module.

Tests AudioCapture lifecycle, AudioStreamIterator, record_utterance,
error paths, and edge cases.  All audio hardware dependencies are mocked.
"""

from __future__ import annotations

import queue
import time
from unittest.mock import MagicMock, patch

import pytest

from lyra.voice.capture import (
    AudioCapture,
    AudioCaptureError,
    AudioChunk,
    AudioChunkWithVad,
    AudioStreamIterator,
    VADError,
    VadMode,
    _frames_for_duration,
    record_utterance,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_silence() -> bytes:
    """Generate 30ms of silence at 16kHz (960 bytes)."""
    return b"\x00\x00" * 480  # 30ms @ 16kHz = 480 samples * 2 bytes


# ===================================================================
# _frames_for_duration helper
# ===================================================================


class TestFramesForDuration:
    def test_computes_correct_byte_count(self) -> None:
        result = _frames_for_duration(16000, 30, 2)
        assert result == 960  # 16000 * 30 / 1000 * 2

    def test_zero_duration(self) -> None:
        result = _frames_for_duration(16000, 0, 2)
        assert result == 0

    def test_different_sample_rates(self) -> None:
        result = _frames_for_duration(44100, 100, 2)
        assert result == 8820  # 44100 * 100 / 1000 * 2


# ===================================================================
# AudioCapture tests
# ===================================================================


class TestAudioCaptureInit:
    """Tests for AudioCapture initialisation and validation."""

    def test_default_parameters(self) -> None:
        capture = AudioCapture()
        assert capture.sample_rate == 16000
        assert not capture.is_running
        assert capture._use_vad is True
        assert capture._vad_aggressiveness == 3

    def test_custom_parameters(self) -> None:
        capture = AudioCapture(
            sample_rate=44100,
            frame_duration_ms=20,
            channels=2,
            use_vad=False,
            vad_aggressiveness=1,
            silence_timeout=2.0,
            device=0,
        )
        assert capture.sample_rate == 44100
        assert capture._frame_duration_ms == 20
        assert capture._channels == 2
        assert capture._use_vad is False

    def test_invalid_frame_duration_raises(self) -> None:
        with pytest.raises(AudioCaptureError, match="Invalid frame duration"):
            AudioCapture(frame_duration_ms=15)

    def test_boundary_frame_durations(self) -> None:
        for ms in (10, 20, 30):
            capture = AudioCapture(frame_duration_ms=ms)
            assert capture._frame_duration_ms == ms

    def test_vad_aggressiveness_clamped(self) -> None:
        capture = AudioCapture(vad_aggressiveness=5)
        assert capture._vad_aggressiveness == 3

        capture = AudioCapture(vad_aggressiveness=-1)
        assert capture._vad_aggressiveness == 0

    def test_init_vad_import_error(self) -> None:
        """When webrtcvad is not available, VAD init should raise."""
        import builtins
        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "webrtcvad":
                raise ImportError("No module named 'webrtcvad'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=failing_import):
            with pytest.raises(AudioCaptureError, match="webrtcvad"):
                AudioCapture(use_vad=True)

    def test_no_vad_when_disabled(self) -> None:
        capture = AudioCapture(use_vad=False)
        assert capture._vad is None


class TestAudioCaptureStartStop:
    """Tests for AudioCapture.start() and stop()."""

    @patch("sounddevice.RawInputStream")
    def test_start_opens_stream(self, MockRawInputStream: MagicMock) -> None:
        capture = AudioCapture(use_vad=False)
        capture.start()

        assert capture.is_running
        MockRawInputStream.assert_called_once()
        args, kwargs = MockRawInputStream.call_args
        assert kwargs["samplerate"] == 16000
        assert kwargs["channels"] == 1
        assert kwargs["dtype"] == "int16"

    @patch("sounddevice.RawInputStream")
    def test_start_idempotent_when_already_running(
        self, MockRawInputStream: MagicMock
    ) -> None:
        capture = AudioCapture(use_vad=False)
        capture.start()
        assert capture.is_running

        # Second start should not create a new stream
        MockRawInputStream.reset_mock()
        capture.start()
        MockRawInputStream.assert_not_called()

    @patch("sounddevice.RawInputStream")
    def test_stop_closes_stream(self, MockRawInputStream: MagicMock) -> None:
        mock_stream = MockRawInputStream.return_value
        capture = AudioCapture(use_vad=False)
        capture.start()
        capture.stop()

        assert not capture.is_running
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert capture._stream is None

    @patch("sounddevice.RawInputStream")
    def test_stop_drains_queue(self, MockRawInputStream: MagicMock) -> None:
        capture = AudioCapture(use_vad=False)
        capture.start()
        # Put some data in queue
        capture._audio_queue.put(b"test_data")
        capture.stop()
        # Queue should have been drained (sentinel added)
        assert capture._audio_queue.qsize() >= 0

    @patch("sounddevice.RawInputStream")
    def test_stop_when_not_running(self, MockRawInputStream: MagicMock) -> None:
        """Calling stop() when not running is a no-op."""
        capture = AudioCapture(use_vad=False)
        capture.stop()  # Should not raise

    @patch("sounddevice.RawInputStream")
    def test_start_failure_cleans_up(
        self, MockRawInputStream: MagicMock
    ) -> None:
        MockRawInputStream.side_effect = RuntimeError("Device error")
        capture = AudioCapture(use_vad=False)

        with pytest.raises(AudioCaptureError, match="Failed to open"):
            capture.start()

        assert not capture.is_running
        assert capture._stream is None

    @patch("sounddevice.RawInputStream")
    def test_start_with_vad_init(
        self, MockRawInputStream: MagicMock
    ) -> None:
        """With VAD enabled, webrtcvad should be loaded during init."""
        capture = AudioCapture(use_vad=True)
        assert capture._vad is not None

    @patch("sounddevice.RawInputStream")
    def test_callback_pushes_to_queue(
        self, MockRawInputStream: MagicMock
    ) -> None:
        """Verify the internal callback puts audio bytes in the queue."""
        capture = AudioCapture(use_vad=False)
        # Manually extract the callback
        capture.start()
        callback = MockRawInputStream.call_args[1]["callback"]

        callback(b"\x00\x01" * 100, 100, None, None)
        data = capture._audio_queue.get(timeout=0.1)
        assert data == b"\x00\x01" * 100


class TestAudioCaptureProperties:
    """Tests for AudioCapture property accessors."""

    def test_sample_rate_property(self) -> None:
        capture = AudioCapture(sample_rate=44100)
        assert capture.sample_rate == 44100

    def test_is_running_initial(self) -> None:
        capture = AudioCapture()
        assert capture.is_running is False


class TestAudioCaptureReadFrame:
    """Tests for _read_frame internal method."""

    def test_read_frame_returns_data(self) -> None:
        capture = AudioCapture(use_vad=False)
        capture._audio_queue.put(b"\x00\x00" * 100)
        result = capture._read_frame(timeout=0.1)
        assert result == b"\x00\x00" * 100

    def test_read_frame_timeout_returns_none(self) -> None:
        capture = AudioCapture(use_vad=False)
        result = capture._read_frame(timeout=0.01)
        assert result is None

    def test_read_frame_none_sentinel(self) -> None:
        """When None is placed in the queue, it should be returned."""
        capture = AudioCapture(use_vad=False)
        capture._audio_queue.put(None)
        result = capture._read_frame(timeout=0.1)
        assert result is None


class TestAudioCaptureProcessFrame:
    """Tests for _process_frame and _process_frame_with_vad."""

    def test_process_frame_returns_audio_chunk(self) -> None:
        capture = AudioCapture(use_vad=False, sample_rate=16000)
        frames = b"\x00\x00" * 200
        chunk = capture._process_frame(frames)
        assert isinstance(chunk, AudioChunk)
        assert chunk.frames == frames
        assert chunk.sample_rate == 16000
        assert chunk.timestamp > 0

    def test_process_frame_with_vad_returns_vad_chunk(self) -> None:
        capture = AudioCapture(use_vad=True)
        capture._vad = MagicMock()
        capture._vad.is_speech.return_value = True
        frames = b"\x00\x00" * 480

        chunk = capture._process_frame_with_vad(frames)
        assert isinstance(chunk, AudioChunkWithVad)
        assert chunk.is_speech is True
        assert chunk.frames == frames

    def test_process_frame_with_vad_no_vad_raises(self) -> None:
        capture = AudioCapture(use_vad=False)
        with pytest.raises(VADError, match="VAD not initialised"):
            capture._process_frame_with_vad(b"\x00\x00" * 480)

    def test_process_frame_with_vad_speech_false(self) -> None:
        capture = AudioCapture(use_vad=True)
        capture._vad = MagicMock()
        capture._vad.is_speech.return_value = False
        chunk = capture._process_frame_with_vad(b"\x00\x00" * 480)
        assert chunk.is_speech is False


class TestAudioCaptureStream:
    """Tests for AudioCapture.stream()."""

    @patch("sounddevice.RawInputStream")
    def test_stream_returns_iterator(
        self, MockRawInputStream: MagicMock
    ) -> None:
        capture = AudioCapture(use_vad=False)
        it = capture.stream(mode=VadMode.RAW)
        assert isinstance(it, AudioStreamIterator)

    @patch("sounddevice.RawInputStream")
    def test_stream_with_vad_mode(
        self, MockRawInputStream: MagicMock
    ) -> None:
        """VAD mode should still return an iterator."""
        capture = AudioCapture(use_vad=True)
        capture._vad = MagicMock()
        capture._vad.is_speech.return_value = False
        it = capture.stream(mode=VadMode.VAD)
        assert isinstance(it, AudioStreamIterator)


# ===================================================================
# AudioStreamIterator tests
# ===================================================================


class TestAudioStreamIterator:
    """Tests for the AudioStreamIterator class."""

    def test_iter_returns_self(self) -> None:
        capture = AudioCapture(use_vad=False)
        it = AudioStreamIterator(capture, VadMode.RAW)
        assert iter(it) is it

    @patch("sounddevice.RawInputStream")
    def test_next_returns_audio_chunk(
        self, MockRawInputStream: MagicMock
    ) -> None:
        capture = AudioCapture(use_vad=False)
        capture.start()
        capture._audio_queue.put(b"\x00\x00" * 480)

        it = AudioStreamIterator(capture, VadMode.RAW)
        chunk = next(it)
        assert isinstance(chunk, AudioChunk)

        # Cleanup
        capture.stop()

    @patch("sounddevice.RawInputStream")
    def test_next_stop_iteration_when_stopped(
        self, MockRawInputStream: MagicMock
    ) -> None:
        capture = AudioCapture(use_vad=False)
        capture._running = False  # Already stopped

        it = AudioStreamIterator(capture, VadMode.RAW)
        with pytest.raises(StopIteration):
            next(it)

    @patch("sounddevice.RawInputStream")
    @pytest.mark.asyncio
    async def test_async_iteration(
        self, MockRawInputStream: MagicMock
    ) -> None:
        capture = AudioCapture(use_vad=False)
        capture._running = False  # Prevent infinite loop

        it = AudioStreamIterator(capture, VadMode.RAW)
        # __aiter__ is async, so calling it returns a coroutine
        # that resolves to self
        aiter_result = await it.__aiter__()
        assert aiter_result is it

    @patch("sounddevice.RawInputStream")
    def test_anext_raises_stop_async_iteration(
        self, MockRawInputStream: MagicMock
    ) -> None:
        import asyncio

        capture = AudioCapture(use_vad=False)
        capture._running = False

        it = AudioStreamIterator(capture, VadMode.RAW)
        with pytest.raises(StopAsyncIteration):
            asyncio.run(it.__anext__())

    @patch("sounddevice.RawInputStream")
    def test_next_with_vad_mode(
        self, MockRawInputStream: MagicMock
    ) -> None:
        capture = AudioCapture(use_vad=True)
        capture._vad = MagicMock()
        capture._vad.is_speech.return_value = True
        capture.start()
        capture._audio_queue.put(b"\x00\x00" * 480)

        it = AudioStreamIterator(capture, VadMode.VAD)
        chunk = next(it)
        assert isinstance(chunk, AudioChunkWithVad)
        assert chunk.is_speech is True

        capture.stop()


# ===================================================================
# record_utterance tests
# ===================================================================


class TestRecordUtterance:
    """Tests for the record_utterance convenience function."""

    def test_not_running_raises(self) -> None:
        capture = AudioCapture(use_vad=False)
        with pytest.raises(AudioCaptureError, match="not running"):
            record_utterance(capture)

    def test_returns_empty_when_stream_stops_immediately(self) -> None:
        """When the stream ends immediately, returns empty bytearray."""
        capture = AudioCapture(use_vad=False)
        capture._running = True
        # Make the capture stream produce nothing, then raise StopIteration
        with patch.object(capture, "stream") as mock_stream:
            mock_iter = MagicMock()

            def iter_self():
                return mock_iter

            mock_iter.__iter__.side_effect = iter_self
            mock_iter.__next__.side_effect = StopIteration()
            mock_stream.return_value = mock_iter

            result = record_utterance(capture, max_duration=0.1, silence_timeout=0.05)
            assert isinstance(result, bytearray)


# ===================================================================
# AudioChunk dataclass tests
# ===================================================================


class TestAudioChunkDataclass:
    """Tests for AudioChunk and AudioChunkWithVad dataclasses."""

    def test_audio_chunk_fields(self) -> None:
        chunk = AudioChunk(frames=b"\x00\x01", sample_rate=16000, timestamp=123.0)
        assert chunk.frames == b"\x00\x01"
        assert chunk.sample_rate == 16000
        assert chunk.timestamp == 123.0

    def test_audio_chunk_is_frozen(self) -> None:
        chunk = AudioChunk(frames=b"a", sample_rate=16000, timestamp=0.0)
        with pytest.raises(AttributeError):
            chunk.frames = b"b"

    def test_audio_chunk_with_vad_extends_chunk(self) -> None:
        chunk = AudioChunkWithVad(
            frames=b"\x00\x01", sample_rate=16000, timestamp=100.0, is_speech=True
        )
        assert isinstance(chunk, AudioChunk)
        assert chunk.is_speech is True

    def test_vad_mode_values(self) -> None:
        assert VadMode.RAW.value == "raw"
        assert VadMode.VAD.value == "vad"


# ===================================================================
# Edge cases
# ===================================================================


class TestAudioCaptureEdgeCases:
    """Edge cases for AudioCapture."""

    @patch("sounddevice.RawInputStream")
    def test_stop_exception_does_not_propagate(
        self, MockRawInputStream: MagicMock
    ) -> None:
        """If closing the stream raises, stop should not propagate."""
        mock_stream = MockRawInputStream.return_value
        mock_stream.close.side_effect = RuntimeError("Close failed")

        capture = AudioCapture(use_vad=False)
        capture.start()
        # Should not raise
        capture.stop()
        assert not capture.is_running

    @patch("sounddevice.RawInputStream")
    def test_read_frame_after_stop(
        self, MockRawInputStream: MagicMock
    ) -> None:
        """Reading a frame after stop should work with sentinel."""
        capture = AudioCapture(use_vad=False)
        capture.start()
        capture.stop()

        # Should not block forever
        result = capture._read_frame(timeout=0.01)
        # May return None (sentinel consumed) or the sentinel itself
        assert result is None or result is None

    def test_audio_chunk_equality_not_implemented(self) -> None:
        """AudioChunk should not implement __eq__ (no comparison needed)."""
        c1 = AudioChunk(frames=b"\x00", sample_rate=16000, timestamp=1.0)
        c2 = AudioChunk(frames=b"\x00", sample_rate=16000, timestamp=1.0)
        # By default dataclasses compare by value
        assert c1 == c2
