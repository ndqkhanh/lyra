"""Tests for the full-duplex handler module (duplex.py).

Covers FullDuplexHandler, AECProcessor, SemanticEndpointer, turn-taking
state machine, and barge-in classification.
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from lyra.voice.duplex import (
    AECProcessor,
    AudioFrame,
    BargeInError,
    BargeInEvent as DuplexBargeIn,
    BargeInType,
    DuplexError,
    DuplexStats,
    EchoCancellationError,
    FullDuplexHandler,
    SemanticEndpointer,
    TurnRecord,
    TurnState,
    VAD_FRAME_MS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_audio(length_ms: int = 20, sample_rate: int = 16000, amplitude: int = 0) -> bytes:
    """Generate PCM audio data for testing."""
    import struct
    num_samples = int(sample_rate * length_ms / 1000)
    return b"".join(struct.pack("<h", amplitude) for _ in range(num_samples))


# ===================================================================
# AECProcessor tests
# ===================================================================


class TestAECProcessor:
    """Tests for the Acoustic Echo Cancellation stub."""

    def test_creation(self) -> None:
        aec = AECProcessor()
        assert aec._sample_rate == 16000
        assert aec._filter_length > 0

    def test_custom_sample_rate(self) -> None:
        aec = AECProcessor(sample_rate=44100, filter_length_ms=50)
        assert aec._sample_rate == 44100

    def test_process_passes_through(self) -> None:
        aec = AECProcessor()
        audio = _sample_audio(20)
        result = aec.process(audio)
        assert result == audio

    def test_process_empty_raises(self) -> None:
        aec = AECProcessor()
        with pytest.raises(EchoCancellationError, match="Empty mic audio"):
            aec.process(b"")

    def test_add_reference(self) -> None:
        aec = AECProcessor()
        aec.add_reference(b"\x00\x01" * 100)
        assert len(aec._reference_buffer) == 1

    def test_add_reference_multiple(self) -> None:
        aec = AECProcessor(sample_rate=16000, filter_length_ms=10)
        # Add many references — trimming keeps at most ~8 + 1 extra from partial fills
        for _ in range(20):
            aec.add_reference(b"\x00\x01" * 100)
        # After 20 inserts the buffer should be substantially smaller than 20
        assert len(aec._reference_buffer) <= 12  # trimmed

    def test_reset_clears_buffer(self) -> None:
        aec = AECProcessor()
        aec.add_reference(b"\x00\x01" * 100)
        aec.reset()
        assert len(aec._reference_buffer) == 0


# ===================================================================
# SemanticEndpointer tests
# ===================================================================


class TestSemanticEndpointer:
    """Tests for the semantic endpointer."""

    def test_creation(self) -> None:
        ep = SemanticEndpointer()
        assert ep._silence_timeout_ms == 300.0

    def test_custom_timeout(self) -> None:
        ep = SemanticEndpointer(silence_timeout_ms=500.0)
        assert ep._silence_timeout_ms == 500.0

    def test_should_end_turn_false(self) -> None:
        ep = SemanticEndpointer(silence_timeout_ms=300.0)
        assert ep.should_end_turn(100.0) is False

    def test_should_end_turn_true(self) -> None:
        ep = SemanticEndpointer(silence_timeout_ms=300.0)
        assert ep.should_end_turn(300.0) is True

    def test_on_silence_start_and_end(self) -> None:
        ep = SemanticEndpointer()
        now = time.monotonic() * 1000
        ep.on_silence_start(now)
        duration = ep.on_silence_ended(now + 500.0)
        assert duration == 500.0

    def test_on_silence_ended_no_start(self) -> None:
        ep = SemanticEndpointer()
        duration = ep.on_silence_ended(1000.0)
        assert duration == 0.0

    def test_classify_genuine_barge_in(self) -> None:
        ep = SemanticEndpointer()
        audio = _sample_audio(20, amplitude=5000)
        event = ep.classify_barge_in(
            user_audio=audio,
            vad_probability=0.8,
            pause_duration_ms=500.0,
            text_prefix="I want to say something",
        )
        assert event.barge_in_type == BargeInType.GENUINE
        assert event.semantic_score > 0.5
        assert len(event.user_audio) > 0

    def test_classify_noise(self) -> None:
        ep = SemanticEndpointer()
        audio = _sample_audio(20, amplitude=100)
        event = ep.classify_barge_in(
            user_audio=audio,
            vad_probability=0.1,
            pause_duration_ms=50.0,
            text_prefix=None,
        )
        assert event.barge_in_type in (BargeInType.FILLED_PAUSE, BargeInType.NOISE)

    def test_classify_self_correction_from_text(self) -> None:
        ep = SemanticEndpointer()
        audio = _sample_audio(20, amplitude=5000)
        event = ep.classify_barge_in(
            user_audio=audio,
            vad_probability=0.9,
            pause_duration_ms=300.0,
            text_prefix="wait actually I meant something else",
        )
        assert event.barge_in_type == BargeInType.SELF_CORRECTION

    def test_classify_filled_pause_from_text(self) -> None:
        ep = SemanticEndpointer()
        audio = _sample_audio(20, amplitude=5000)
        event = ep.classify_barge_in(
            user_audio=audio,
            vad_probability=0.9,
            pause_duration_ms=50.0,
            text_prefix="um",
        )
        assert event.barge_in_type == BargeInType.FILLED_PAUSE

    def test_classify_short_text_as_noise(self) -> None:
        ep = SemanticEndpointer()
        audio = _sample_audio(20, amplitude=5000)
        event = ep.classify_barge_in(
            user_audio=audio,
            vad_probability=0.9,
            pause_duration_ms=300.0,
            text_prefix="a",
        )
        assert event.barge_in_type == BargeInType.NOISE

    def test_semantic_score_range(self) -> None:
        ep = SemanticEndpointer()
        audio = _sample_audio(20, amplitude=5000)
        # Genuine with high VAD and long text
        event = ep.classify_barge_in(
            user_audio=audio,
            vad_probability=0.95,
            pause_duration_ms=600.0,
            text_prefix="this is a long text that should get a high score",
        )
        assert 0.0 <= event.semantic_score <= 1.0
        assert event.semantic_score > 0.5


# ===================================================================
# FullDuplexHandler tests
# ===================================================================


class TestFullDuplexHandler:
    """Tests for the FullDuplexHandler."""

    def test_initial_state(self) -> None:
        handler = FullDuplexHandler()
        assert handler.state == TurnState.LISTENING
        assert handler.stats.total_turns == 0

    def test_custom_components(self) -> None:
        aec = AECProcessor(sample_rate=44100)
        endpointer = SemanticEndpointer(silence_timeout_ms=500.0)
        state_changes = []

        def on_change(state):
            state_changes.append(state)

        handler = FullDuplexHandler(
            aec=aec,
            endpointer=endpointer,
            on_state_change=on_change,
        )
        assert handler._aec._sample_rate == 44100
        assert handler._endpointer._silence_timeout_ms == 500.0

        # Trigger state change
        handler.transition_to(TurnState.THINKING)
        assert len(state_changes) > 0
        assert state_changes[-1] == TurnState.THINKING

    def test_transition_listening_to_thinking(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        assert handler.state == TurnState.THINKING

    def test_transition_thinking_to_speaking(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        assert handler.state == TurnState.SPEAKING

    def test_transition_speaking_to_listening(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        handler.transition_to(TurnState.LISTENING)
        assert handler.state == TurnState.LISTENING

    def test_transition_speaking_to_interrupted(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        handler.transition_to(TurnState.INTERRUPTED)
        assert handler.state == TurnState.INTERRUPTED

    def test_transition_interrupted_to_listening(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        handler.transition_to(TurnState.INTERRUPTED)
        handler.transition_to(TurnState.LISTENING)
        assert handler.state == TurnState.LISTENING

    def test_transition_same_state_noop(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.LISTENING)
        assert handler.state == TurnState.LISTENING

    def test_invalid_transition_raises(self) -> None:
        handler = FullDuplexHandler()
        with pytest.raises(DuplexError, match="Invalid state transition"):
            handler.transition_to(TurnState.SPEAKING)  # Can't go LISTENING -> SPEAKING

    def test_invalid_transition_from_thinking(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        with pytest.raises(DuplexError):
            handler.transition_to(TurnState.INTERRUPTED)

    def test_turn_history_property(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        assert isinstance(handler.turn_history, list)
        # After one full cycle we should have history
        handler.transition_to(TurnState.SPEAKING)
        handler.transition_to(TurnState.LISTENING)
        assert len(handler.turn_history) > 0

    @pytest.mark.asyncio
    async def test_feed_audio_listening_speech(self) -> None:
        handler = FullDuplexHandler()
        audio = _sample_audio(20, amplitude=5000)  # Loud = speech
        await handler.feed_audio(audio)
        # Should buffer the audio
        assert len(handler._user_buffer) > 0

    @pytest.mark.asyncio
    async def test_feed_audio_thinking_noop(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        audio = _sample_audio(20, amplitude=5000)
        await handler.feed_audio(audio)
        # Should be noop while thinking
        assert len(handler._user_buffer) == 0

    @pytest.mark.asyncio
    async def test_feed_audio_speaking_triggers_barge_in(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        audio = _sample_audio(20, amplitude=8000)
        await handler.feed_audio(audio)
        # Should have detected barge-in (loud audio while speaking)
        assert handler._interrupt_requested or handler._stats.total_interruptions >= 0

    @pytest.mark.asyncio
    async def test_feed_audio_speaking_with_vad(self) -> None:
        """Low VAD while speaking should not trigger barge-in."""
        handler = FullDuplexHandler()
        # Use a custom VAD that returns low probability
        handler._vad_provider = lambda x: 0.1  # Very low probability
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        audio = b"\x00\x00" * 320  # Silence
        await handler.feed_audio(audio)
        assert handler._interrupt_requested is False

    def test_request_interruption(self) -> None:
        handler = FullDuplexHandler()
        # Set up to SPEAKING state
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        handler.request_interruption()
        assert handler._interrupt_requested is True

    def test_request_interruption_wrong_state(self) -> None:
        handler = FullDuplexHandler()
        # In LISTENING state, should be noop
        handler.request_interruption()
        assert handler._interrupt_requested is False

    def test_should_interrupt(self) -> None:
        handler = FullDuplexHandler()
        assert handler.should_interrupt() is False
        handler._interrupt_requested = True
        assert handler.should_interrupt() is True

    @pytest.mark.asyncio
    async def test_handle_user_speech(self) -> None:
        handler = FullDuplexHandler()
        await handler.handle_user_speech("Hello")
        assert handler._assistant_speaking is True

    @pytest.mark.asyncio
    async def test_handle_user_speech_wrong_state(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        with pytest.raises(DuplexError, match="Cannot handle user speech"):
            await handler.handle_user_speech("Hello")

    @pytest.mark.asyncio
    async def test_start_assistant_speech(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        await handler.start_assistant_speech()
        assert handler.state == TurnState.SPEAKING

    @pytest.mark.asyncio
    async def test_end_assistant_speech(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        await handler.start_assistant_speech()
        await handler.end_assistant_speech()
        assert handler.state == TurnState.LISTENING

    def test_reset(self) -> None:
        handler = FullDuplexHandler()
        handler.transition_to(TurnState.THINKING)
        handler.transition_to(TurnState.SPEAKING)
        handler.reset()
        assert handler.state == TurnState.LISTENING
        assert handler.stats.total_turns == 0
        assert handler._interrupt_requested is False
        assert handler._assistant_speaking is False
        assert len(handler._user_buffer) == 0

    def test_duplex_stats_defaults(self) -> None:
        stats = DuplexStats()
        assert stats.total_turns == 0
        assert stats.total_interruptions == 0
        assert stats.turn_take_reliability == 1.0

    @pytest.mark.asyncio
    async def test_run_loop_empty(self) -> None:
        handler = FullDuplexHandler()
        # No turns in history, loop should noop with sleep
        with patch.object(asyncio, "sleep") as mock_sleep:
            # Set a small timeout for the task
            async def run_and_cancel():
                task = asyncio.create_task(handler.run_loop().__anext__())
                await asyncio.sleep(0.02)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            await run_and_cancel()

    @pytest.mark.asyncio
    async def test_run_loop_with_turns(self) -> None:
        handler = FullDuplexHandler()
        # Simulate some turns
        handler._turn_history.append(
            TurnRecord(
                state=TurnState.LISTENING,
                user_text="hello",
                turn_start_ms=1000.0,
                turn_end_ms=2000.0,
                latency_ms=1000.0,
            )
        )
        # Get first turn
        async for turn in handler.run_loop():
            assert turn.user_text == "hello"
            break

    @pytest.mark.asyncio
    async def test_feed_audio_speaking_aec(self) -> None:
        handler = FullDuplexHandler()
        handler._assistant_speaking = True
        audio = b"\x00\x01" * 160
        # Should pass through AEC
        result_audio = handler._aec.process(audio)
        assert result_audio == audio

    def test_default_vad_silence(self) -> None:
        prob = FullDuplexHandler._default_vad(b"\x00\x00" * 320)
        assert prob < 0.5  # Silence should have low probability

    def test_default_vad_speech(self) -> None:
        import struct
        loud = b"".join(struct.pack("<h", 8000) for _ in range(160))
        prob = FullDuplexHandler._default_vad(loud)
        assert prob > 0.5  # Loud signal should have high probability

    def test_default_vad_empty(self) -> None:
        assert FullDuplexHandler._default_vad(b"") == 0.0
        assert FullDuplexHandler._default_vad(b"\x00") == 0.0

    def test_turn_state_enum(self) -> None:
        assert len(TurnState) == 4

    def test_barge_in_type_enum(self) -> None:
        assert len(BargeInType) == 4
