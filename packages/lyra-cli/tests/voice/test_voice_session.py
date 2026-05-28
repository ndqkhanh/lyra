"""Tests for VoiceSession, WakeWordDetector, WakeWordResult, and SessionConfig."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from lyra_cli.voice.voice_session import (
    SessionConfig,
    SessionState,
    VoiceSession,
    WakeWordDetector,
    WakeWordResult,
)


class TestWakeWordResult:
    def test_default_values(self):
        r = WakeWordResult(detected=False)
        assert not r.detected
        assert r.confidence == 0.0
        assert r.phrase == ""
        assert r.remaining_text == ""

    def test_confidence_clamped(self):
        r = WakeWordResult(detected=True, confidence=2.0)
        assert r.confidence == 0.0

    def test_valid_result(self):
        r = WakeWordResult(detected=True, confidence=0.9, phrase="hey lyra hello", remaining_text="hello")
        assert r.detected
        assert r.confidence == 0.9
        assert r.remaining_text == "hello"


class TestSessionConfig:
    def test_defaults(self):
        cfg = SessionConfig()
        assert "hey lyra" in cfg.wake_words
        assert cfg.wake_word_sensitivity == 0.5
        assert cfg.inactivity_timeout == 30.0
        assert cfg.max_session_duration == 3600.0
        assert cfg.auto_stop_on_silence
        assert not cfg.push_to_talk

    def test_values_clamped(self):
        cfg = SessionConfig(
            wake_word_sensitivity=2.0,
            inactivity_timeout=1.0,
            max_session_duration=10.0,
        )
        assert cfg.wake_word_sensitivity == 1.0
        assert cfg.inactivity_timeout == 5.0
        assert cfg.max_session_duration == 60.0


class TestWakeWordDetector:
    def test_detect_exact_prefix(self):
        detector = WakeWordDetector()
        result = detector.detect("hey lyra what is the weather")
        assert result.detected
        assert result.remaining_text == "what is the weather"
        assert result.confidence == 1.0

    def test_detect_substring_match(self):
        detector = WakeWordDetector()
        result = detector.detect("please hey lyra turn on the lights")
        assert result.detected
        assert "turn on the lights" in result.remaining_text

    def test_detect_no_match(self):
        detector = WakeWordDetector()
        result = detector.detect("what is the weather")
        assert not result.detected

    def test_detect_empty_text(self):
        detector = WakeWordDetector()
        result = detector.detect("")
        assert not result.detected

    def test_detect_only_whitespace(self):
        detector = WakeWordDetector()
        result = detector.detect("   ")
        assert not result.detected

    def test_detect_okay_lyra(self):
        detector = WakeWordDetector()
        result = detector.detect("okay lyra do something")
        assert result.detected
        assert result.remaining_text == "do something"

    def test_detect_single_word_lyra(self):
        detector = WakeWordDetector()
        result = detector.detect("lyra hello")
        assert result.detected
        assert result.remaining_text == "hello"

    def test_strip_wake_word(self):
        detector = WakeWordDetector()
        remaining = detector.strip_wake_word("hey lyra do this")
        assert remaining == "do this"

    def test_strip_wake_word_no_match(self):
        detector = WakeWordDetector()
        remaining = detector.strip_wake_word("do this")
        assert remaining == "do this"

    def test_custom_wake_words(self):
        detector = WakeWordDetector(wake_words=["computer"])
        result = detector.detect("computer activate")
        assert result.detected
        assert result.remaining_text == "activate"

    def test_wake_words_property(self):
        detector = WakeWordDetector()
        words = detector.wake_words
        assert "hey lyra" in words
        assert isinstance(words, list)

    def test_short_phrase_fuzzy_match(self):
        detector = WakeWordDetector()
        result = detector.detect("lyra")
        assert result.detected


class TestVoiceSession:
    def test_initial_state(self):
        session = VoiceSession()
        assert session.state == SessionState.IDLE
        assert not session.is_active
        assert session.is_idle

    def test_start(self):
        session = VoiceSession()
        session.start()
        assert session.is_idle
        assert session.is_active is False  # IDLE is not active

    def test_start_then_process_makes_active(self):
        session = VoiceSession()
        session.start()
        response = session.process_text("hello")
        assert response != ""
        assert session.state == SessionState.IDLE  # back to idle after processing

    def test_stop(self):
        session = VoiceSession()
        session.start()
        session.stop()
        assert session.state == SessionState.STOPPED
        assert not session.is_active

    def test_stop_then_start_raises(self):
        session = VoiceSession()
        session.start()
        session.stop()
        with pytest.raises(RuntimeError, match="cannot be restarted"):
            session.start()

    def test_pause_and_resume(self):
        session = VoiceSession()
        session.start()
        session.pause()
        assert session.state == SessionState.PAUSED
        session.resume()
        assert session.state == SessionState.IDLE

    def test_process_text_with_wake_word(self):
        session = VoiceSession()
        session.start()
        response = session.process_text("hey lyra what time is it")
        assert "I heard" in response
        assert "what time is it" in response

    def test_process_text_without_wake_word_push_to_talk(self):
        cfg = SessionConfig(push_to_talk=True)
        session = VoiceSession(config=cfg)
        session.start()
        response = session.process_text("hello")
        assert response == ""

    def test_process_text_empty(self):
        session = VoiceSession()
        session.start()
        response = session.process_text("")
        assert response == ""
        response = session.process_text("   ")
        assert response == ""

    def test_check_timeout(self):
        cfg = SessionConfig(inactivity_timeout=5.0)
        session = VoiceSession(config=cfg, sound_notifier=MagicMock())
        session.start()
        session._last_activity = __import__("datetime").datetime(2020, 1, 1)
        assert session.check_timeout()
        assert session.state == SessionState.STOPPED

    def test_check_timeout_no_auto_stop(self):
        cfg = SessionConfig(inactivity_timeout=5.0, auto_stop_on_silence=False)
        session = VoiceSession(config=cfg, sound_notifier=MagicMock())
        session.start()
        session._last_activity = __import__("datetime").datetime(2020, 1, 1)
        assert not session.check_timeout()

    def test_check_max_duration(self):
        cfg = SessionConfig(max_session_duration=5.0)
        session = VoiceSession(config=cfg, sound_notifier=MagicMock())
        session.start()
        session._session_start = __import__("datetime").datetime(2020, 1, 1)
        session._last_activity = __import__("datetime").datetime(2020, 1, 1)
        assert session.check_max_duration()
        assert session.state == SessionState.STOPPED

    def test_conversation_history(self):
        session = VoiceSession()
        session.start()
        session.process_text("hey lyra hello")
        assert len(session.conversation_history) == 1
        assert session.conversation_history[0]["command"] == "hello"

    def test_get_conversation_context(self):
        session = VoiceSession()
        session.start()
        session.process_text("hey lyra first")
        session.process_text("hey lyra second")
        session.process_text("hey lyra third")
        context = session.get_conversation_context(max_turns=2)
        assert len(context) == 2
        assert context[-1]["command"] == "third"

    def test_custom_command_handler(self):
        def handler(text: str) -> str:
            return f"custom: {text}"

        session = VoiceSession(command_handler=handler)
        session.start()
        response = session.process_text("hey lyra do thing")
        assert response == "custom: do thing"

    def test_on_event_listener(self):
        session = VoiceSession()
        session.start()
        state_changes = []
        session.on("state_change", lambda state: state_changes.append(state))
        session.process_text("hey lyra test")
        assert len(state_changes) > 0

    def test_on_wake_word_event(self):
        session = VoiceSession()
        session.start()
        wake_events = []
        session.on("wake_word", lambda result: wake_events.append(result))
        session.process_text("hey lyra test")
        assert len(wake_events) == 1
        assert wake_events[0].detected

    def test_tts_backend_called(self):
        mock_tts = MagicMock()
        mock_tts.name = "mock"
        mock_tts.synthesize.return_value = "/tmp/out.wav"

        session = VoiceSession(tts_backend=mock_tts)
        session.start()
        session.process_text("hey lyra hello")
        mock_tts.synthesize.assert_called_once()

    def test_sound_notifier_used(self):
        mock_notifier = MagicMock()
        session = VoiceSession(sound_notifier=mock_notifier)
        session.start()
        session.process_text("hey lyra test")
        assert mock_notifier.notify.call_count >= 1

    def test_session_duration(self):
        session = VoiceSession()
        assert session.session_duration == 0.0
        session.start()
        assert session.session_duration >= 0.0
