"""Tests for the Inner Monologue engine.

Covers InnerMonologueEngine, CoTResult, MonologueLatencySnapshot,
ThinkStrategy, and frame generation at 80ms intervals.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from lyra.voice.inner_monologue import (
    ChainOfThoughtProvider,
    CoTResult,
    InnerMonologueEngine,
    InnerMonologueError,
    InnerMonologueFrame,
    MonologueLatencySnapshot,
    MonologueStage,
    TbSError,
    ThinkStrategy,
    _percentile,
)


# ===================================================================
# CoTResult tests
# ===================================================================


class TestCoTResult:
    """Tests for the CoTResult dataclass."""

    def test_defaults(self) -> None:
        result = CoTResult(reasoning="step by step", answer="42")
        assert result.reasoning == "step by step"
        assert result.answer == "42"
        assert result.token_count == 0
        assert result.think_ratio == 0.0
        assert result.latency_ms == 0.0

    def test_custom_values(self) -> None:
        result = CoTResult(
            reasoning="think", answer="answer",
            token_count=100, think_ratio=0.5, latency_ms=500.0,
        )
        assert result.token_count == 100
        assert result.think_ratio == 0.5
        assert result.latency_ms == 500.0


# ===================================================================
# InnerMonologueFrame tests
# ===================================================================


class TestInnerMonologueFrame:
    """Tests for the InnerMonologueFrame dataclass."""

    def test_defaults(self) -> None:
        frame = InnerMonologueFrame(text_token="hello")
        assert frame.text_token == "hello"
        assert frame.audio_data is None
        assert frame.audio_sample_rate == 24000
        assert frame.frame_index == 0
        assert frame.has_audio is False

    def test_with_audio(self) -> None:
        frame = InnerMonologueFrame(
            text_token="hello",
            audio_data=b"\x00\x01" * 100,
            audio_sample_rate=16000,
            frame_index=1,
        )
        assert frame.has_audio is True
        assert frame.audio_sample_rate == 16000
        assert frame.frame_index == 1

    def test_stage_latencies(self) -> None:
        frame = InnerMonologueFrame(
            text_token="hello",
            stage_latencies_ms={"think": 50.0, "text_encode": 10.0},
        )
        assert frame.stage_latencies_ms["think"] == 50.0


# ===================================================================
# InnerMonologueEngine tests
# ===================================================================


class TestInnerMonologueEngine:
    """Tests for the InnerMonologueEngine."""

    def test_creation_defaults(self) -> None:
        engine = InnerMonologueEngine()
        assert engine._think_strategy == ThinkStrategy.ROUTED
        assert engine._frame_duration_ms == 80.0
        assert engine.total_frames == 0
        assert engine.total_tokens == 0

    def test_creation_with_cot(self) -> None:
        cot = MagicMock(spec=ChainOfThoughtProvider)
        engine = InnerMonologueEngine(
            cot_provider=cot,
            think_strategy=ThinkStrategy.ALWAYS,
        )
        assert engine._cot is cot
        assert engine._think_strategy == ThinkStrategy.ALWAYS

    def test_creation_never_think(self) -> None:
        engine = InnerMonologueEngine(
            think_strategy=ThinkStrategy.NEVER,
        )
        assert engine._think_strategy == ThinkStrategy.NEVER

    def test_total_frames_and_tokens(self) -> None:
        engine = InnerMonologueEngine()
        assert engine.total_frames == 0
        assert engine.total_tokens == 0

    def test_latency_snapshots_empty(self) -> None:
        engine = InnerMonologueEngine()
        assert engine.latency_snapshots == []

    def test_reset_stats(self) -> None:
        engine = InnerMonologueEngine()
        engine._total_frames = 100
        engine._total_tokens = 500
        engine._latency.record("think", 50.0)
        engine.reset_stats()
        assert engine.total_frames == 0
        assert engine.total_tokens == 0
        assert engine.latency_snapshots == []

    def test_should_think_always(self) -> None:
        engine = InnerMonologueEngine(think_strategy=ThinkStrategy.ALWAYS)
        assert engine._should_think() is True
        assert engine._should_think(is_complex=False) is True

    def test_should_think_never(self) -> None:
        engine = InnerMonologueEngine(think_strategy=ThinkStrategy.NEVER)
        assert engine._should_think() is False
        assert engine._should_think(is_complex=True) is False

    def test_should_think_routed(self) -> None:
        engine = InnerMonologueEngine(think_strategy=ThinkStrategy.ROUTED)
        assert engine._should_think() is False
        assert engine._should_think(is_complex=True) is True
        assert engine._should_think(is_complex=False) is False

    def test_build_combined_text_with_reasoning(self) -> None:
        engine = InnerMonologueEngine()
        result = engine._build_combined_text("think step 1", "answer here")
        assert "[think]" in result
        assert "[/think]" in result
        assert "answer here" in result

    def test_build_combined_text_without_reasoning(self) -> None:
        engine = InnerMonologueEngine()
        result = engine._build_combined_text(None, "just answer")
        assert result == "just answer"

    def test_tokenise_text(self) -> None:
        engine = InnerMonologueEngine()
        tokens = engine._tokenise_text("hello world test")
        assert tokens == ["hello", "world", "test"]

    def test_tokenise_text_empty(self) -> None:
        engine = InnerMonologueEngine()
        tokens = engine._tokenise_text("")
        assert tokens == []

    def test_frame_count(self) -> None:
        engine = InnerMonologueEngine()
        # At ~0.2 words per frame, 5 words should produce ~25 frames
        frames = engine._frame_count("a b c d e")
        assert frames >= 1

    def test_encode_text_token(self) -> None:
        engine = InnerMonologueEngine()
        encoded = engine._encode_text_token("hello")
        assert encoded == "hello"

    def test_generate_audio_frame_default(self) -> None:
        engine = InnerMonologueEngine()
        audio, sr = engine._generate_audio_frame("hello")
        assert audio is None
        assert sr == 24000

    @pytest.mark.asyncio
    async def test_stream_basic(self) -> None:
        engine = InnerMonologueEngine(think_strategy=ThinkStrategy.NEVER)
        frames = []
        async for frame in engine.stream("hello world"):
            frames.append(frame)
            if len(frames) >= 3:
                break
        assert len(frames) > 0
        for f in frames:
            assert isinstance(f, InnerMonologueFrame)
            assert f.text_token != ""

    @pytest.mark.asyncio
    async def test_stream_with_cot(self) -> None:
        cot = AsyncMock(spec=ChainOfThoughtProvider)
        cot.reason.return_value = CoTResult(
            reasoning="I think therefore",
            answer="the answer is 42",
            token_count=20,
            think_ratio=0.5,
            latency_ms=100.0,
        )
        engine = InnerMonologueEngine(
            cot_provider=cot,
            think_strategy=ThinkStrategy.ALWAYS,
        )
        frames = []
        async for frame in engine.stream("what is the answer?", is_complex=True):
            frames.append(frame)
            if len(frames) >= 2:
                break
        assert len(frames) > 0
        assert cot.reason.called

    @pytest.mark.asyncio
    async def test_stream_cot_failure(self) -> None:
        cot = AsyncMock(spec=ChainOfThoughtProvider)
        cot.reason.side_effect = RuntimeError("API error")
        engine = InnerMonologueEngine(
            cot_provider=cot,
            think_strategy=ThinkStrategy.ALWAYS,
        )
        with pytest.raises(TbSError, match="CoT reasoning failed"):
            async for frame in engine.stream("test", is_complex=True):
                pass  # Should raise before yielding

    @pytest.mark.asyncio
    async def test_stream_with_context(self) -> None:
        cot = AsyncMock(spec=ChainOfThoughtProvider)
        cot.reason.return_value = CoTResult(
            reasoning="thinking...", answer="42",
        )
        engine = InnerMonologueEngine(
            cot_provider=cot,
            think_strategy=ThinkStrategy.ALWAYS,
        )
        frames = []
        async for frame in engine.stream("query", context="previous context"):
            frames.append(frame)
            if len(frames) >= 1:
                break
        # Verify context was passed
        assert cot.reason.called
        call_kwargs = cot.reason.call_args[1]
        assert call_kwargs.get("context") == "previous context"

    @pytest.mark.asyncio
    async def test_think_method(self) -> None:
        cot = AsyncMock(spec=ChainOfThoughtProvider)
        cot.reason.return_value = CoTResult(
            reasoning="thinking", answer="answer",
        )
        engine = InnerMonologueEngine(cot_provider=cot)
        result = await engine.think("question")
        assert result.answer == "answer"

    @pytest.mark.asyncio
    async def test_think_method_no_cot(self) -> None:
        engine = InnerMonologueEngine(cot_provider=None)
        with pytest.raises(TbSError, match="Think-before-Speak is not available"):
            await engine.think("question")


# ===================================================================
# MonologueLatencySnapshot tests
# ===================================================================


class TestMonologueLatencySnapshot:
    """Tests for MonologueLatencySnapshot dataclass."""

    def test_creation(self) -> None:
        snap = MonologueLatencySnapshot(
            stage="think", count=5,
            p50_ms=100.0, p95_ms=200.0, p99_ms=300.0, mean_ms=150.0,
        )
        assert snap.stage == "think"
        assert snap.count == 5
        assert snap.p50_ms == 100.0
        assert snap.mean_ms == 150.0


# ===================================================================
# MonologueStage tests
# ===================================================================


class TestMonologueStage:
    """Tests for MonologueStage enum."""

    def test_values(self) -> None:
        assert MonologueStage.THINK.value == "think"
        assert MonologueStage.TEXT_ENCODE.value == "text_encode"
        assert MonologueStage.AUDIO_GENERATE.value == "audio_generate"
        assert MonologueStage.INTERLEAVE.value == "interleave"
        assert MonologueStage.TOTAL.value == "total"

    def test_all_stages(self) -> None:
        assert len(list(MonologueStage)) == 5


# ===================================================================
# ThinkStrategy tests
# ===================================================================


class TestThinkStrategy:
    """Tests for ThinkStrategy enum."""

    def test_values(self) -> None:
        assert ThinkStrategy.ALWAYS.value == "always"
        assert ThinkStrategy.ROUTED.value == "routed"
        assert ThinkStrategy.NEVER.value == "never"


# ===================================================================
# Helper function tests
# ===================================================================


class TestPercentileHelper:
    """Tests for the _percentile helper function."""

    def test_percentile_empty(self) -> None:
        assert _percentile([], 50) == 0.0

    def test_percentile_single(self) -> None:
        assert _percentile([100.0], 50) == 100.0
        assert _percentile([100.0], 99) == 100.0

    def test_percentile_multi(self) -> None:
        samples = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert _percentile(samples, 50) == 30.0
        assert _percentile(samples, 0) == 10.0
        assert _percentile(samples, 100) == 50.0
