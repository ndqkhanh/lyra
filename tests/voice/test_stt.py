"""Tests for the speech-to-text providers."""
from __future__ import annotations

import pytest

from lyra.voice.stt import (
    AnthropicSTT,
    DeepSeekSTT,
    OpenAISTT,
    STTError,
    TranscriptionResult,
    _pcm_to_wav,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_audio() -> bytes:
    """Generate a short 16-bit 16kHz mono PCM sine tone for STT testing."""
    import math
    import struct

    sample_rate = 16000
    duration_ms = 200  # 200 ms
    num_samples = int(sample_rate * duration_ms / 1000)
    frequency = 440.0
    amplitude = 0.5
    max_val = 32767

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * max_val * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack("<h", value))

    return b"".join(samples)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestPcmToWav:
    """Tests for the PCM-to-WAV conversion helper."""

    def test_wav_header_is_44_bytes(self, sample_audio: bytes) -> None:
        wav = _pcm_to_wav(sample_audio, 16000)
        assert len(wav) == len(sample_audio) + 44

    def test_wav_has_riff_marker(self, sample_audio: bytes) -> None:
        wav = _pcm_to_wav(sample_audio, 16000)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_wav_format_is_pcm(self, sample_audio: bytes) -> None:
        wav = _pcm_to_wav(sample_audio, 16000)
        # Format tag at offset 20
        assert wav[20:22] == b"\x01\x00"

    def test_wav_mono_16bit(self, sample_audio: bytes) -> None:
        wav = _pcm_to_wav(sample_audio, 16000)
        # Channels at offset 22, bits per sample at offset 34
        assert wav[22:24] == b"\x01\x00"
        assert wav[34:36] == b"\x10\x00"


# ---------------------------------------------------------------------------
# Mock S1 provider adapter
# ---------------------------------------------------------------------------


class _MockCompletionResponse:
    """Simulates a minimal ``CompletionResponse`` for STT testing."""

    def __init__(self, content: str = "hello world") -> None:
        self.content = content
        self.tool_calls = None
        self.usage = None
        self.finish_reason = "end_turn"
        self.model = "test-model"
        self.latency_ms = 50.0


class _MockAdapter:
    """Simulates the S1 ``ProviderBackend`` interface with configurable return values."""

    def __init__(self, response_text: str = "hello world") -> None:
        self._response_text = response_text
        self._last_request = None

    @property
    def provider_name(self) -> str:
        return "mock"

    async def complete(self, request) -> _MockCompletionResponse:
        self._last_request = request
        return _MockCompletionResponse(content=self._response_text)


# ---------------------------------------------------------------------------
# AnthropicSTT tests
# ---------------------------------------------------------------------------


class TestAnthropicSTT:
    """Tests for the Anthropic STT provider."""

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="transcribed text")
        stt = AnthropicSTT(anthropic_adapter=mock_adapter)

        result = await stt.transcribe(sample_audio)

        assert isinstance(result, TranscriptionResult)
        assert result.text == "transcribed text"
        assert result.language == "en"
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_transcribe_sends_request(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="test")
        stt = AnthropicSTT(anthropic_adapter=mock_adapter)

        await stt.transcribe(sample_audio)

        assert mock_adapter._last_request is not None
        assert mock_adapter._last_request.model == "claude-sonnet-4-6"
        assert mock_adapter._last_request.temperature == 0.0
        assert len(mock_adapter._last_request.messages) == 1

    @pytest.mark.asyncio
    async def test_transcribe_error_propagation(self, sample_audio: bytes) -> None:
        class _FailingAdapter:
            async def complete(self, request) -> None:
                raise RuntimeError("API error")

        stt = AnthropicSTT(anthropic_adapter=_FailingAdapter())

        with pytest.raises(STTError, match="API error"):
            await stt.transcribe(sample_audio)

    @pytest.mark.asyncio
    async def test_transcribe_with_language_hint(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="hola")
        stt = AnthropicSTT(anthropic_adapter=mock_adapter)

        result = await stt.transcribe(sample_audio, language="es")

        assert result.language == "es"
        assert "language: es" in mock_adapter._last_request.messages[0].content

    @pytest.mark.asyncio
    async def test_transcribe_duration_estimate(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="test")
        stt = AnthropicSTT(anthropic_adapter=mock_adapter)

        result = await stt.transcribe(sample_audio)

        expected_duration = (len(sample_audio) / (16000 * 2)) * 1000
        assert abs(result.duration_ms - expected_duration) < 1.0


# ---------------------------------------------------------------------------
# OpenAISTT tests
# ---------------------------------------------------------------------------


class TestOpenAISTT:
    """Tests for the OpenAI STT provider (Whisper via S1)."""

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="transcribed")
        stt = OpenAISTT(openai_adapter=mock_adapter)

        result = await stt.transcribe(sample_audio)

        assert result.text == "transcribed"
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_transcribe_sends_system_message(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="test")
        stt = OpenAISTT(openai_adapter=mock_adapter)

        await stt.transcribe(sample_audio)

        assert mock_adapter._last_request is not None
        messages = mock_adapter._last_request.messages
        assert messages[0].role == "system"
        assert "Transcribe" in messages[0].content

    @pytest.mark.asyncio
    async def test_transcribe_error_propagation(self, sample_audio: bytes) -> None:
        class _FailingAdapter:
            async def complete(self, request) -> None:
                raise ConnectionError("Network error")

        stt = OpenAISTT(openai_adapter=_FailingAdapter())

        with pytest.raises(STTError, match="Network error"):
            await stt.transcribe(sample_audio)


# ---------------------------------------------------------------------------
# DeepSeekSTT tests
# ---------------------------------------------------------------------------


class TestDeepSeekSTT:
    """Tests for the DeepSeek STT provider."""

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="deepseek transcription")
        stt = DeepSeekSTT(deepseek_adapter=mock_adapter)

        result = await stt.transcribe(sample_audio)

        assert result.text == "deepseek transcription"
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_transcribe_sends_long_prompt(self, sample_audio: bytes) -> None:
        mock_adapter = _MockAdapter(response_text="test")
        stt = DeepSeekSTT(deepseek_adapter=mock_adapter)

        await stt.transcribe(sample_audio)

        assert mock_adapter._last_request is not None
        content = mock_adapter._last_request.messages[0].content
        assert "base64" in content.lower()
        assert "transcribe" in content.lower()

    @pytest.mark.asyncio
    async def test_transcribe_error_propagation(self, sample_audio: bytes) -> None:
        class _FailingAdapter:
            async def complete(self, request) -> None:
                raise TimeoutError("Request timed out")

        stt = DeepSeekSTT(deepseek_adapter=_FailingAdapter())

        with pytest.raises(STTError):
            await stt.transcribe(sample_audio)
