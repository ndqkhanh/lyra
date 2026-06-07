"""
Inner Monologue engine -- text-token-before-audio at 80 ms frames (Moshi pattern).

Implements the core Inner Monologue innovation from Moshi
(arXiv:2410.00037v2): text tokens emitted *before* corresponding audio
tokens at each 80 ms framing boundary.  This text prefix acts as the
model's "inner speech" -- chain-of-thought reasoning that improves spoken
QA accuracy from 9.2% to 26.6% on WebQ (Moshi).

Think-before-Speak (TbS) extension from VoxMind (arXiv:2604.15710v1)
adds explicit CoT reasoning before audio output, improving task completion
by +113.79% with only 12.6% token overhead.

Usage::

    engine = InnerMonologueEngine(
        stt_provider=my_stt,
        llm_router=my_router,
        tts_provider=my_tts,
    )

    async for frame in engine.stream("What is the weather in Hanoi?"):
        # Each frame carries text + optional audio at 80 ms granularity
        print(frame.text_token, frame.has_audio)
"""

from __future__ import annotations

import asyncio
import structlog
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from statistics import median
from typing import Any, Protocol

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INNER_MONOLOGUE_FRAME_MS: float = 80.0
"""Duration of each Inner Monologue frame in milliseconds (Moshi pattern)."""

INNER_MONOLOGUE_FRAME_S: float = 0.08
"""Duration of each Inner Monologue frame in seconds."""

VOCABULARY_RATE_HZ: float = 12.5
"""Moshi operates at 12.5 Hz (1 / 0.08 s)."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InnerMonologueError(Exception):
    """Raised when the Inner Monologue engine encounters a runtime error."""


class TbSError(InnerMonologueError):
    """Raised when Think-before-Speak reasoning fails."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ThinkStrategy(Enum):
    """Strategy for applying Think-before-Speak reasoning."""

    ALWAYS = "always"
    """Apply CoT reasoning on every turn (maximum quality, highest latency)."""

    ROUTED = "routed"
    """Apply CoT only when a task router classifies the query as complex
    (VoxMind 1:0.5 think:answer ratio)."""

    NEVER = "never"
    """Skip CoT reasoning -- direct answer only (minimum latency)."""


class MonologueStage(Enum):
    """Stages within the Inner Monologue pipeline."""

    THINK = "think"
    TEXT_ENCODE = "text_encode"
    AUDIO_GENERATE = "audio_generate"
    INTERLEAVE = "interleave"
    TOTAL = "total"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InnerMonologueFrame:
    """A single 80 ms frame carrying text + optional audio tokens.

    Moshi (arXiv:2410.00037v2) frames operate at 12.5 Hz.  Each frame
    carries a text token emitted *before* the audio semantic token.  The
    text token represents the model's "inner speech" at that moment.

    Attributes:
        text_token: The inner monologue text token for this frame.
        audio_data: 16-bit mono PCM audio bytes (if audio has been generated
            for this frame), or ``None``.
        audio_sample_rate: Sample rate of the audio data (default 24000).
        frame_index: Sequential frame index within the current utterance.
        timestamp_ms: Wall-clock timestamp when this frame was produced.
        has_audio: Whether ``audio_data`` is present.
        stage_latencies_ms: Per-stage latencies for this frame, keyed by
            ``MonologueStage`` value.
    """

    text_token: str
    audio_data: bytes | None = None
    audio_sample_rate: int = 24000
    frame_index: int = 0
    timestamp_ms: float = 0.0
    stage_latencies_ms: dict[str, float] = field(default_factory=dict)

    @property
    def has_audio(self) -> bool:
        """Return ``True`` if this frame carries audio data."""
        return self.audio_data is not None


@dataclass(frozen=True)
class CoTResult:
    """Result of Think-before-Speak reasoning.

    Attributes:
        reasoning: The chain-of-thought reasoning text.
        answer: The final answer produced after reasoning.
        token_count: Total token count (reasoning + answer).
        think_ratio: Ratio of reasoning tokens to total tokens
            (VoxMind optimal: 1:0.5 think:answer = 0.67).
        latency_ms: Wall-clock time for the CoT reasoning call.
    """

    reasoning: str
    answer: str
    token_count: int = 0
    think_ratio: float = 0.0
    latency_ms: float = 0.0


@dataclass(frozen=True)
class MonologueLatencySnapshot:
    """Latency snapshot across all Inner Monologue stages.

    Attributes:
        stage: The pipeline stage being measured.
        count: Number of samples.
        p50_ms: 50th percentile latency in milliseconds.
        p95_ms: 95th percentile latency in milliseconds.
        p99_ms: 99th percentile latency in milliseconds.
        mean_ms: Mean latency in milliseconds.
    """

    stage: str
    count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class ChainOfThoughtProvider(Protocol):
    """Protocol for a CoT reasoning provider (VoxMind TbS pattern)."""

    async def reason(
        self,
        query: str,
        context: str | None = None,
    ) -> CoTResult:
        """Run chain-of-thought reasoning on *query*.

        Args:
            query: The transcribed user query.
            context: Optional conversation context.

        Returns:
            A ``CoTResult`` with reasoning and final answer.
        """
        ...


# ---------------------------------------------------------------------------
# Latency tracker
# ---------------------------------------------------------------------------


class _StageTracker:
    """Tracks latency samples per stage for percentile computation."""

    def __init__(self) -> None:
        self._stages: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    def record(self, stage: str, latency_ms: float) -> None:
        """Record a latency sample for *stage*."""
        if stage not in self._stages:
            self._stages[stage] = []
        self._stages[stage].append(latency_ms)

    def snapshot(self) -> list[MonologueLatencySnapshot]:
        """Return percentile snapshots for all tracked stages."""
        snapshots: list[MonologueLatencySnapshot] = []
        for stage, samples in self._stages.items():
            if not samples:
                continue
            sorted_s = sorted(samples)
            n = len(sorted_s)
            snapshots.append(
                MonologueLatencySnapshot(
                    stage=stage,
                    count=n,
                    p50_ms=_percentile(sorted_s, 50),
                    p95_ms=_percentile(sorted_s, 95),
                    p99_ms=_percentile(sorted_s, 99),
                    mean_ms=sum(sorted_s) / n,
                )
            )
        return snapshots

    def clear(self) -> None:
        """Clear all recorded samples."""
        self._stages.clear()


def _percentile(sorted_samples: list[float], pct: int) -> float:
    """Compute the *pct*-th percentile of a sorted list."""
    if not sorted_samples:
        return 0.0
    k = max(0, min(len(sorted_samples) - 1, int(len(sorted_samples) * pct / 100)))
    return sorted_samples[k]


# ---------------------------------------------------------------------------
# InnerMonologueEngine
# ---------------------------------------------------------------------------


class InnerMonologueEngine:
    """Inner Monologue engine implementing Moshi-style text-before-audio.

    The engine operates at 12.5 Hz (80 ms frames).  For each frame it:
      1. **Thinks** -- produces a text token (CoT inner monologue).
      2. **Encodes** -- the text token is prepared for the TTS pipeline.
      3. **Generates audio** -- the corresponding audio chunk is produced.
      4. **Interleaves** -- text + audio are emitted as a single frame.

    References:
        - Moshi (arXiv:2410.00037v2): Inner Monologue, 80 ms frames,
          12.5 Hz rate, 17-stream multi-stream architecture.
        - VoxMind (arXiv:2604.15710v1): Think-before-Speak CoT,
          +113.79% task completion, 12.6% token overhead.
    """

    def __init__(
        self,
        cot_provider: ChainOfThoughtProvider | None = None,
        think_strategy: ThinkStrategy = ThinkStrategy.ROUTED,
        frame_duration_ms: float = INNER_MONOLOGUE_FRAME_MS,
    ) -> None:
        """Initialise the Inner Monologue engine.

        Args:
            cot_provider: Optional CoT reasoning provider.  If ``None``,
                TbS is skipped and the engine operates in direct-answer mode.
            think_strategy: Strategy for applying CoT reasoning
                (default: ``ROUTED`` -- only complex queries).
            frame_duration_ms: Frame duration in milliseconds
                (default 80 ms per Moshi).
        """
        self._cot = cot_provider
        self._think_strategy = think_strategy
        self._frame_duration_ms = frame_duration_ms

        # Per-stage latency tracking
        self._latency: _StageTracker = _StageTracker()
        self._total_frames: int = 0
        self._total_tokens: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def latency_snapshots(self) -> list[MonologueLatencySnapshot]:
        """Return latency percentiles for all tracked stages."""
        return self._latency.snapshot()

    @property
    def total_frames(self) -> int:
        """Total number of frames produced by this engine."""
        return self._total_frames

    @property
    def total_tokens(self) -> int:
        """Total number of text tokens produced."""
        return self._total_tokens

    def reset_stats(self) -> None:
        """Reset latency tracking and frame counters."""
        self._latency.clear()
        self._total_frames = 0
        self._total_tokens = 0

    async def stream(
        self,
        query: str,
        context: str | None = None,
        is_complex: bool | None = None,
    ) -> AsyncIterator[InnerMonologueFrame]:
        """Stream Inner Monologue frames for *query*.

        This is the primary entry point.  The engine:
        1. Runs CoT reasoning (if configured and applicable).
        2. Emits text tokens at 80 ms frame boundaries.
        3. When audio is available, includes it in each frame.

        Args:
            query: The transcribed user query.
            context: Optional conversation context.
            is_complex: Override for the task complexity classification.
                If ``None``, the engine applies the configured
                ``think_strategy``.

        Yields:
            ``InnerMonologueFrame`` instances at ~12.5 Hz.

        Raises:
            InnerMonologueError: If the engine encounters a runtime error.
        """
        t_total = time.monotonic()

        # ---- 1. Think (CoT reasoning) ----
        reasoning_text: str | None = None
        answer_text: str = query

        if self._cot is not None and self._should_think(is_complex):
            t_think = time.monotonic()
            try:
                cot_result = await self._cot.reason(query, context=context)
                reasoning_text = cot_result.reasoning
                answer_text = cot_result.answer
                think_latency = (time.monotonic() - t_think) * 1000
                self._latency.record(MonologueStage.THINK.value, think_latency)
                logger.debug(
                    "inner_monologue.cot",
                    think_ratio=round(cot_result.think_ratio, 3),
                    tokens=cot_result.token_count,
                    latency_ms=round(think_latency, 1),
                )
            except Exception as exc:
                raise TbSError(f"CoT reasoning failed: {exc}") from exc

        # ---- 2. Tokenise into 80 ms frames ----
        combined_text = self._build_combined_text(reasoning_text, answer_text)
        tokens = self._tokenise_text(combined_text)

        self._total_tokens += len(tokens)
        tokens_per_frame = max(1, len(tokens) // max(1, self._frame_count(combined_text)))
        token_index = 0
        frame_index = 0

        while token_index < len(tokens):
            t_frame = time.monotonic()

            # 2a. Text tokens for this frame
            frame_tokens = tokens[token_index : token_index + tokens_per_frame]
            text_token = " ".join(frame_tokens)

            t_encode = time.monotonic()
            text_encoded = self._encode_text_token(text_token)
            text_encode_latency = (time.monotonic() - t_encode) * 1000
            self._latency.record(MonologueStage.TEXT_ENCODE.value, text_encode_latency)

            # 2b. Generate audio for this frame (if TTS is available)
            t_audio = time.monotonic()
            audio_data, audio_sr = self._generate_audio_frame(text_encoded)
            audio_latency = (time.monotonic() - t_audio) * 1000
            self._latency.record(MonologueStage.AUDIO_GENERATE.value, audio_latency)

            # 2c. Build and yield the frame
            t_interleave = time.monotonic()
            interleave_latency = (time.monotonic() - t_interleave) * 1000
            self._latency.record(MonologueStage.INTERLEAVE.value, interleave_latency)

            frame = InnerMonologueFrame(
                text_token=text_token,
                audio_data=audio_data,
                audio_sample_rate=audio_sr,
                frame_index=frame_index,
                timestamp_ms=(time.monotonic() * 1000),
                stage_latencies_ms={
                    MonologueStage.THINK.value: think_latency if reasoning_text else 0.0,
                    MonologueStage.TEXT_ENCODE.value: text_encode_latency,
                    MonologueStage.AUDIO_GENERATE.value: audio_latency,
                    MonologueStage.INTERLEAVE.value: interleave_latency,
                },
            )

            yield frame

            token_index += tokens_per_frame
            frame_index += 1
            self._total_frames += 1

            # Emulate 80 ms frame pacing for realistic streaming
            elapsed = (time.monotonic() - t_frame) * 1000
            sleep_ms = max(0.0, self._frame_duration_ms - elapsed)
            if sleep_ms > 0:
                await asyncio.sleep(sleep_ms / 1000)

        # Record total latency
        total_latency = (time.monotonic() - t_total) * 1000
        self._latency.record(MonologueStage.TOTAL.value, total_latency)

    async def think(
        self,
        query: str,
        context: str | None = None,
    ) -> CoTResult:
        """Run CoT reasoning only, without audio generation.

        Useful when the caller wants just the reasoning (e.g. for safety
        auditing or logging) without the streaming pipeline overhead.

        Args:
            query: The transcribed user query.
            context: Optional conversation context.

        Returns:
            A ``CoTResult`` with reasoning and final answer.

        Raises:
            TbSError: If no CoT provider is configured.
        """
        if self._cot is None:
            raise TbSError(
                "Think-before-Speak is not available: no CoT provider configured"
            )
        return await self._cot.reason(query, context=context)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _should_think(self, is_complex: bool | None = None) -> bool:
        """Determine whether CoT reasoning should be applied."""
        if self._think_strategy == ThinkStrategy.ALWAYS:
            return True
        if self._think_strategy == ThinkStrategy.NEVER:
            return False
        # ROUTED -- default to False (simple) unless caller overrides
        return bool(is_complex)

    def _build_combined_text(
        self,
        reasoning: str | None,
        answer: str,
    ) -> str:
        """Build the combined inner monologue + answer text.

        In the Moshi pattern, the inner monologue text is included *before*
        the spoken answer.  The TTS sees both, enabling context-aware prosody.
        """
        if reasoning:
            return f"[think]{reasoning}[/think]\n{answer}"
        return answer

    def _tokenise_text(self, text: str) -> list[str]:
        """Split text into word-level tokens for frame assignment.

        This is a simplified tokeniser.  In production, replace with the
        actual model's tokeniser for accurate frame-level alignment.
        """
        return text.split()

    def _frame_count(self, text: str) -> int:
        """Estimate the number of 80 ms frames for *text*.

        Uses an approximate speaking rate of 150 words per minute
        (2.5 words/s).  At 12.5 Hz, that's ~0.2 words per frame.
        """
        word_count = max(1, len(text.split()))
        return max(1, int(word_count / 0.2))

    def _encode_text_token(self, text_token: str) -> str:
        """Prepare a text token for TTS input.

        Subclasses can override this to apply voice-specific formatting,
        SSML tags, or emotion markers.
        """
        return text_token

    def _generate_audio_frame(
        self,
        text_encoded: str,
        sample_rate: int = 24000,
    ) -> tuple[bytes | None, int]:
        """Generate audio data for a single 80 ms frame.

        In a production system this delegates to the TTS provider.  The
        default implementation returns ``None`` (no audio), which means the
        frame carries text only -- suitable for text-only monitoring or
        hybrid cascaded mode.

        Returns:
            A tuple of ``(audio_data, sample_rate)``.  ``audio_data`` is
            ``None`` when audio is not yet available.
        """
        # Override in subclass or wrap via TTSProvider in pipeline
        return None, sample_rate
