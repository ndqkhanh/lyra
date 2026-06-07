"""
Voice pipeline -- end-to-end streaming pipeline for voice interaction.

Pipeline flow::

    Capture → VAD → STT → Agent Router → TTS → Playback

Supports streaming mode with barge-in (user interrupts the assistant)
and configurable latency tracking (p50/p95).
"""

from __future__ import annotations

import asyncio
import logging
import structlog
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from statistics import median
from typing import Any

from src.voice.capture import (
    AudioCapture,
    AudioChunk,
    AudioChunkWithVad,
    VadMode,
    record_utterance,
)
from src.voice.router import RouterError, RouterResponse, VoiceAgentRouter
from src.voice.stt import STTProvider, TranscriptionResult, STTError
from src.voice.tts import TTSProvider, TTSResult, TTSError

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PipelineError(Exception):
    """Raised when the voice pipeline encounters a runtime error."""


class BargeInEvent(Exception):
    """Raised internally when the user interrupts the assistant's speech."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PipelineStats:
    """Statistics for the voice pipeline.

    Attributes:
        total_utterances: Total number of utterances processed.
        total_stt_latency_ms: Total STT latency across all utterances.
        total_tts_latency_ms: Total TTS latency across all utterances.
        total_router_latency_ms: Total router latency across all utterances.
        stt_latencies_ms: List of individual STT latencies for percentile calc.
        tts_latencies_ms: List of individual TTS latencies for percentile calc.
        router_latencies_ms: List of individual router latencies.
        total_pipeline_latency_ms: Total end-to-end time.
        failures: Number of pipeline failures.
        start_time: Monotonic timestamp when the pipeline started.
    """

    total_utterances: int = 0
    total_stt_latency_ms: float = 0.0
    total_tts_latency_ms: float = 0.0
    total_router_latency_ms: float = 0.0
    stt_latencies_ms: list[float] = field(default_factory=list)
    tts_latencies_ms: list[float] = field(default_factory=list)
    router_latencies_ms: list[float] = field(default_factory=list)
    total_pipeline_latency_ms: float = 0.0
    failures: int = 0
    start_time: float = 0.0

    @property
    def p50_stt(self) -> float:
        """Median STT latency in milliseconds."""
        return median(self.stt_latencies_ms) if self.stt_latencies_ms else 0.0

    @property
    def p95_stt(self) -> float:
        """95th percentile STT latency in milliseconds."""
        if not self.stt_latencies_ms:
            return 0.0
        sorted_lat = sorted(self.stt_latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx]

    @property
    def p50_tts(self) -> float:
        """Median TTS latency in milliseconds."""
        return median(self.tts_latencies_ms) if self.tts_latencies_ms else 0.0

    @property
    def p95_tts(self) -> float:
        """95th percentile TTS latency in milliseconds."""
        if not self.tts_latencies_ms:
            return 0.0
        sorted_lat = sorted(self.tts_latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx]

    @property
    def p50_router(self) -> float:
        """Median router latency in milliseconds."""
        return median(self.router_latencies_ms) if self.router_latencies_ms else 0.0

    @property
    def p95_router(self) -> float:
        """95th percentile router latency in milliseconds."""
        if not self.router_latencies_ms:
            return 0.0
        sorted_lat = sorted(self.router_latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx]

    def to_dict(self) -> dict[str, Any]:
        """Export stats as a dictionary."""
        return {
            "total_utterances": self.total_utterances,
            "total_stt_latency_ms": round(self.total_stt_latency_ms, 2),
            "total_tts_latency_ms": round(self.total_tts_latency_ms, 2),
            "total_router_latency_ms": round(self.total_router_latency_ms, 2),
            "p50_stt_ms": round(self.p50_stt, 2),
            "p95_stt_ms": round(self.p95_stt, 2),
            "p50_tts_ms": round(self.p50_tts, 2),
            "p95_tts_ms": round(self.p95_tts, 2),
            "p50_router_ms": round(self.p50_router, 2),
            "p95_router_ms": round(self.p95_router, 2),
            "failures": self.failures,
        }


# ---------------------------------------------------------------------------
# VoicePipeline
# ---------------------------------------------------------------------------


class BargeInMode(Enum):
    """Barge-in behaviour mode.

    * ``DISABLED`` — the user cannot interrupt; the full TTS plays out.
    * ``ENABLED`` — the user can interrupt the TTS at any time.
    """

    DISABLED = "disabled"
    ENABLED = "enabled"


class VoicePipeline:
    """End-to-end voice interaction pipeline.

    Orchestrates: capture → VAD → STT → router → TTS → playback
    with streaming support and optional barge-in.

    Usage::

        pipeline = VoicePipeline(
            capture=AudioCapture(),
            stt=my_stt_provider,
            tts=my_tts_provider,
            router=my_voice_router,
        )
        await pipeline.run()
    """

    def __init__(
        self,
        capture: AudioCapture,
        stt: STTProvider,
        tts: TTSProvider,
        router: VoiceAgentRouter,
        barge_in: BargeInMode = BargeInMode.ENABLED,
        max_utterance_duration: float = 30.0,
        silence_timeout: float = 1.5,
        enable_streaming: bool = True,
    ) -> None:
        """Initialise the voice pipeline.

        Args:
            capture: An ``AudioCapture`` instance for microphone input.
            stt: A speech-to-text provider.
            tts: A text-to-speech provider.
            router: A ``VoiceAgentRouter`` for routing transcribed text.
            barge_in: Barge-in mode (default ENABLED).
            max_utterance_duration: Maximum recording duration per utterance.
            silence_timeout: Seconds of silence before an utterance ends.
            enable_streaming: Enable streaming capture mode.
        """
        self._capture = capture
        self._stt = stt
        self._tts = tts
        self._router = router
        self._barge_in = barge_in
        self._max_utterance_duration = max_utterance_duration
        self._silence_timeout = silence_timeout
        self._enable_streaming = enable_streaming

        self._is_running = False
        self._stats = PipelineStats()
        self._barge_in_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def stats(self) -> PipelineStats:
        """Return current pipeline statistics."""
        return self._stats

    @property
    def is_running(self) -> bool:
        """``True`` while the pipeline is active."""
        return self._is_running

    async def run(self) -> None:
        """Run the voice pipeline in a continuous loop.

        Starts audio capture, then listens for utterances, transcribes,
        routes, synthesises, and plays back responses.

        Raises:
            PipelineError: If the pipeline encounters a fatal error.
        """
        self._stats = PipelineStats()
        self._stats.start_time = time.monotonic()

        logger.info("VoicePipeline starting")

        # Start audio capture
        try:
            self._capture.start()
        except Exception as exc:
            raise PipelineError(f"Failed to start audio capture: {exc}") from exc

        self._is_running = True

        try:
            await self._main_loop()
        except asyncio.CancelledError:
            logger.info("VoicePipeline cancelled")
        except Exception as exc:
            logger.exception("VoicePipeline encountered an error")
            raise PipelineError(f"Pipeline error: {exc}") from exc
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the voice pipeline gracefully."""
        self._is_running = False
        self._capture.stop()
        self._stats.total_pipeline_latency_ms = (
            time.monotonic() - self._stats.start_time
        ) * 1000
        logger.info(
            "VoicePipeline stopped",
            utterances=self._stats.total_utterances,
            failures=self._stats.failures,
        )

    # ------------------------------------------------------------------
    # Internal pipeline stages
    # ------------------------------------------------------------------

    async def _main_loop(self) -> None:
        """Core pipeline loop: listen → transcribe → route → speak."""
        while self._is_running:
            try:
                # Stage 1: Capture utterance
                utterance_audio = await self._capture_utterance()
                if utterance_audio is None or len(utterance_audio) < 320:  # < 20ms at 16kHz
                    continue

                # Stage 2: STT
                transcription = await self._transcribe(utterance_audio)
                if not transcription.text.strip():
                    continue

                logger.info(
                    "Transcribed",
                    text=transcription.text,
                    stt_latency_ms=round(transcription.latency_ms, 1),
                )

                # Stage 3: Router (orchestrator)
                router_response = await self._route(transcription)

                logger.info(
                    "Routed",
                    router_latency_ms=round(router_response.latency_ms, 1),
                    response_len=len(router_response.text),
                )

                # Stage 4: TTS + Playback
                await self._speak(router_response.text)

            except BargeInEvent:
                logger.debug("Pipeline: barge-in detected, restarting listen cycle")
                continue
            except (STTError, TTSError, RouterError) as exc:
                self._stats.failures += 1
                logger.warning("Pipeline stage error", error=str(exc))
                continue

    async def _capture_utterance(self) -> bytearray | None:
        """Capture a single utterance from the microphone.

        Returns:
            PCM audio data for the utterance, or ``None`` if nothing captured.
        """
        if self._enable_streaming:
            return record_utterance(
                self._capture,
                max_duration=self._max_utterance_duration,
                silence_timeout=self._silence_timeout,
            )
        else:
            # Single-chunk mode: read one frame
            frames = self._capture._read_frame()
            if frames is None:
                return None
            return bytearray(frames)

    async def _transcribe(self, audio_data: bytearray) -> TranscriptionResult:
        """Transcribe audio data to text.

        Args:
            audio_data: PCM audio bytes.

        Returns:
            A ``TranscriptionResult``.

        Raises:
            STTError: If transcription fails.
        """
        start = time.monotonic()
        result = await self._stt.transcribe(bytes(audio_data))
        latency_ms = (time.monotonic() - start) * 1000

        self._stats.total_utterances += 1
        self._stats.total_stt_latency_ms += latency_ms
        self._stats.stt_latencies_ms.append(latency_ms)

        return result

    async def _route(self, transcription: TranscriptionResult) -> RouterResponse:
        """Route transcribed text through the agent router.

        Args:
            transcription: The transcription result.

        Returns:
            A ``RouterResponse``.

        Raises:
            RouterError: If routing fails.
        """
        start = time.monotonic()
        response = await self._router.route_transcribed_text(
            text=transcription.text,
        )
        latency_ms = (time.monotonic() - start) * 1000

        self._stats.total_router_latency_ms += latency_ms
        self._stats.router_latencies_ms.append(latency_ms)

        return response

    async def _speak(self, text: str) -> None:
        """Synthesise and play back the response audio.

        If barge-in is enabled, monitors the microphone during playback
        and stops if new speech is detected.

        Args:
            text: Text to synthesise.

        Raises:
            BargeInEvent: If the user interrupts during playback.
            TTSError: If TTS synthesis fails.
        """
        # Stage 4a: Synthesise
        start = time.monotonic()
        tts_result: TTSResult = await self._tts.synthesize(text)
        tts_latency_ms = (time.monotonic() - start) * 1000

        self._stats.total_tts_latency_ms += tts_latency_ms
        self._stats.tts_latencies_ms.append(tts_latency_ms)

        # Stage 4b: Playback
        if self._barge_in == BargeInMode.ENABLED:
            self._playback_with_barge_in(tts_result)
        else:
            self._playback(tts_result)

    def _playback(self, tts_result: TTSResult) -> None:
        """Play audio data directly.

        In a real implementation this would use ``sounddevice`` or PyAudio
        to stream audio to the output device.  For now we log the event.

        Args:
            tts_result: The TTS result with audio data.
        """
        import sounddevice as sd  # noqa: F811

        try:
            sd.play(
                tts_result.audio_data,
                samplerate=tts_result.sample_rate,
                blocking=True,
            )
        except Exception as exc:
            logger.warning("Playback failed", error=str(exc))

    def _playback_with_barge_in(self, tts_result: TTSResult) -> None:
        """Play audio with barge-in (user can interrupt by speaking).

        Monitors the capture stream for speech frames during playback.
        If speech is detected, stops playback and raises ``BargeInEvent``.

        Args:
            tts_result: The TTS result with audio data.

        Raises:
            BargeInEvent: If user speech is detected during playback.
        """
        import sounddevice as sd  # noqa: F811

        interrupted = False

        def _monitor_mic() -> None:
            """Background thread: monitor mic for speech during playback."""
            nonlocal interrupted
            vad = self._capture._vad
            if vad is None:
                return
            sample_rate = self._capture.sample_rate
            frame_size = int(sample_rate * 0.03) * 2  # 30ms frame

            while not interrupted:
                frames = self._capture._read_frame(timeout=0.1)
                if frames is None or len(frames) < frame_size:
                    continue
                try:
                    if vad.is_speech(frames, sample_rate):
                        interrupted = True
                        return
                except Exception:
                    pass

        # Start mic monitor thread
        monitor = threading.Thread(target=_monitor_mic, daemon=True)
        monitor.start()

        try:
            sd.play(
                tts_result.audio_data,
                samplerate=tts_result.sample_rate,
                blocking=True,
            )
        except Exception as exc:
            logger.warning("Playback failed", error=str(exc))
            return

        if interrupted:
            # Stop any ongoing playback
            sd.stop()
            raise BargeInEvent("User interrupted during TTS playback")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset_stats(self) -> None:
        """Reset pipeline statistics."""
        self._stats = PipelineStats()
