"""Tests for VoicePipeline orchestrator."""
import struct

import pytest

from lyra_voice.pipeline import (
    InteractionMode,
    PipelineEvent,
    PipelineState,
    VoicePipeline,
    VoicePipelineConfig,
    VoiceTurn,
)
from lyra_voice.providers import (
    STTProvider,
    STTProviderKind,
    STTResult,
    TTSProvider,
    TTSProviderKind,
    VoiceProviderRegistry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class EchoSTT(STTProvider):
    """STT that echoes audio length as text — always available."""
    kind = STTProviderKind.WHISPER

    async def transcribe(self, audio, config=None):
        return STTResult(
            text=f"transcribed {len(audio)} bytes",
            confidence=0.95,
            language="en",
            duration_ms=len(audio) / 32.0,
        )


class EchoTTS(TTSProvider):
    """TTS that returns text as bytes — always available."""
    kind = TTSProviderKind.KOKORO

    async def synthesize(self, text, config=None):
        return text.encode("utf-8")


def _make_test_audio(duration_ms: int = 100, sample_rate: int = 16000, amplitude: float = 0.5) -> bytes:
    """Generate a sine wave test audio."""
    import math

    num_samples = int(sample_rate * duration_ms / 1000)
    samples = [int(16000 * amplitude * math.sin(2 * math.pi * 440 * i / sample_rate))
               for i in range(num_samples)]
    return struct.pack(f"<{len(samples)}h", *samples)


# ---------------------------------------------------------------------------
# VoicePipeline
# ---------------------------------------------------------------------------


class TestVoicePipeline:
    @pytest.fixture
    def registry(self):
        reg = VoiceProviderRegistry()
        reg.register_stt("default", EchoSTT())
        reg.register_tts("default", EchoTTS())
        return reg

    @pytest.fixture
    def pipeline(self, registry):
        return VoicePipeline(registry=registry, mode=InteractionMode.PUSH_TO_TALK)

    @pytest.mark.asyncio
    async def test_process_audio_speech(self, pipeline):
        audio = _make_test_audio(1000)  # 1 second of loud audio
        turn = await pipeline.process_audio(audio)
        assert turn is not None
        assert "transcribed" in turn.user_text
        assert turn.agent_text == turn.user_text  # echo mode (no agent handler)

    @pytest.mark.asyncio
    async def test_process_audio_silence(self, pipeline):
        silence = b"\x00" * 320
        turn = await pipeline.process_audio(silence)
        assert turn is None  # silence not processed

    @pytest.mark.asyncio
    async def test_process_audio_with_agent_handler(self, pipeline):
        def handler(text: str) -> str:
            return f"Agent says: {text}"

        audio = _make_test_audio(500)
        turn = await pipeline.process_audio(audio, agent_handler=handler)
        assert turn is not None
        assert turn.agent_text.startswith("Agent says:")

    @pytest.mark.asyncio
    async def test_stats_updated(self, pipeline):
        audio = _make_test_audio(500)
        await pipeline.process_audio(audio)
        assert pipeline.stats.total_turns == 1
        assert pipeline.stats.total_errors == 0

    @pytest.mark.asyncio
    async def test_state_transitions(self, pipeline):
        audio = _make_test_audio(500)
        await pipeline.process_audio(audio)
        assert pipeline.state == PipelineState.IDLE

    @pytest.mark.asyncio
    async def test_event_emission(self, pipeline):
        events = []

        async def handler(event, **kwargs):
            events.append(event)

        pipeline.on(PipelineEvent.SPEECH_STARTED, handler)
        pipeline.on(PipelineEvent.STT_COMPLETED, handler)
        pipeline.on(PipelineEvent.TTS_COMPLETED, handler)

        audio = _make_test_audio(500)
        await pipeline.process_audio(audio)

        assert PipelineEvent.SPEECH_STARTED in events
        assert PipelineEvent.STT_COMPLETED in events

    @pytest.mark.asyncio
    async def test_turns_recorded(self, pipeline):
        audio = _make_test_audio(500)
        await pipeline.process_audio(audio)
        assert len(pipeline.turns) == 1
        assert isinstance(pipeline.turns[0], VoiceTurn)

    @pytest.mark.asyncio
    async def test_reset_stats(self, pipeline):
        audio = _make_test_audio(500)
        await pipeline.process_audio(audio)
        pipeline.reset_stats()
        assert pipeline.stats.total_turns == 0
        assert len(pipeline.turns) == 0

    @pytest.mark.asyncio
    async def test_error_handling(self):
        class BrokenSTT(STTProvider):
            kind = STTProviderKind.WHISPER

            async def transcribe(self, audio, config=None):
                raise RuntimeError("STT exploded")

        reg = VoiceProviderRegistry()
        reg.register_stt("default", BrokenSTT())
        reg.register_tts("default", EchoTTS())

        pipeline = VoicePipeline(registry=reg)
        audio = _make_test_audio(500)
        turn = await pipeline.process_audio(audio)
        assert turn is None
        assert pipeline.stats.total_errors == 1


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestVoicePipelineIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline_push_to_talk(self):
        """End-to-end PTT: audio in → text out."""
        reg = VoiceProviderRegistry()
        reg.register_stt("default", EchoSTT())
        reg.register_tts("default", EchoTTS())

        pipeline = VoicePipeline(reg, mode=InteractionMode.PUSH_TO_TALK)

        def uppercase(text: str) -> str:
            return text.upper()

        audio = _make_test_audio(1000)
        turn = await pipeline.push_to_talk(audio, uppercase)
        assert turn is not None
        assert turn.user_text == turn.agent_text.lower()
        assert turn.stt_latency_ms > 0

    @pytest.mark.asyncio
    async def test_streaming_with_barge_in(self):
        """Streaming pipeline handles barge-in gracefully."""
        reg = VoiceProviderRegistry()
        reg.register_stt("default", EchoSTT())
        reg.register_tts("default", EchoTTS())
        # VAD + Turn already registered as "default" by VoiceProviderRegistry

        pipeline = VoicePipeline(reg, mode=InteractionMode.FULL_DUPLEX)

        # Generate chunks: speech → silence → speech → silence
        chunks = [
            _make_test_audio(200),
            _make_test_audio(200),
            _make_test_audio(200),
            b"\x00" * 640,  # silence
            _make_test_audio(200),
            _make_test_audio(200),
            b"\x00" * 640,  # silence
        ]

        async def chunk_stream():
            for c in chunks:
                yield c

        turns = [t async for t in pipeline.process_stream(chunk_stream())]
        assert len(turns) >= 1  # At least one turn completed
