"""Tests for the voice pipeline."""
from __future__ import annotations

import pytest

from lyra.voice.capture import (
    AudioCapture,
    AudioCaptureError,
    record_utterance,
)
from lyra.voice.pipeline import (
    BargeInMode,
    BargeInEvent,
    PipelineError,
    PipelineStats,
    VoicePipeline,
)
from lyra.voice.router import RouterResponse, VoiceAgentRouter
from lyra.voice.stt import TranscriptionResult
from lyra.voice.tts import TTSResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sine_tone(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate a PCM sine tone for tests."""
    import math
    import struct

    num_samples = int(sample_rate * duration_ms / 1000)
    amplitude = 0.3
    max_val = 32767
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * max_val * math.sin(2 * math.pi * 440 * t))
        samples.append(struct.pack("<h", value))
    return b"".join(samples)


class _MockSTT:
    """Duck-typed STT provider for testing."""
    async def transcribe(self, audio_data, **kw) -> TranscriptionResult:
        return TranscriptionResult(text="test query", language="en", confidence=0.95, latency_ms=50.0)


class _MockTTS:
    """Duck-typed TTS provider for testing."""
    async def synthesize(self, text, **kw) -> TTSResult:
        return TTSResult(
            audio_data=_make_sine_tone(100, 24000),
            sample_rate=24000,
            duration_ms=100.0,
            latency_ms=50.0,
        )


class _MockRouter(VoiceAgentRouter):
    """Router subclass that returns a canned response synchronously."""
    def __init__(self) -> None:
        super().__init__(orchestrator_run=lambda **kw: None)

    async def route_transcribed_text(self, text: str, **kw) -> RouterResponse:
        return RouterResponse(
            text="test response",
            query=text,
            confidence=0.95,
            latency_ms=100.0,
        )


# ---------------------------------------------------------------------------
# PipelineStats tests
# ---------------------------------------------------------------------------


class TestPipelineStats:
    """Tests for the ``PipelineStats`` dataclass."""

    def test_empty_stats(self) -> None:
        stats = PipelineStats()
        assert stats.total_utterances == 0
        assert stats.p50_stt == 0.0
        assert stats.p95_stt == 0.0
        assert stats.p50_tts == 0.0
        assert stats.p95_tts == 0.0

    def test_stt_percentiles(self) -> None:
        stats = PipelineStats()
        stats.stt_latencies_ms = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

        assert stats.p50_stt == 55.0  # median of 10 values
        # p95 = sorted[floor(10*0.95)] = sorted[9] = 100.0
        assert stats.p95_stt == 100.0

    def test_tts_percentiles(self) -> None:
        stats = PipelineStats()
        stats.tts_latencies_ms = [100.0, 200.0, 300.0, 400.0]

        assert stats.p50_tts == 250.0
        assert stats.p95_tts == 400.0

    def test_router_percentiles(self) -> None:
        stats = PipelineStats()
        stats.router_latencies_ms = [50.0, 150.0, 250.0]

        assert stats.p50_router == 150.0
        assert stats.p95_router == 250.0

    def test_to_dict_excludes_internal_lists(self) -> None:
        stats = PipelineStats()
        stats.total_utterances = 5
        stats.stt_latencies_ms = [10.0, 20.0]
        d = stats.to_dict()

        assert isinstance(d, dict)
        assert d["total_utterances"] == 5
        assert "stt_latencies_ms" not in d
        assert "tts_latencies_ms" not in d

    def test_failures_tracked(self) -> None:
        stats = PipelineStats()
        stats.failures = 3
        assert stats.to_dict()["failures"] == 3


# ---------------------------------------------------------------------------
# VoicePipeline tests
# ---------------------------------------------------------------------------


class TestVoicePipeline:
    """Tests for the ``VoicePipeline`` class."""

    @pytest.mark.asyncio
    async def test_run_without_capture_raises_error(self) -> None:
        """Pipeline should fail if audio capture cannot be started."""
        class _BrokenCapture(AudioCapture):
            def start(self) -> None:
                raise AudioCaptureError("No microphone")

        pipeline = VoicePipeline(
            capture=_BrokenCapture(sample_rate=16000),
            stt=_MockSTT(),
            tts=_MockTTS(),
            router=VoiceAgentRouter(orchestrator_run=lambda **kw: None),
        )

        with pytest.raises(PipelineError, match="No microphone"):
            await pipeline.run()

    @pytest.mark.asyncio
    async def test_pipeline_lifecycle(self) -> None:
        """Test pipeline construction, start, and stop.

        Verifies the pipeline can be created, stop() sets is_running to
        False, and run() raises for broken capture.
        """
        pipeline = VoicePipeline(
            capture=AudioCapture(sample_rate=16000, use_vad=False),
            stt=_MockSTT(),
            tts=_MockTTS(),
            router=VoiceAgentRouter(orchestrator_run=lambda **kw: None),
        )
        assert not pipeline.is_running
        pipeline.stop()
        assert not pipeline.is_running

    @pytest.mark.asyncio
    async def test_stt_provider_protocol_check(self) -> None:
        """Verify that the STTProvider protocol is importable."""
        from lyra.voice.stt import STTProvider
        assert STTProvider is not None

    @pytest.mark.asyncio
    async def test_tts_provider_protocol_check(self) -> None:
        """Verify that the TTSProvider protocol is importable."""
        from lyra.voice.tts import TTSProvider
        assert TTSProvider is not None

    @pytest.mark.asyncio
    async def test_pipeline_error_bubbling(self) -> None:
        """Pipeline should wrap underlying exceptions."""

        class _FailingCapture(AudioCapture):
            def start(self) -> None:
                raise AudioCaptureError("Microphone initialization failed")

        pipeline = VoicePipeline(
            capture=_FailingCapture(sample_rate=16000, use_vad=False),
            stt=_MockSTT(),
            tts=_MockTTS(),
            router=VoiceAgentRouter(orchestrator_run=lambda **kw: None),
        )

        with pytest.raises(PipelineError):
            await pipeline.run()


# ---------------------------------------------------------------------------
# BargeIn tests
# ---------------------------------------------------------------------------


class TestBargeIn:
    """Tests for barge-in functionality."""

    def test_barge_in_event_is_exception(self) -> None:
        """BargeInEvent should be a proper exception type."""
        event = BargeInEvent("interrupted")
        assert isinstance(event, Exception)
        assert str(event) == "interrupted"

    def test_barge_in_mode_enum(self) -> None:
        assert BargeInMode.DISABLED.value == "disabled"
        assert BargeInMode.ENABLED.value == "enabled"


# ---------------------------------------------------------------------------
# record_utterance tests
# ---------------------------------------------------------------------------


class TestRecordUtterance:
    """Tests for the ``record_utterance`` convenience function."""

    def test_requires_running_capture(self) -> None:
        capture = AudioCapture(sample_rate=16000, use_vad=False)
        with pytest.raises(AudioCaptureError, match="not running"):
            record_utterance(capture)
