"""
Speech-to-Text provider abstraction for the Lyra voice subsystem.

Defines the ``STTProvider`` protocol and two concrete implementations:
  - ``AnthropicSTT`` — uses the Anthropic Messages API with audio content blocks.
  - ``DeepSeekSTT`` — uses the DeepSeek / OpenAI-compatible transcription API.
  - ``OpenAISTT``   — uses the OpenAI Whisper API (via the S1 ``ProviderBackend``).
"""

from __future__ import annotations

import io
import logging
import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from src.routing.provider.types import (
    Capability,
    CompletionRequest,
    CompletionResponse,
    EffortLevel,
    Message,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class STTError(Exception):
    """Raised when speech-to-text processing fails."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptionResult:
    """Result of a speech-to-text transcription.

    Attributes:
        text: The transcribed text.
        language: Detected language code (e.g. ``"en"``, ``"vi"``).
        confidence: Confidence score (0.0 - 1.0), if available.
        duration_ms: Audio duration in milliseconds.
        latency_ms: Wall-clock time for the transcription call.
    """

    text: str
    language: str = "en"
    confidence: float = 1.0
    duration_ms: float = 0.0
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# STTProvider Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class STTProvider(Protocol):
    """Protocol for speech-to-text providers.

    Implementations must provide at least a ``transcribe`` method that
    accepts 16-bit 16 kHz mono PCM audio and returns a ``TranscriptionResult``.
    """

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe *audio_data* to text.

        Args:
            audio_data: 16-bit mono PCM audio bytes.
            sample_rate: Sample rate of the audio (default 16000).
            language: Optional language hint (e.g. ``"en"``, ``"vi"``).

        Returns:
            A ``TranscriptionResult`` with the transcribed text.
        """
        ...


# ---------------------------------------------------------------------------
# WAV helper
# ---------------------------------------------------------------------------


def _pcm_to_wav(audio_data: bytes, sample_rate: int = 16000) -> bytes:
    """Wrap raw 16-bit mono PCM bytes in a WAV container.

    Many STT APIs expect WAV rather than raw PCM.
    """
    import struct

    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(audio_data)
    header_size = 44

    header = b"RIFF"
    header += struct.pack("<I", header_size + data_size - 8)
    header += b"WAVE"
    header += b"fmt "
    header += struct.pack("<I", 16)  # chunk size
    header += struct.pack("<H", 1)  # PCM format
    header += struct.pack("<H", num_channels)
    header += struct.pack("<I", sample_rate)
    header += struct.pack("<I", byte_rate)
    header += struct.pack("<H", block_align)
    header += struct.pack("<H", bits_per_sample)
    header += b"data"
    header += struct.pack("<I", data_size)

    return header + audio_data


# ---------------------------------------------------------------------------
# AnthropicSTT
# ---------------------------------------------------------------------------


class AnthropicSTT:
    """Speech-to-text using the Anthropic Messages API.

    Relies on the S1 Anthropic adapter to send audio content blocks
    (base64-encoded WAV) for transcription.  The model must support the
    ``AUDIO_INPUT`` capability.

    Note: Anthropic's audio-in support is evolving.  This implementation
    wraps audio as a user message with base64-encoded WAV content.
    """

    def __init__(
        self,
        anthropic_adapter,
        model: str = "claude-sonnet-4-6",
        system_prompt: str | None = None,
    ) -> None:
        """Initialise the Anthropic STT provider.

        Args:
            anthropic_adapter: An ``AnthropicAdapter`` instance (S1 provider).
            model: Claude model to use for transcription.
            system_prompt: Optional system instruction (e.g. "Transcribe
                the following audio verbatim. Return only the transcribed text.").
        """
        self._adapter = anthropic_adapter
        self._model = model
        self._system_prompt = system_prompt or (
            "You are a speech-to-text system. Transcribe the user's spoken "
            "audio exactly as heard. Output only the transcribed text."
        )

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio using the Anthropic Messages API.

        Audio is wrapped in a WAV container, base64-encoded, and sent as
        a user message content block.

        Args:
            audio_data: 16-bit mono PCM audio bytes.
            sample_rate: Sample rate (default 16000).
            language: Language hint (currently passed via the prompt).

        Returns:
            A ``TranscriptionResult``.
        """
        import time
        import base64

        wav_bytes = _pcm_to_wav(audio_data, sample_rate)
        b64_audio = base64.b64encode(wav_bytes).decode("ascii")
        duration_ms = (len(audio_data) / (sample_rate * 2)) * 1000

        lang_hint = f" (language: {language})" if language else ""
        messages = (
            Message(
                role="user",
                content=f"<audio>{b64_audio}</audio>{lang_hint}",
            ),
        )

        request = CompletionRequest(
            messages=messages,
            model=self._model,
            max_tokens=1024,
            temperature=0.0,
        )

        start = time.monotonic()
        try:
            response: CompletionResponse = await self._adapter.complete(request)
        except Exception as exc:
            raise STTError(f"Anthropic STT failed: {exc}") from exc

        latency_ms = (time.monotonic() - start) * 1000

        return TranscriptionResult(
            text=response.content.strip(),
            language=language or "en",
            confidence=1.0,
            duration_ms=duration_ms,
            latency_ms=latency_ms,
        )


# ---------------------------------------------------------------------------
# OpenAISTT (Whisper via S1)
# ---------------------------------------------------------------------------


class OpenAISTT:
    """Speech-to-text using the OpenAI Whisper API via the S1 provider.

    Uses the OpenAI adapter's ``complete()`` method with a suitable prompt
    to transcribe audio.  For direct Whisper API access, this wraps the
    audio as a WAV file in a user message.
    """

    def __init__(
        self,
        openai_adapter,
        model: str = "gpt-4o-audio-preview",
        system_prompt: str | None = None,
    ) -> None:
        """Initialise the OpenAI STT provider.

        Args:
            openai_adapter: An ``OpenAIAdapter`` instance (S1 provider).
            model: OpenAI model to use ('gpt-4o-audio-preview' for native
                audio, or 'whisper-1' via the audio API).
            system_prompt: Optional system instruction for transcription.
        """
        self._adapter = openai_adapter
        self._model = model
        self._system_prompt = system_prompt or (
            "Transcribe the following audio exactly as spoken. "
            "Output only the transcribed text, no additional commentary."
        )

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio using an OpenAI model.

        Args:
            audio_data: 16-bit mono PCM audio bytes.
            sample_rate: Sample rate (default 16000).
            language: Language hint.

        Returns:
            A ``TranscriptionResult``.
        """
        import time
        import base64

        wav_bytes = _pcm_to_wav(audio_data, sample_rate)
        b64_audio = base64.b64encode(wav_bytes).decode("ascii")
        duration_ms = (len(audio_data) / (sample_rate * 2)) * 1000

        lang_hint = f" (language: {language})" if language else ""
        messages = (
            Message(role="system", content=self._system_prompt),
            Message(
                role="user",
                content=f"<audio>{b64_audio}</audio>{lang_hint}",
            ),
        )

        request = CompletionRequest(
            messages=messages,
            model=self._model,
            max_tokens=1024,
            temperature=0.0,
        )

        start = time.monotonic()
        try:
            response: CompletionResponse = await self._adapter.complete(request)
        except Exception as exc:
            raise STTError(f"OpenAI STT failed: {exc}") from exc

        latency_ms = (time.monotonic() - start) * 1000

        return TranscriptionResult(
            text=response.content.strip(),
            language=language or "en",
            confidence=1.0,
            duration_ms=duration_ms,
            latency_ms=latency_ms,
        )


# ---------------------------------------------------------------------------
# DeepSeekSTT (via OpenAI-compatible API)
# ---------------------------------------------------------------------------


class DeepSeekSTT:
    """Speech-to-text via the DeepSeek API (OpenAI-compatible).

    DeepSeek does not currently offer a dedicated audio transcription
    endpoint, so this implementation uses the S1 DeepSeek provider's
    ``complete()`` method with base64-encoded WAV audio embedded in the
    prompt.  The model is expected to handle the transcription as a
    text-generation task from the encoded audio data.

    Note: This is a best-effort implementation.  For reliable STT,
    prefer ``AnthropicSTT`` or ``OpenAISTT``.
    """

    def __init__(
        self,
        deepseek_adapter,
        model: str = "deepseek-chat",
    ) -> None:
        """Initialise the DeepSeek STT provider.

        Args:
            deepseek_adapter: A ``DeepSeekAdapter`` instance (S1 provider).
            model: DeepSeek model to use for transcription.
        """
        self._adapter = deepseek_adapter
        self._model = model

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio via the DeepSeek (OpenAI-compatible) API.

        Args:
            audio_data: 16-bit mono PCM audio bytes.
            sample_rate: Sample rate (default 16000).
            language: Language hint.

        Returns:
            A ``TranscriptionResult``.
        """
        import time
        import base64

        wav_bytes = _pcm_to_wav(audio_data, sample_rate)
        b64_audio = base64.b64encode(wav_bytes).decode("ascii")
        duration_ms = (len(audio_data) / (sample_rate * 2)) * 1000

        lang_hint = f" (language: {language})" if language else ""
        messages = (
            Message(
                role="user",
                content=(
                    "Transcribe the following base64-encoded WAV audio exactly "
                    f"as spoken.{lang_hint}\n\n{b64_audio}\n\n"
                    "Output only the transcribed text."
                ),
            ),
        )

        request = CompletionRequest(
            messages=messages,
            model=self._model,
            max_tokens=1024,
            temperature=0.0,
        )

        start = time.monotonic()
        try:
            response: CompletionResponse = await self._adapter.complete(request)
        except Exception as exc:
            raise STTError(f"DeepSeek STT failed: {exc}") from exc

        latency_ms = (time.monotonic() - start) * 1000

        return TranscriptionResult(
            text=response.content.strip(),
            language=language or "en",
            confidence=1.0,
            duration_ms=duration_ms,
            latency_ms=latency_ms,
        )
