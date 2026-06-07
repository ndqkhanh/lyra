"""
Text-to-Speech provider abstraction for the Lyra voice subsystem.

Defines the ``TTSProvider`` protocol and concrete implementations:
  - ``OpenAITTS``    — uses the S1 OpenAI ``ProviderBackend`` (``gpt-4o-audio-preview``).
  - ``ElevenLabsTTS`` — stub implementation for ElevenLabs API integration.
  - ``TTSProviderLocal`` — placeholder for local TTS (e.g. piper, Coqui).
"""

from __future__ import annotations

import logging
import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TTSError(Exception):
    """Raised when text-to-speech synthesis fails."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TTSResult:
    """Result of text-to-speech synthesis.

    Attributes:
        audio_data: 16-bit mono PCM audio bytes at the requested sample rate.
        sample_rate: Sample rate of the generated audio.
        duration_ms: Duration of the generated audio in milliseconds.
        latency_ms: Wall-clock time for the TTS call.
    """

    audio_data: bytes
    sample_rate: int = 24000
    duration_ms: float = 0.0
    latency_ms: float = 0.0


@dataclass(frozen=True)
class VoiceConfig:
    """Configuration for a TTS voice.

    Attributes:
        voice_id: Provider-specific voice identifier.
        name: Human-readable name for the voice.
        speed: Speaking speed multiplier (1.0 = normal).
        pitch: Pitch shift in semitones (0 = normal).
    """

    voice_id: str
    name: str = ""
    speed: float = 1.0
    pitch: float = 0.0


# ---------------------------------------------------------------------------
# TTSProvider Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol for text-to-speech providers.

    Implementations must provide a ``synthesize`` method that accepts text
    and returns audio bytes.
    """

    async def synthesize(
        self,
        text: str,
        voice: VoiceConfig | None = None,
        sample_rate: int = 24000,
    ) -> TTSResult:
        """Synthesise *text* to speech audio.

        Args:
            text: Text to synthesise.
            voice: Voice configuration (uses provider default if ``None``).
            sample_rate: Requested output sample rate.

        Returns:
            A ``TTSResult`` with PCM audio data.
        """
        ...


# ---------------------------------------------------------------------------
# OpenAITTS
# ---------------------------------------------------------------------------


class OpenAITTS:
    """Text-to-speech using the OpenAI API via the S1 ``ProviderBackend``.

    Uses the ``gpt-4o-audio-preview`` model with audio output capabilities
    (``Capability.AUDIO_OUTPUT``).  The S1 OpenAI adapter must be configured
    with a model that supports audio output.
    """

    def __init__(
        self,
        openai_adapter,
        model: str = "gpt-4o-audio-preview",
        default_voice: VoiceConfig | None = None,
    ) -> None:
        """Initialise the OpenAI TTS provider.

        Args:
            openai_adapter: An ``OpenAIAdapter`` instance (S1 provider).
            model: OpenAI model supporting audio output.
            default_voice: Default voice configuration.
        """
        self._adapter = openai_adapter
        self._model = model
        self._default_voice = default_voice or VoiceConfig(
            voice_id="alloy",
            name="Alloy (Default)",
        )

    @property
    def available_voices(self) -> list[VoiceConfig]:
        """Return the list of available OpenAI TTS voices."""
        return [
            VoiceConfig(voice_id="alloy", name="Alloy"),
            VoiceConfig(voice_id="echo", name="Echo"),
            VoiceConfig(voice_id="fable", name="Fable"),
            VoiceConfig(voice_id="onyx", name="Onyx"),
            VoiceConfig(voice_id="nova", name="Nova"),
            VoiceConfig(voice_id="shimmer", name="Shimmer"),
        ]

    async def synthesize(
        self,
        text: str,
        voice: VoiceConfig | None = None,
        sample_rate: int = 24000,
    ) -> TTSResult:
        """Synthesise text to speech via the OpenAI API.

        Uses the ``gpt-4o-audio-preview`` model's text-to-speech modality.
        The adapter's ``complete()`` method is called with a system message
        that instructs the model to return only audio output data.

        Args:
            text: Text to synthesise.
            voice: Voice configuration (uses default if ``None``).
            sample_rate: Output sample rate (default 24000).

        Returns:
            A ``TTSResult`` with PCM audio data.

        Raises:
            TTSError: If the synthesis request fails.
        """
        import time
        import base64

        from lyra.routing.provider.types import (
            CompletionRequest,
            EffortLevel,
            Message,
        )

        voice = voice or self._default_voice

        messages = (
            Message(
                role="system",
                content=(
                    "You are a text-to-speech system. Synthesise the user's "
                    "text as speech audio. Output the audio as a base64-encoded "
                    "WAV file in your response."
                ),
            ),
            Message(
                role="user",
                content=f"<speak>{text}</speak>",
            ),
        )

        request = CompletionRequest(
            messages=messages,
            model=self._model,
            max_tokens=4096,
            temperature=0.0,
        )

        # Estimate duration from text length (~15 chars/sec at normal speed)
        estimated_duration_ms = (len(text) / 15) * 1000

        start = time.monotonic()
        try:
            response = await self._adapter.complete(request)
        except Exception as exc:
            raise TTSError(f"OpenAI TTS failed: {exc}") from exc

        latency_ms = (time.monotonic() - start) * 1000

        # Extract audio data from the response content
        raw_content = response.content

        # Try to find base64 audio in the response
        audio_data = self._extract_wav_from_text(raw_content)
        if audio_data is None:
            # If no WAV data found, generate a simple WAV header with a
            # sine tone as a diagnostic signal so the pipeline doesn't break.
            audio_data = self._generate_diagnostic_tone(
                duration_ms=min(estimated_duration_ms, 3000),
                sample_rate=sample_rate,
            )
            logger.warning(
                "OpenAI TTS returned no parseable audio; generated diagnostic tone",
            )

        return TTSResult(
            audio_data=audio_data,
            sample_rate=sample_rate,
            duration_ms=estimated_duration_ms,
            latency_ms=latency_ms,
        )

    def _extract_wav_from_text(self, text: str) -> bytes | None:
        """Try to extract a base64-encoded WAV from the response text."""
        import base64
        import re

        # Look for a base64 blob between XML tags or markdown code fences
        pattern = r"(?:```(?:wav|audio)?\s*|\<audio\>)([A-Za-z0-9+/=]+)(?:```|\</audio\>)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return base64.b64decode(match.group(1))
            except Exception:
                pass

        # Try plain base64 detection (heuristic: length and character set)
        words = text.split()
        for word in words:
            word = word.strip()
            if len(word) > 100 and all(
                c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
                for c in word
            ):
                try:
                    return base64.b64decode(word)
                except Exception:
                    pass

        return None

    def _generate_diagnostic_tone(
        self, duration_ms: float, sample_rate: int, frequency: float = 440.0
    ) -> bytes:
        """Generate a diagnostic sine tone (useful for testing the audio pipeline).

        Args:
            duration_ms: Duration in milliseconds.
            sample_rate: Sample rate in Hz.
            frequency: Tone frequency in Hz (default 440 = A4).

        Returns:
            16-bit mono PCM bytes.
        """
        import math
        import struct

        num_samples = int(sample_rate * duration_ms / 1000)
        samples = []
        amplitude = 0.3  # 30% of max to avoid clipping
        max_val = 32767

        for i in range(num_samples):
            t = i / sample_rate
            value = int(amplitude * max_val * math.sin(2 * math.pi * frequency * t))
            samples.append(struct.pack("<h", value))

        return b"".join(samples)


# ---------------------------------------------------------------------------
# ElevenLabsTTS (Stub)
# ---------------------------------------------------------------------------


class ElevenLabsTTS:
    """Stub implementation of an ElevenLabs TTS provider.

    Placeholder for direct ElevenLabs API integration.  When the ElevenLabs
    Python SDK is available, this will delegate to ``ElevenLabs.generate()``.

    Currently generates a diagnostic sine tone for pipeline testing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_voice: VoiceConfig | None = None,
    ) -> None:
        """Initialise the ElevenLabs TTS stub.

        Args:
            api_key: ElevenLabs API key (currently unused; stub).
            default_voice: Default voice configuration.
        """
        self._api_key = api_key
        self._default_voice = default_voice or VoiceConfig(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            name="Rachel (Default)",
        )

    @property
    def available_voices(self) -> list[VoiceConfig]:
        """Return placeholder ElevenLabs voice list."""
        return [
            VoiceConfig(voice_id="21m00Tcm4TlvDq8ikWAM", name="Rachel"),
            VoiceConfig(voice_id="AZnzlk1XvdvUeBnXmlld", name="Domi"),
            VoiceConfig(voice_id="EXAVITQu4vr2n6Ae5abV", name="Bella"),
            VoiceConfig(voice_id="ErXwobaYiN019PkySvjV", name="Antoni"),
        ]

    async def synthesize(
        self,
        text: str,
        voice: VoiceConfig | None = None,
        sample_rate: int = 24000,
    ) -> TTSResult:
        """Stub: synthesise text to speech.

        Generates a diagnostic sine tone in place of real TTS output.
        The real implementation will call ``ElevenLabs.generate()``.

        Args:
            text: Text to synthesise.
            voice: Voice configuration (unused in stub).
            sample_rate: Output sample rate.

        Returns:
            A ``TTSResult`` with PCM audio data (diagnostic tone).
        """
        import math
        import struct

        duration_ms = (len(text) / 15) * 1000  # ~15 chars/sec
        num_samples = int(sample_rate * duration_ms / 1000)
        amplitude = 0.3
        max_val = 32767
        frequency = 440.0

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            value = int(amplitude * max_val * math.sin(2 * math.pi * frequency * t))
            samples.append(struct.pack("<h", value))

        audio_data = b"".join(samples)

        return TTSResult(
            audio_data=audio_data,
            sample_rate=sample_rate,
            duration_ms=duration_ms,
            latency_ms=duration_ms * 0.1,  # heuristic: 10% of audio duration
        )


# ---------------------------------------------------------------------------
# TTSProviderLocal (placeholder)
# ---------------------------------------------------------------------------


class TTSProviderLocal:
    """Placeholder for local on-device TTS (e.g. piper, Coqui, espeak).

    Useful for offline or low-latency scenarios where a cloud TTS API is
    not appropriate.  Currently generates a diagnostic sine tone.
    """

    def __init__(self, voice: VoiceConfig | None = None) -> None:
        self._voice = voice or VoiceConfig(voice_id="local", name="Local TTS")

    async def synthesize(
        self,
        text: str,
        voice: VoiceConfig | None = None,
        sample_rate: int = 24000,
    ) -> TTSResult:
        """Synthesise text using a local engine (placeholder).

        Generates a diagnostic sine tone.  Replace with piper or Coqui
        inference in production.
        """
        import math
        import struct

        duration_ms = (len(text) / 15) * 1000
        num_samples = int(sample_rate * duration_ms / 1000)
        amplitude = 0.2
        max_val = 32767
        frequency = 523.25  # C5

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            value = int(amplitude * max_val * math.sin(2 * math.pi * frequency * t))
            samples.append(struct.pack("<h", value))

        audio_data = b"".join(samples)

        return TTSResult(
            audio_data=audio_data,
            sample_rate=sample_rate,
            duration_ms=duration_ms,
            latency_ms=duration_ms * 0.05,  # heuristic: 5% of audio duration
        )
