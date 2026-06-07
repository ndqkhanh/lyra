"""Tests for the text-to-speech providers."""
from __future__ import annotations

import pytest

from src.voice.tts import (
    ElevenLabsTTS,
    OpenAITTS,
    TTSProviderLocal,
    TTSError,
    TTSResult,
    VoiceConfig,
)


# ---------------------------------------------------------------------------
# Mock S1 adapter for TTS testing
# ---------------------------------------------------------------------------


class _MockTTSAdapter:
    """Simulates the S1 ``ProviderBackend`` for TTS tests."""

    def __init__(self, response_content: str = "mock audio response") -> None:
        self._response_content = response_content
        self._last_request = None

    async def complete(self, request) -> "_MockTTSResponse":
        self._last_request = request
        return _MockTTSResponse(content=self._response_content)


class _MockTTSResponse:
    """Simulates a ``CompletionResponse`` for TTS testing."""

    def __init__(self, content: str = "") -> None:
        self.content = content
        self.tool_calls = None
        self.usage = None
        self.finish_reason = "end_turn"
        self.model = "test-model"
        self.latency_ms = 100.0


# ---------------------------------------------------------------------------
# OpenAITTS tests
# ---------------------------------------------------------------------------


class TestOpenAITTS:
    """Tests for the OpenAI TTS provider."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio(self) -> None:
        tts = OpenAITTS(openai_adapter=_MockTTSAdapter())
        result = await tts.synthesize("Hello world")

        assert isinstance(result, TTSResult)
        assert len(result.audio_data) > 0
        assert result.sample_rate == 24000

    @pytest.mark.asyncio
    async def test_synthesize_with_custom_voice(self) -> None:
        voice = VoiceConfig(voice_id="echo", name="Echo")
        tts = OpenAITTS(openai_adapter=_MockTTSAdapter(), default_voice=voice)

        assert tts._default_voice.voice_id == "echo"

    @pytest.mark.asyncio
    async def test_available_voices(self) -> None:
        tts = OpenAITTS(openai_adapter=_MockTTSAdapter())

        voices = tts.available_voices
        assert len(voices) == 6
        voice_ids = {v.voice_id for v in voices}
        assert "alloy" in voice_ids
        assert "echo" in voice_ids
        assert "shimmer" in voice_ids

    @pytest.mark.asyncio
    async def test_synthesize_duration_estimate(self) -> None:
        tts = OpenAITTS(openai_adapter=_MockTTSAdapter())
        text = "Hello, this is a test message for TTS synthesis."

        result = await tts.synthesize(text)

        expected_duration = (len(text) / 15) * 1000
        assert abs(result.duration_ms - expected_duration) < expected_duration * 0.1

    @pytest.mark.asyncio
    async def test_synthesize_generates_diagnostic_tone_on_empty_response(self) -> None:
        """When the API returns no parseable audio, the TTS should generate a tone."""
        class _EmptyAdapter:
            async def complete(self, request) -> _MockTTSResponse:
                return _MockTTSResponse(content="No audio data here at all.")

        tts = OpenAITTS(openai_adapter=_EmptyAdapter())
        result = await tts.synthesize("Hello")

        assert len(result.audio_data) > 0
        assert result.sample_rate == 24000

    @pytest.mark.asyncio
    async def test_diagnostic_tone_is_valid_pcm(self) -> None:
        tts = OpenAITTS(openai_adapter=_MockTTSAdapter())

        tone = tts._generate_diagnostic_tone(
            duration_ms=100, sample_rate=16000, frequency=440.0
        )

        # 100ms at 16kHz 16-bit mono = 3200 bytes
        expected_size = int(16000 * 0.1 * 2)
        assert len(tone) == expected_size

    @pytest.mark.asyncio
    async def test_extract_wav_from_text_base64(self) -> None:
        import base64

        dummy_audio = b"\x00\x01\x02\x03" * 100
        b64 = base64.b64encode(dummy_audio).decode("ascii")

        tts = OpenAITTS(openai_adapter=_MockTTSAdapter())
        result = tts._extract_wav_from_text(f"```wav\n{b64}\n```")

        assert result == dummy_audio

    @pytest.mark.asyncio
    async def test_extract_wav_from_text_returns_none_for_plain_text(self) -> None:
        tts = OpenAITTS(openai_adapter=_MockTTSAdapter())
        result = tts._extract_wav_from_text("This is just regular text.")

        assert result is None


# ---------------------------------------------------------------------------
# ElevenLabsTTS tests
# ---------------------------------------------------------------------------


class TestElevenLabsTTS:
    """Tests for the ElevenLabs TTS stub."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio(self) -> None:
        tts = ElevenLabsTTS(api_key="test-key")
        result = await tts.synthesize("Hello world")

        assert isinstance(result, TTSResult)
        assert len(result.audio_data) > 0
        assert result.sample_rate == 24000

    @pytest.mark.asyncio
    async def test_available_voices(self) -> None:
        tts = ElevenLabsTTS()
        voices = tts.available_voices
        assert len(voices) == 4
        assert voices[0].voice_id == "21m00Tcm4TlvDq8ikWAM"

    @pytest.mark.asyncio
    async def test_synthesize_with_custom_sample_rate(self) -> None:
        tts = ElevenLabsTTS()
        result = await tts.synthesize("Test", sample_rate=16000)

        assert result.sample_rate == 16000

    @pytest.mark.asyncio
    async def test_synthesize_duration_scales_with_text_length(self) -> None:
        tts = ElevenLabsTTS()

        short = await tts.synthesize("Hi")
        long_text = await tts.synthesize("This is a much longer sentence for testing purposes.")

        assert long_text.duration_ms > short.duration_ms


# ---------------------------------------------------------------------------
# TTSProviderLocal tests
# ---------------------------------------------------------------------------


class TestTTSProviderLocal:
    """Tests for the local TTS placeholder."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio(self) -> None:
        tts = TTSProviderLocal()
        result = await tts.synthesize("Hello world")

        assert isinstance(result, TTSResult)
        assert len(result.audio_data) > 0

    @pytest.mark.asyncio
    async def test_synthesize_default_voice(self) -> None:
        tts = TTSProviderLocal()
        assert tts._voice.voice_id == "local"

    @pytest.mark.asyncio
    async def test_synthesize_custom_voice(self) -> None:
        voice = VoiceConfig(voice_id="piper", name="Piper TTS")
        tts = TTSProviderLocal(voice=voice)
        assert tts._voice.voice_id == "piper"
