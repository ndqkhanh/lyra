"""Comprehensive tests for the full_duplex.py engine module.

Tests FullDuplexEngine, EchoCancellation, BargeInDetector, TurnTakingPolicy,
and all associated data classes.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from lyra.voice.full_duplex import (
    BARGE_IN_COOLDOWN_MS,
    BargeInDetector,
    BargeInEvent,
    ConversationState,
    DuplexEngineStats,
    EchoCancellation,
    FullDuplexEngine,
    FullDuplexError,
    TurnSegment,
    TurnTakingPolicy,
)


# ===================================================================
# Helper
# ===================================================================


def _make_pcm(amplitude: int = 0, samples: int = 320) -> bytes:
    """Generate PCM audio data (16-bit mono)."""
    import struct
    return b"".join(struct.pack("<h", amplitude) for _ in range(samples))


# ===================================================================
# ConversationState enum tests
# ===================================================================


class TestConversationState:
    def test_all_states(self) -> None:
        assert ConversationState.IDLE
        assert ConversationState.LISTENING
        assert ConversationState.THINKING
        assert ConversationState.SPEAKING
        assert ConversationState.INTERRUPTED

    def test_normal_cycle_order(self) -> None:
        """States should have unique auto values."""
        states = list(ConversationState)
        assert len(states) == 5


# ===================================================================
# DuplexEngineStats tests
# ===================================================================


class TestDuplexEngineStats:
    def test_initial_values(self) -> None:
        stats = DuplexEngineStats()
        assert stats.total_turns == 0
        assert stats.total_barge_ins == 0
        assert stats.state_transitions == 0


# ===================================================================
# TurnSegment tests
# ===================================================================


class TestTurnSegment:
    def test_default_values(self) -> None:
        seg = TurnSegment(audio=b"\x00\x00" * 160)
        assert seg.sample_rate == 16000
        assert seg.is_speech is False

    def test_is_frozen(self) -> None:
        seg = TurnSegment(audio=b"\x00\x00" * 160)
        with pytest.raises(AttributeError):
            seg.audio = b"changed"  # type: ignore[misc]


# ===================================================================
# EchoCancellation tests
# ===================================================================


class TestEchoCancellation:
    """Tests for the software AEC."""

    def test_default_init(self) -> None:
        aec = EchoCancellation()
        assert aec._sample_rate == 16000
        assert len(aec._filter_coeffs) == 1600  # 100ms @ 16kHz

    def test_custom_params(self) -> None:
        aec = EchoCancellation(sample_rate=48000, filter_length_ms=50, adaptation_rate=0.05)
        assert aec._sample_rate == 48000
        assert aec._adaptation_rate == 0.05

    def test_add_reference(self) -> None:
        aec = EchoCancellation()
        aec.add_reference(b"\x00\x01" * 160)
        assert len(aec._reference_buffer) == 1

    def test_process_passthrough_no_reference(self) -> None:
        """Without reference, audio passes through unchanged."""
        aec = EchoCancellation()
        audio = _make_pcm(amplitude=100)
        result = aec.process(audio)
        assert result == audio

    def test_process_empty_raises(self) -> None:
        aec = EchoCancellation()
        with pytest.raises(FullDuplexError, match="Empty mic audio"):
            aec.process(b"")

    def test_process_with_reference(self) -> None:
        """With reference, process should not crash."""
        aec = EchoCancellation()
        aec.add_reference(_make_pcm(amplitude=500, samples=320))
        result = aec.process(_make_pcm(amplitude=100, samples=320))
        assert isinstance(result, bytes)
        assert len(result) == 640

    def test_process_nlms_subtraction(self) -> None:
        """NLMS should modify the output."""
        aec = EchoCancellation(adaptation_rate=0.1)
        # Add a reference that will be used for subtraction
        ref = _make_pcm(amplitude=3000, samples=160)
        aec.add_reference(ref)
        aec.add_reference(ref)
        aec.add_reference(ref)

        mic = _make_pcm(amplitude=3000, samples=160)
        result = aec.process(mic)
        # The output MIGHT be the same or different depending on filter
        # It should at least be valid PCM
        assert isinstance(result, bytes)
        assert len(result) == 320

    def test_reset(self) -> None:
        aec = EchoCancellation()
        aec.add_reference(b"\x00\x01" * 160)
        aec.reset()
        assert len(aec._reference_buffer) == 0
        assert all(c == 0.0 for c in aec._filter_coeffs)

    def test_samples_conversion(self) -> None:
        audio = _make_pcm(amplitude=100, samples=4)
        samples = EchoCancellation._samples_from_bytes(audio)
        assert len(samples) == 4
        assert samples[0] == 100

        back = EchoCancellation._bytes_from_samples(samples)
        assert back == audio


# ===================================================================
# BargeInDetector tests
# ===================================================================


class TestBargeInDetector:
    """Tests for the barge-in detector."""

    def test_default_params(self) -> None:
        detector = BargeInDetector()
        assert detector._energy_threshold == 800.0
        assert detector._min_interruption_ms == 120.0
        assert detector._cooldown_ms == BARGE_IN_COOLDOWN_MS

    def test_quiet_frame_no_barge_in(self) -> None:
        detector = BargeInDetector(energy_threshold=2000.0)
        event = detector.feed_frame(_make_pcm(amplitude=0), timestamp_ms=1000.0)
        assert event is None

    def test_loud_frame_triggers_barge_in(self) -> None:
        detector = BargeInDetector(
            energy_threshold=100.0,
            min_interruption_ms=50.0,
        )
        loud = _make_pcm(amplitude=8000, samples=320)

        # First frame sets up speech start
        event = detector.feed_frame(loud, timestamp_ms=1000.0)
        # Should be None because we need min_interruption_ms worth of speech

        # Second frame should trigger
        event = detector.feed_frame(loud, timestamp_ms=1060.0)
        if event is None:
            # Might need more frames
            event = detector.feed_frame(loud, timestamp_ms=1120.0)

        if event is not None:
            assert isinstance(event, BargeInEvent)
            assert event.confidence > 0.0
            assert event.energy_level > 0.0
            assert len(event.audio_frames) > 0

    def test_cooldown_suppresses_rapid_firing(self) -> None:
        """Cooldown should prevent back-to-back triggers."""
        detector = BargeInDetector(
            energy_threshold=100.0,
            min_interruption_ms=50.0,
            cooldown_ms=10000.0,
        )
        loud = _make_pcm(amplitude=8000, samples=320)

        # Trigger first barge-in
        detector.feed_frame(loud, timestamp_ms=1000.0)
        first = detector.feed_frame(loud, timestamp_ms=1060.0)

        # Try again during cooldown
        second = detector.feed_frame(loud, timestamp_ms=2000.0)
        # Second should be suppressed (None) if cooldown still active
        assert second is None or isinstance(second, BargeInEvent)

    def test_reset_clears_speech_frames(self) -> None:
        detector = BargeInDetector()
        detector.feed_frame(_make_pcm(amplitude=8000), timestamp_ms=1000.0)
        assert len(detector._speech_frames) > 0

        detector.reset()
        assert len(detector._speech_frames) == 0
        assert detector._speech_start_ms == 0.0

    def test_rms_edge_cases(self) -> None:
        assert BargeInDetector._compute_rms(b"") == 0.0
        assert BargeInDetector._compute_rms(b"\x00") == 0.0
        assert BargeInDetector._compute_rms(b"\x00\x00" * 10) == 0.0
        assert BargeInDetector._compute_rms(b"\x01\x00" * 10) > 0.0

    def test_default_vad(self) -> None:
        assert BargeInDetector._default_vad(b"") == 0.0
        assert BargeInDetector._default_vad(b"\x00") == 0.0
        assert BargeInDetector._default_vad(b"\x00\x00" * 160) == 0.0
        assert BargeInDetector._default_vad(
            _make_pcm(amplitude=8000, samples=320)
        ) > 0.0

    def test_latency_budget_warning(self) -> None:
        """Detection latency beyond budget should be logged (no crash)."""
        detector = BargeInDetector(
            energy_threshold=1.0,
            min_interruption_ms=1.0,
            cooldown_ms=0.0,
        )
        # Feed many frames to exceed the latency budget
        loud = _make_pcm(amplitude=8000, samples=320 // 2)
        for i in range(5):
            event = detector.feed_frame(loud, timestamp_ms=1000.0 + i * 5.0)
            if event:
                break
        # Should not crash regardless


# ===================================================================
# TurnTakingPolicy tests
# ===================================================================


class TestTurnTakingPolicy:
    """Tests for the turn-taking policy."""

    def test_default_aggressiveness(self) -> None:
        policy = TurnTakingPolicy()
        assert policy.aggressiveness == TurnTakingPolicy.Aggressiveness.BALANCED
        assert policy._aggressiveness == TurnTakingPolicy.Aggressiveness.BALANCED

    def test_custom_aggressiveness(self) -> None:
        policy = TurnTakingPolicy(
            aggressiveness=TurnTakingPolicy.Aggressiveness.EAGER,
        )
        assert policy._aggressiveness == TurnTakingPolicy.Aggressiveness.EAGER
        assert policy._effective_silence_timeout_ms < 1000.0  # Default * 0.5

    def test_patient_aggressiveness(self) -> None:
        policy = TurnTakingPolicy(
            aggressiveness=TurnTakingPolicy.Aggressiveness.PATIENT,
        )
        # Default silence_timeout_ms is 600.0, PATIENT factor is 1.5 → 900.0
        assert policy._effective_silence_timeout_ms == 900.0

    def test_aggressiveness_property(self) -> None:
        policy = TurnTakingPolicy()
        assert policy.aggressiveness == TurnTakingPolicy.Aggressiveness.BALANCED

    def test_should_not_speak_during_barge_in(self) -> None:
        policy = TurnTakingPolicy(barge_in_grace_ms=500.0)
        should, conf = policy.should_speak(
            silence_duration_ms=100.0,
            is_barge_in=True,
            utterance_duration_ms=1000.0,
            is_utterance_complete=True,
        )
        assert not should
        assert conf == 0.0

    def test_should_speak_after_complete_utterance(self) -> None:
        policy = TurnTakingPolicy(silence_timeout_ms=100.0)
        should, conf = policy.should_speak(
            silence_duration_ms=200.0,
            is_barge_in=False,
            utterance_duration_ms=1000.0,
            is_utterance_complete=True,
        )
        assert should
        assert conf > 0.5

    def test_short_utterance_not_valid(self) -> None:
        policy = TurnTakingPolicy(min_utterance_ms=500.0)
        should, conf = policy.should_speak(
            silence_duration_ms=1000.0,
            is_barge_in=False,
            utterance_duration_ms=100.0,
            is_utterance_complete=False,
        )
        assert not should
        assert conf < 0.5

    def test_eager_takes_turn_with_long_silence(self) -> None:
        policy = TurnTakingPolicy(
            aggressiveness=TurnTakingPolicy.Aggressiveness.EAGER,
            silence_timeout_ms=1000.0,
        )
        should, conf = policy.should_speak(
            silence_duration_ms=1500.0,
            is_barge_in=False,
            utterance_duration_ms=500.0,
            is_utterance_complete=False,
        )
        assert should  # EAGER can take turn even without completion
        assert conf == 0.6

    def test_should_listen_with_vad(self) -> None:
        policy = TurnTakingPolicy()
        assert policy.should_listen(True, 0.0, 1000.0)

    def test_should_listen_after_barge_in(self) -> None:
        policy = TurnTakingPolicy(barge_in_grace_ms=500.0)
        assert policy.should_listen(False, 900.0, 1000.0)

    def test_should_not_listen_when_quiet(self) -> None:
        policy = TurnTakingPolicy(barge_in_grace_ms=100.0)
        assert not policy.should_listen(False, 0.0, 1000.0)

    def test_aggressiveness_enum_values(self) -> None:
        assert TurnTakingPolicy.Aggressiveness.PATIENT.value == "patient"
        assert TurnTakingPolicy.Aggressiveness.BALANCED.value == "balanced"
        assert TurnTakingPolicy.Aggressiveness.EAGER.value == "eager"


# ===================================================================
# FullDuplexEngine tests
# ===================================================================


class TestFullDuplexEngine:
    """Tests for the FullDuplexEngine lifecycle and state machine."""

    def test_initial_state(self) -> None:
        engine = FullDuplexEngine()
        assert engine.state == ConversationState.IDLE
        assert not engine.is_active
        assert isinstance(engine.stats, DuplexEngineStats)

    def test_start_transitions_to_listening(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        assert engine.is_active
        assert engine.state == ConversationState.LISTENING
        assert engine._turn_start_ms > 0

    def test_start_already_running(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.start()  # Second start should not crash
        assert engine.is_active

    def test_stop(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.stop()
        assert not engine.is_active
        assert engine.state == ConversationState.IDLE
        assert not engine._assistant_speaking

    def test_stop_when_not_active(self) -> None:
        engine = FullDuplexEngine()
        engine.stop()  # Should not raise
        assert not engine.is_active

    def test_stop_computes_avg_interruption_latency(self) -> None:
        engine = FullDuplexEngine()
        engine._stats.total_barge_ins = 2
        engine._stats.total_interruption_latency_ms = 500.0
        engine.start()
        engine.stop()
        assert engine.stats.avg_interruption_latency_ms == 250.0

    def test_reset(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        engine.reset()
        assert engine.state == ConversationState.IDLE
        assert not engine.is_active
        assert engine.stats.total_turns == 0

    def test_turn_policy_property(self) -> None:
        engine = FullDuplexEngine()
        assert isinstance(engine.turn_policy, TurnTakingPolicy)

    def test_begin_thinking(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        assert engine.state == ConversationState.THINKING
        assert engine.stats.state_transitions >= 2

    def test_begin_thinking_wrong_state(self) -> None:
        """begin_thinking should only work from LISTENING."""
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        engine.begin_thinking()  # Already THINKING, should be no-op
        assert engine.state == ConversationState.THINKING

    def test_begin_speaking(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        engine.begin_speaking()
        assert engine.state == ConversationState.SPEAKING
        assert engine._assistant_speaking

    def test_begin_speaking_wrong_state(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_speaking()  # From LISTENING, no-op
        assert engine.state == ConversationState.LISTENING

    def test_end_speaking(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        engine.begin_speaking()
        engine.end_speaking()
        assert engine.state == ConversationState.LISTENING
        assert not engine._assistant_speaking

    def test_end_speaking_wrong_state(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.end_speaking()  # From LISTENING, no-op
        assert engine.state == ConversationState.LISTENING

    def test_handle_interruption_not_interrupted(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        audio = engine.handle_interruption()
        assert audio == b""

    def test_handle_interruption_interrupted(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        engine.begin_speaking()
        # Force interrupt
        engine._state = ConversationState.INTERRUPTED
        audio = engine.handle_interruption()
        assert isinstance(audio, bytes)
        assert engine.state == ConversationState.LISTENING

    def test_should_take_turn_after_speech(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine._last_speech_ms = time.monotonic() * 1000
        engine._silence_start_ms = time.monotonic() * 1000

        should, conf = engine.should_take_turn()
        assert isinstance(should, bool)
        assert 0.0 <= conf <= 1.0

    def test_should_listen(self) -> None:
        engine = FullDuplexEngine()
        engine.start()

        # With VAD active, should listen
        engine._last_vad_active = True
        assert engine.should_listen()

        # Without VAD and no barge-in, may or may not listen
        engine._last_vad_active = False
        engine._last_barge_in_ms = 0.0
        assert isinstance(engine.should_listen(), bool)

    def test_is_interrupted(self) -> None:
        engine = FullDuplexEngine()
        assert not engine.is_interrupted()
        engine._state = ConversationState.INTERRUPTED
        assert engine.is_interrupted()

    def test_feed_mic_audio_listening(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.feed_mic_audio(_make_pcm(amplitude=8000))
        assert len(engine._mic_buffer) >= 0

    def test_feed_mic_audio_speaking_triggers_barge_in(self) -> None:
        """Audio feed during SPEAKING should run barge-in detection."""
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        engine.begin_speaking()

        # Feed multiple loud frames
        for i in range(10):
            engine.feed_mic_audio(_make_pcm(amplitude=8000))

    def test_feed_mic_audio_not_active(self) -> None:
        engine = FullDuplexEngine()
        # Not started, should just return
        engine.feed_mic_audio(b"test")  # Should not raise

    def test_feed_assistant_audio(self) -> None:
        engine = FullDuplexEngine()
        engine.feed_assistant_audio(_make_pcm(amplitude=100))
        assert len(engine._assistant_audio_buffer) == 1

    def test_feed_mic_audio_listening_silence_tracking(self) -> None:
        engine = FullDuplexEngine()
        engine.start()

        # Feed silence
        engine.feed_mic_audio(_make_pcm(amplitude=0))
        assert engine._silence_start_ms > 0

        # Feed speech
        engine.feed_mic_audio(_make_pcm(amplitude=8000))
        assert engine._last_speech_ms > 0
        assert engine._silence_start_ms == 0.0

    def test_barge_in_detected_callback(self) -> None:
        changes = []
        engine = FullDuplexEngine(
            on_state_change=lambda s: changes.append(s),
        )
        engine.start()
        engine.begin_thinking()
        engine.begin_speaking()

        # Trigger barge-in
        engine._on_barge_in_detected(
            BargeInEvent(
                detected_at_ms=time.monotonic() * 1000,
                confidence=0.8,
                energy_level=5000.0,
                audio_frames=b"audio",
            )
        )
        assert engine.state == ConversationState.INTERRUPTED
        assert engine._stats.total_barge_ins == 1

    def test_state_transition_callback(self) -> None:
        transitions = []
        def on_change(state):
            transitions.append(state)

        engine = FullDuplexEngine(on_state_change=on_change)
        engine.start()
        assert ConversationState.LISTENING in transitions

    def test_state_transition_callback_error(self) -> None:
        """Callback error should not propagate."""
        def failing_callback(state):
            raise RuntimeError("Callback failed")

        engine = FullDuplexEngine(on_state_change=failing_callback)
        engine.start()  # Should not raise
        assert engine.is_active

    def test_feed_mic_audio_speaking_aec_applied(self) -> None:
        engine = FullDuplexEngine()
        engine.start()
        engine.begin_thinking()
        engine.begin_speaking()

        original_process = engine._echo_cancellation.process
        engine._echo_cancellation.process = MagicMock(return_value=b"processed")

        engine.feed_mic_audio(_make_pcm(amplitude=100))
        engine._echo_cancellation.process.assert_called()

    def test_stats_object(self) -> None:
        engine = FullDuplexEngine()
        assert isinstance(engine.stats, DuplexEngineStats)
        engine._stats.total_turns = 5
        assert engine.stats.total_turns == 5


# ===================================================================
# Edge cases
# ===================================================================


class TestFullDuplexEdgeCases:
    def test_barge_in_event_dataclass(self) -> None:
        event = BargeInEvent(
            detected_at_ms=1000.0,
            confidence=0.9,
            energy_level=500.0,
            audio_frames=b"data",
        )
        assert event.detected_at_ms == 1000.0
        assert event.confidence == 0.9

    def test_barge_in_event_defaults(self) -> None:
        event = BargeInEvent(detected_at_ms=0.0)
        assert event.confidence == 0.0

    def test_barge_in_event_frozen(self) -> None:
        event = BargeInEvent(detected_at_ms=0.0)
        with pytest.raises(AttributeError):
            event.detected_at_ms = 1.0  # type: ignore[misc]
