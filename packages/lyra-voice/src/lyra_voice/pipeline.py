"""VoicePipeline — full-duplex voice orchestrator with barge-in handling.

Chains: Capture → VAD → STT → Agent/Router → TTS → Playback

Supports three interaction modes:
- Push-to-talk (PTT): explicit start/stop
- Wake-word: "Hey Lyra" triggers listening
- Full-duplex: continuous barge-in (requires Smart Turn)

Key features:
- Streaming STT with interim results
- Streaming TTS with early playback
- Barge-in detection and handling
- Audio ducking during interruptions
- SFX injection at pipeline events
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .providers import (
    STTProvider,
    TTSProvider,
    TurnTakingProvider,
    VADProvider,
    VoicePipelineConfig,
    VoiceProviderRegistry,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InteractionMode(str, Enum):
    PUSH_TO_TALK = "push_to_talk"
    WAKE_WORD = "wake_word"
    FULL_DUPLEX = "full_duplex"


class PipelineState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


class PipelineEvent(str, Enum):
    """Events emitted by the voice pipeline for hook/SFX integration."""

    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_STOPPED = "pipeline_stopped"
    WAKE_WORD_DETECTED = "wake_word_detected"
    SPEECH_STARTED = "speech_started"
    SPEECH_ENDED = "speech_ended"
    STT_COMPLETED = "stt_completed"
    AGENT_RESPONSE = "agent_response"
    TTS_STARTED = "tts_started"
    TTS_COMPLETED = "tts_completed"
    BARGE_IN = "barge_in"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class VoiceTurn:
    """A single complete voice interaction turn."""

    turn_id: str
    user_text: str = ""
    agent_text: str = ""
    audio_input_ms: float = 0.0
    stt_latency_ms: float = 0.0
    agent_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    was_interrupted: bool = False
    events: list[tuple[PipelineEvent, float]] = field(default_factory=list)


@dataclass
class VoicePipelineStats:
    """Cumulative voice pipeline statistics."""

    total_turns: int = 0
    total_interruptions: int = 0
    total_audio_processed_ms: float = 0.0
    avg_stt_latency_ms: float = 0.0
    avg_tts_latency_ms: float = 0.0
    total_errors: int = 0


# ---------------------------------------------------------------------------
# Voice pipeline
# ---------------------------------------------------------------------------


class VoicePipeline:
    """Full-duplex voice pipeline orchestrator.

    Parameters
    ----------
    registry : VoiceProviderRegistry | None
        Provider registry. Creates a default registry with EnergyVAD + GapBasedTurn
        if None.
    config : VoicePipelineConfig | None
        Pipeline configuration. Default config if None.
    mode : InteractionMode
        Voice interaction mode. PUSH_TO_TALK by default.
    """

    def __init__(
        self,
        registry: VoiceProviderRegistry | None = None,
        config: VoicePipelineConfig | None = None,
        mode: InteractionMode = InteractionMode.PUSH_TO_TALK,
    ) -> None:
        self._registry = registry or VoiceProviderRegistry()
        self._config = config or VoicePipelineConfig()
        self._mode = mode
        self._state = PipelineState.IDLE
        self._stats = VoicePipelineStats()
        self._event_handlers: dict[PipelineEvent, list[Callable]] = {
            e: [] for e in PipelineEvent
        }
        self._turns: list[VoiceTurn] = []

    # -- Provider accessors ---------------------------------------------------

    @property
    def stt(self) -> STTProvider:
        return self._registry.get_stt("default")

    @property
    def tts(self) -> TTSProvider:
        return self._registry.get_tts("default")

    @property
    def vad(self) -> VADProvider:
        return self._registry.get_vad("default")

    @property
    def turn(self) -> TurnTakingProvider:
        return self._registry.get_turn("default")

    # -- Event system ---------------------------------------------------------

    def on(self, event: PipelineEvent, handler: Callable) -> None:
        """Register a handler for a pipeline event."""
        self._event_handlers[event].append(handler)

    async def _emit(self, event: PipelineEvent, **kwargs: Any) -> None:
        for handler in self._event_handlers[event]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, **kwargs)
                else:
                    handler(event, **kwargs)
            except Exception:
                logger.exception("Event handler for %s failed", event)

    # -- Core pipeline --------------------------------------------------------

    async def process_audio(
        self,
        audio: bytes,
        agent_handler: Callable[[str], str] | None = None,
    ) -> VoiceTurn | None:
        """Process audio through the full pipeline: VAD → STT → Agent → TTS.

        Parameters
        ----------
        audio : bytes
            Raw 16-bit mono PCM audio data.
        agent_handler : callable | None
            Async or sync function that takes user text and returns agent response text.
            If None, the pipeline only does STT and returns the turn without TTS.

        Returns
        -------
        VoiceTurn | None
            The completed turn, or None if no speech was detected.
        """
        turn_id = f"turn_{int(time.time() * 1000)}"
        turn = VoiceTurn(turn_id=turn_id)
        t0 = time.time()

        try:
            # 1. VAD
            vad_result = await self.vad.detect(audio, self._config.vad)
            if not vad_result.is_speech:
                self._stats.total_audio_processed_ms += vad_result.end_ms
                return None

            await self._emit(PipelineEvent.SPEECH_STARTED)
            self._state = PipelineState.LISTENING

            # 2. STT
            stt_start = time.time()
            stt_result = await self.stt.transcribe(audio, self._config.stt)
            stt_latency = (time.time() - stt_start) * 1000
            turn.stt_latency_ms = stt_latency
            turn.user_text = stt_result.text
            turn.audio_input_ms = stt_result.duration_ms
            self._stats.total_audio_processed_ms += stt_result.duration_ms

            if not stt_result.text.strip():
                return None

            await self._emit(PipelineEvent.STT_COMPLETED, text=stt_result.text)

            # 3. Agent
            self._state = PipelineState.PROCESSING
            agent_start = time.time()

            if agent_handler is not None:
                agent_response = agent_handler(stt_result.text)
                if asyncio.iscoroutine(agent_response):
                    agent_response = await agent_response
            else:
                agent_response = stt_result.text  # echo mode

            turn.agent_text = str(agent_response)
            turn.agent_latency_ms = (time.time() - agent_start) * 1000

            await self._emit(PipelineEvent.AGENT_RESPONSE, text=turn.agent_text)

            if not turn.agent_text.strip():
                return turn

            # 4. TTS
            self._state = PipelineState.SPEAKING
            tts_start = time.time()
            audio_output = await self.tts.synthesize(
                turn.agent_text, self._config.tts
            )
            turn.tts_latency_ms = (time.time() - tts_start) * 1000

            await self._emit(PipelineEvent.TTS_COMPLETED, audio=audio_output)

            # 5. Done
            self._state = PipelineState.IDLE
            self._stats.total_turns += 1

            # Update rolling averages
            n = self._stats.total_turns
            self._stats.avg_stt_latency_ms = (
                (self._stats.avg_stt_latency_ms * (n - 1) + stt_latency) / n
            )
            self._stats.avg_tts_latency_ms = (
                (self._stats.avg_tts_latency_ms * (n - 1) + turn.tts_latency_ms) / n
            )

            turn.events.append((PipelineEvent.PIPELINE_STOPPED, time.time() - t0))
            self._turns.append(turn)
            return turn

        except Exception as exc:
            self._state = PipelineState.IDLE
            self._stats.total_errors += 1
            logger.exception("Pipeline error in turn %s: %s", turn_id, exc)
            await self._emit(PipelineEvent.ERROR, error=str(exc))
            return None

    async def process_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        agent_handler: Callable[[str], str] | None = None,
    ) -> AsyncIterator[VoiceTurn]:
        """Process a continuous audio stream with barge-in support.

        Yields VoiceTurn objects as they complete.
        Supports interruption when new speech is detected during agent TTS.
        """
        self._state = PipelineState.LISTENING
        audio_buffer: list[bytes] = []
        agent_speaking = False
        current_tts_task: asyncio.Task | None = None

        async for chunk in audio_stream:
            # VAD on chunk
            vad_result = await self.vad.detect(chunk, self._config.vad)

            if vad_result.is_speech:
                if agent_speaking:
                    # Barge-in detected
                    await self._emit(PipelineEvent.BARGE_IN)
                    self._stats.total_interruptions += 1
                    if current_tts_task and not current_tts_task.done():
                        current_tts_task.cancel()
                    agent_speaking = False
                    audio_buffer = []

                audio_buffer.append(chunk)
            elif audio_buffer:
                # End of speech segment — process it
                combined = b"".join(audio_buffer)
                audio_buffer = []

                turn = await self.process_audio(combined, agent_handler)
                if turn is not None and turn.agent_text:
                    yield turn
                    agent_speaking = True

        # Process remaining buffer
        if audio_buffer:
            combined = b"".join(audio_buffer)
            turn = await self.process_audio(combined, agent_handler)
            if turn is not None:
                yield turn

        self._state = PipelineState.IDLE

    # -- Interaction modes ----------------------------------------------------

    async def push_to_talk(
        self,
        audio: bytes,
        agent_handler: Callable[[str], str],
    ) -> VoiceTurn | None:
        """PTT mode: process explicit audio segment."""
        self._mode = InteractionMode.PUSH_TO_TALK
        await self._emit(PipelineEvent.PIPELINE_STARTED, mode="push_to_talk")
        return await self.process_audio(audio, agent_handler)

    async def listen_for_wake_word(
        self,
        audio_stream: AsyncIterator[bytes],
        wake_words: tuple[str, ...] = ("hey lyra",),
        agent_handler: Callable[[str], str] | None = None,
        timeout_s: float = 30.0,
    ) -> AsyncIterator[VoiceTurn]:
        """Wake-word mode: listen for wake word, then process command.

        Yields VoiceTurn objects after each wake-word-triggered interaction.
        Times out after ``timeout_s`` seconds of silence.
        """
        self._mode = InteractionMode.WAKE_WORD
        await self._emit(PipelineEvent.PIPELINE_STARTED, mode="wake_word")

        last_speech = time.time()
        audio_buffer: list[bytes] = []
        wake_detected = False
        command_buffer: list[bytes] = []
        post_wake_silence = 0.0

        async for chunk in audio_stream:
            if time.time() - last_speech > timeout_s and not wake_detected:
                break

            vad_result = await self.vad.detect(chunk, self._config.vad)

            if vad_result.is_speech:
                last_speech = time.time()
                if not wake_detected:
                    audio_buffer.append(chunk)
                    # Check for wake word via STT
                    if len(audio_buffer) >= 5:  # ~500ms of audio
                        combined = b"".join(audio_buffer)
                        stt_result = await self.stt.transcribe(combined)
                        if any(ww in stt_result.text.lower() for ww in wake_words):
                            wake_detected = True
                            self._state = PipelineState.LISTENING
                            await self._emit(PipelineEvent.WAKE_WORD_DETECTED)
                            audio_buffer = []
                else:
                    command_buffer.append(chunk)
                    post_wake_silence = 0.0
            elif wake_detected:
                post_wake_silence += len(chunk) / self._config.sample_rate
                if post_wake_silence >= (self._config.turn.endpoint_threshold_ms / 1000):
                    if command_buffer:
                        combined = b"".join(command_buffer)
                        turn = await self.process_audio(combined, agent_handler)
                        if turn is not None:
                            yield turn
                    wake_detected = False
                    command_buffer = []
                    post_wake_silence = 0.0
                    audio_buffer = []

        self._state = PipelineState.IDLE

    # -- Statistics -----------------------------------------------------------

    @property
    def stats(self) -> VoicePipelineStats:
        return self._stats

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def turns(self) -> list[VoiceTurn]:
        return list(self._turns)

    def reset_stats(self) -> None:
        self._stats = VoicePipelineStats()
        self._turns = []
