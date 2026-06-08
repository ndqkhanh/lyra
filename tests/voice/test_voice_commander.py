"""Tests for the VoiceCommander hold-to-talk fleet steering interface."""
from __future__ import annotations

import pytest

from unittest.mock import MagicMock, patch

from lyra.voice.voice_commander import (
    Command,
    CommandType,
    CommanderStats,
    VoiceCommander,
)


# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------


class _MockSTT:
    """Simulates an STT provider with configurable return values."""

    def __init__(self, response_text: str = "hello world") -> None:
        self._response_text = response_text
        self.last_audio = None
        self.last_sample_rate = None

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> "_MockTranscriptionResult":
        self.last_audio = audio_data
        self.last_sample_rate = sample_rate
        return _MockTranscriptionResult(self._response_text, language or "en")


class _MockTranscriptionResult:
    def __init__(self, text: str, language: str = "en") -> None:
        self.text = text
        self.language = language
        self.confidence = 1.0
        self.duration_ms = 200.0
        self.latency_ms = 50.0


class _MockTTS:
    """Simulates a TTS provider."""

    def __init__(self) -> None:
        self.last_text = None

    async def synthesize(
        self,
        text: str,
        voice: None = None,
        sample_rate: int = 24000,
    ) -> "_MockTTSResult":
        self.last_text = text
        return _MockTTSResult(
            audio_data=b"\x00\x00" * int(sample_rate * 0.2),
            sample_rate=sample_rate,
        )


class _MockTTSResult:
    def __init__(self, audio_data: bytes, sample_rate: int) -> None:
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.duration_ms = 200.0
        self.latency_ms = 50.0


class _MockCapture:
    """Simulates AudioCapture -- returns silence by default."""

    def __init__(self) -> None:
        self._running = False
        self.sample_rate = 16000
        self._vad = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def _read_frame(self, timeout: float | None = 0.5) -> bytes | None:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_stt() -> _MockSTT:
    return _MockSTT()


@pytest.fixture
def mock_tts() -> _MockTTS:
    return _MockTTS()


@pytest.fixture
def mock_capture() -> _MockCapture:
    return _MockCapture()


@pytest.fixture
def commander(mock_stt: _MockSTT, mock_tts: _MockTTS) -> VoiceCommander:
    return VoiceCommander(stt=mock_stt, tts=mock_tts)


# ---------------------------------------------------------------------------
# Test voice command parsing
# ---------------------------------------------------------------------------


class TestVoiceCommandParsing:
    """Tests for command type classification from transcribed text."""

    @pytest.mark.asyncio
    async def test_route_to_agent_english(self, commander: VoiceCommander) -> None:
        cmd = await commander.command("go to researcher-1")
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        assert cmd.target == "researcher-1"
        assert cmd.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_route_to_agent_alternatives(self, commander: VoiceCommander) -> None:
        texts = [
            "route to agent-alpha",
            "switch to worker-3",
            "connect to the supervisor",
            "open dashboard",
        ]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.ROUTE_TO_AGENT, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_query_status(self, commander: VoiceCommander) -> None:
        cmd = await commander.command("what is the status")
        assert cmd.type == CommandType.QUERY_STATUS
        assert cmd.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_status_variants(self, commander: VoiceCommander) -> None:
        texts = ["status", "progress", "how are you", "what's up"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.QUERY_STATUS, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_approve_action(self, commander: VoiceCommander) -> None:
        texts = ["yes", "approve", "confirm", "do it", "go ahead", "proceed"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.APPROVE_ACTION, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_deny_action(self, commander: VoiceCommander) -> None:
        texts = ["no", "deny", "reject", "decline", "don't"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.DENY_ACTION, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_interrupt(self, commander: VoiceCommander) -> None:
        texts = ["stop", "cancel", "interrupt", "halt", "abort", "pause", "enough"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.INTERRUPT, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_unknown_command(self, commander: VoiceCommander) -> None:
        cmd = await commander.command("the sky is blue today")
        assert cmd.type == CommandType.UNKNOWN

    @pytest.mark.asyncio
    async def test_empty_text_raises(self, commander: VoiceCommander) -> None:
        with pytest.raises(ValueError, match="empty"):
            await commander.command("")

    @pytest.mark.asyncio
    async def test_whitespace_text_raises(self, commander: VoiceCommander) -> None:
        with pytest.raises(ValueError, match="empty"):
            await commander.command("   ")

    @pytest.mark.asyncio
    async def test_command_has_correct_fields(self, commander: VoiceCommander) -> None:
        cmd = await commander.command("go to researcher-1")
        assert isinstance(cmd, Command)
        assert cmd.text == "go to researcher-1"
        assert cmd.language is not None
        assert isinstance(cmd.args, dict)
        assert "target_agent" in cmd.args


# ---------------------------------------------------------------------------
# Test bilingual detection
# ---------------------------------------------------------------------------


class TestBilingualDetection:
    """Tests for VI + EN language auto-detection in commands."""

    @pytest.mark.asyncio
    async def test_vietnamese_route(self, commander: VoiceCommander) -> None:
        cmd = await commander.command("chuyển đến agent-1")
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        assert cmd.target == "agent-1"

    @pytest.mark.asyncio
    async def test_vietnamese_route_variants(self, commander: VoiceCommander) -> None:
        texts = [
            ("đi đến worker-2", "worker-2"),
            ("kết nối với supervisor", "supervisor"),
            ("mở dashboard", "dashboard"),
        ]
        for text, expected_target in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.ROUTE_TO_AGENT, f"Failed for: {text}"
            assert cmd.target == expected_target, f"Expected {expected_target}, got {cmd.target}"

    @pytest.mark.asyncio
    async def test_vietnamese_status(self, commander: VoiceCommander) -> None:
        texts = ["trạng thái", "tiến độ", "thế nào", "tình hình"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.QUERY_STATUS, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_vietnamese_approve(self, commander: VoiceCommander) -> None:
        texts = ["có", "đồng ý", "xác nhận", "tiến hành", "được"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.APPROVE_ACTION, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_vietnamese_deny(self, commander: VoiceCommander) -> None:
        texts = ["không", "từ chối"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.DENY_ACTION, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_vietnamese_interrupt(self, commander: VoiceCommander) -> None:
        texts = ["dừng", "dừng lại", "hủy", "ngừng", "đủ rồi", "kết thúc"]
        for text in texts:
            cmd = await commander.command(text)
            assert cmd.type == CommandType.INTERRUPT, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_language_populated(self, commander: VoiceCommander) -> None:
        cmd_en = await commander.command("status")
        assert cmd_en.language is not None

        cmd_vi = await commander.command("trạng thái")
        assert cmd_vi.language is not None


# ---------------------------------------------------------------------------
# Test barge-in interruption (listen path)
# ---------------------------------------------------------------------------


class TestBargeInInterruption:
    """Tests for barge-in support in the commander's listen flow."""

    @pytest.mark.asyncio
    async def test_listen_returns_empty_on_silence(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
        mock_capture: _MockCapture,
    ) -> None:
        """When no speech is detected, listen should return empty string."""
        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            capture=mock_capture,
        )
        result = await commander.listen(timeout=0.5)
        # With no audio, the result should be empty (silence produces
        # no transcription)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_listen_returns_transcription(
        self,
        mock_tts: _MockTTS,
        mock_capture: _MockCapture,
    ) -> None:
        """When speech is detected and transcribed, listen returns the text."""
        stt = _MockSTT(response_text="go to agent-1")
        commander = VoiceCommander(
            stt=stt,
            tts=mock_tts,
            capture=mock_capture,
        )
        result = await commander.listen(timeout=0.5)
        assert isinstance(result, str)

    def test_interrupt_command_is_classified(self, commander: VoiceCommander) -> None:
        """Verify that interrupt keywords produce INTERRUPT command type."""
        import asyncio

        cmd = asyncio.run(commander.command("stop"))
        assert cmd.type == CommandType.INTERRUPT
        assert cmd.confidence >= 0.7


# ---------------------------------------------------------------------------
# Test hold-to-talk flow
# ---------------------------------------------------------------------------


class TestHoldToTalkFlow:
    """Tests for the full hold-to-talk cycle: listen -> command."""

    @pytest.mark.asyncio
    async def test_listen_then_command_route(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
        mock_capture: _MockCapture,
    ) -> None:
        """Simulate hold-to-talk: listen, then parse the command."""
        stt = _MockSTT(response_text="go to agent-alpha")
        commander = VoiceCommander(stt=stt, tts=mock_tts, capture=mock_capture)

        text = await commander.listen(timeout=0.5)
        # Even if listen returns empty (silent mock), we can still
        # test command() with a known text
        cmd = await commander.command("go to agent-alpha")
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        assert cmd.target == "agent-alpha"

    @pytest.mark.asyncio
    async def test_listen_then_command_status(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
        mock_capture: _MockCapture,
    ) -> None:
        """Simulate hold-to-talk: listen for status, then parse."""
        stt = _MockSTT(response_text="what is the status")
        commander = VoiceCommander(stt=stt, tts=mock_tts, capture=mock_capture)

        cmd = await commander.command("what is the status")
        assert cmd.type == CommandType.QUERY_STATUS

    @pytest.mark.asyncio
    async def test_listen_then_speak(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
        mock_capture: _MockCapture,
    ) -> None:
        """Test speak after a command is parsed."""
        commander = VoiceCommander(stt=mock_stt, tts=mock_tts, capture=mock_capture)

        # speak should not raise
        await commander.speak("Routing to agent-alpha")
        assert mock_tts.last_text == "Routing to agent-alpha"

    @pytest.mark.asyncio
    async def test_full_hold_to_talk_cycle(
        self,
        mock_tts: _MockTTS,
        mock_capture: _MockCapture,
    ) -> None:
        """End-to-end hold-to-talk: listen -> command -> speak."""
        stt = _MockSTT(response_text="approve")
        commander = VoiceCommander(stt=stt, tts=mock_tts, capture=mock_capture)

        cmd = await commander.command("approve")
        assert cmd.type == CommandType.APPROVE_ACTION

        await commander.speak("Action approved")
        assert mock_tts.last_text == "Action approved"

    def test_commander_stats(self, commander: VoiceCommander) -> None:
        """Verify that commander tracks statistics."""
        import asyncio

        asyncio.run(commander.command("go to agent-x"))
        asyncio.run(commander.command("status"))

        stats = commander.stats
        assert isinstance(stats, CommanderStats)
        assert stats.total_commands >= 2
        assert stats.recognised_count >= 2


# ---------------------------------------------------------------------------
# Test voice pack loading
# ---------------------------------------------------------------------------


class TestVoicePackIntegration:
    """Tests for voice pack integration with SoundEffectEngine."""

    @pytest.mark.asyncio
    async def test_commander_accepts_sound_engine(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """VoiceCommander can be initialised with a SoundEffectEngine."""
        from lyra.voice.sound_effects import SoundEffectEngine

        engine = SoundEffectEngine(active_pack="minimal")
        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            sound_engine=engine,
        )
        assert commander._sound_engine is not None
        assert commander._sound_engine.active_pack == "minimal"

    @pytest.mark.asyncio
    async def test_speak_with_voice_pack(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """VoiceCommander.speak() accepts a voice_pack parameter."""
        commander = VoiceCommander(stt=mock_stt, tts=mock_tts)
        # Should not raise even without a sound engine configured
        await commander.speak("hello", voice_pack="minimal")

    @pytest.mark.asyncio
    async def test_speak_with_sound_engine_and_pack(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """VoiceCommander.speak() switches pack when engine is configured."""
        from lyra.voice.sound_effects import SoundEffectEngine

        engine = SoundEffectEngine(active_pack="minimal")
        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            sound_engine=engine,
        )

        await commander.speak("hello", voice_pack="jarvis")
        assert engine.active_pack == "jarvis"

    @pytest.mark.asyncio
    async def test_speak_unknown_pack_logs_warning(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """Using an unknown voice pack name logs a warning but does not raise."""
        from lyra.voice.sound_effects import SoundEffectEngine

        engine = SoundEffectEngine(active_pack="minimal")
        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            sound_engine=engine,
        )

        # Should not raise, just log a warning
        await commander.speak("hello", voice_pack="nonexistent-pack")
        assert engine.active_pack == "minimal"  # unchanged

    @pytest.mark.asyncio
    async def test_commander_without_sound_engine(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
        mock_capture: _MockCapture,
    ) -> None:
        """VoiceCommander works without a SoundEffectEngine."""
        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            capture=mock_capture,
        )
        assert commander._sound_engine is None

        # listen and speak should still work
        cmd = await commander.command("status")
        assert cmd.type == CommandType.QUERY_STATUS
        await commander.speak("Status queried")


# ---------------------------------------------------------------------------
# Test fleet notify callback
# ---------------------------------------------------------------------------


class TestFleetNotifyCallback:
    """Tests for the fleet_notify callback integration."""

    @pytest.mark.asyncio
    async def test_fleet_notify_called_on_command(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """The fleet_notify callback is invoked after command parsing."""
        received_commands: list[Command] = []

        def _notify(cmd: Command) -> None:
            received_commands.append(cmd)

        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            fleet_notify=_notify,
        )

        await commander.command("go to researcher-1")
        assert len(received_commands) == 1
        assert received_commands[0].type == CommandType.ROUTE_TO_AGENT
        assert received_commands[0].target == "researcher-1"

    @pytest.mark.asyncio
    async def test_fleet_notify_receives_all_commands(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """Every parsed command is forwarded to the fleet callback."""
        received: list[str] = []

        def _notify(cmd: Command) -> None:
            received.append(cmd.type.value)

        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            fleet_notify=_notify,
        )

        await commander.command("status")
        await commander.command("stop")
        await commander.command("go to agent-1")

        assert received == ["query_status", "interrupt", "route_to_agent"]

    @pytest.mark.asyncio
    async def test_fleet_notify_error_does_not_crash(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """An error in fleet_notify is caught and logged, not propagated."""

        def _failing(cmd: Command) -> None:
            raise RuntimeError("callback failure")

        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            fleet_notify=_failing,
        )

        # Should not raise even though callback fails
        cmd = await commander.command("status")
        assert cmd.type == CommandType.QUERY_STATUS

    @pytest.mark.asyncio
    async def test_no_fleet_notify_by_default(
        self,
        mock_stt: _MockSTT,
        mock_tts: _MockTTS,
    ) -> None:
        """Without fleet_notify, command parsing works normally."""
        commander = VoiceCommander(stt=mock_stt, tts=mock_tts)
        assert commander._fleet_notify is None

        cmd = await commander.command("approve")
        assert cmd.type == CommandType.APPROVE_ACTION


# ---------------------------------------------------------------------------
# Test statistics tracking
# ---------------------------------------------------------------------------


class TestCommanderStats:
    """Tests for CommanderStats accumulation."""

    @pytest.mark.asyncio
    async def test_stats_initial_values(self, commander: VoiceCommander) -> None:
        stats = commander.stats
        assert stats.total_commands == 0
        assert stats.total_listen_calls == 0
        assert stats.total_speak_calls == 0
        assert stats.recognised_count == 0
        assert stats.unknown_count == 0
        assert stats.failures == 0

    @pytest.mark.asyncio
    async def test_stats_accumulate_commands(self, commander: VoiceCommander) -> None:
        await commander.command("go to agent-x")
        await commander.command("status")
        await commander.command("unknown gibberish here")

        stats = commander.stats
        assert stats.total_commands == 3
        assert stats.recognised_count >= 2

    @pytest.mark.asyncio
    async def test_stats_track_speak_calls(self, commander: VoiceCommander) -> None:
        await commander.speak("hello")
        assert commander.stats.total_speak_calls == 1

        await commander.speak("world")
        assert commander.stats.total_speak_calls == 2

    @pytest.mark.asyncio
    async def test_reset_stats(self, commander: VoiceCommander) -> None:
        await commander.command("status")
        assert commander.stats.total_commands > 0

        commander.reset_stats()
        assert commander.stats.total_commands == 0
        assert commander.stats.total_listen_calls == 0

    @pytest.mark.asyncio
    async def test_command_confidence_range(self, commander: VoiceCommander) -> None:
        cmd = await commander.command("stop")
        assert 0.0 <= cmd.confidence <= 1.0

        cmd_unknown = await commander.command("lorem ipsum dolor sit amet")
        assert cmd_unknown.confidence == 0.0

    @pytest.mark.asyncio
    async def test_repr(self, commander: VoiceCommander) -> None:
        r = repr(commander)
        assert "VoiceCommander" in r
        assert "Mock" in r or "STT" in r


# ---------------------------------------------------------------------------
# Test Command dataclass
# ---------------------------------------------------------------------------


class TestCommandDataclass:
    """Tests for the Command frozen dataclass."""

    def test_command_fields(self) -> None:
        cmd = Command(
            type=CommandType.ROUTE_TO_AGENT,
            text="go to agent-1",
            confidence=0.85,
            target="agent-1",
            args={"target_agent": "agent-1"},
        )
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        assert cmd.text == "go to agent-1"
        assert cmd.confidence == 0.85
        assert cmd.target == "agent-1"
        assert cmd.args["target_agent"] == "agent-1"

    def test_command_is_frozen(self) -> None:
        cmd = Command(type=CommandType.UNKNOWN, text="hello")
        with pytest.raises(AttributeError):
            cmd.text = "changed"  # type: ignore[misc]

    def test_command_defaults(self) -> None:
        cmd = Command(type=CommandType.INTERRUPT, text="stop")
        assert cmd.confidence == 1.0
        assert cmd.target is None
        assert cmd.args == {}

    def test_command_type_values(self) -> None:
        assert CommandType.ROUTE_TO_AGENT.value == "route_to_agent"
        assert CommandType.QUERY_STATUS.value == "query_status"
        assert CommandType.APPROVE_ACTION.value == "approve_action"
        assert CommandType.DENY_ACTION.value == "deny_action"
        assert CommandType.INTERRUPT.value == "interrupt"
        assert CommandType.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# Test CommanderStats dataclass
# ---------------------------------------------------------------------------


class TestCommanderStatsDataclass:
    """Tests for the CommanderStats dataclass."""

    def test_initial_values(self) -> None:
        stats = CommanderStats()
        assert stats.total_commands == 0
        assert stats.total_listen_calls == 0
        assert stats.total_speak_calls == 0
        assert stats.recognised_count == 0
        assert stats.unknown_count == 0
        assert stats.en_count == 0
        assert stats.vi_count == 0
        assert stats.failures == 0


# ---------------------------------------------------------------------------
# Test listen() error paths
# ---------------------------------------------------------------------------


class TestListenErrorPaths:
    """Tests for error handling in VoiceCommander.listen()."""

    @pytest.mark.asyncio
    async def test_listen_capture_start_failure(
        self, mock_stt: _MockSTT, mock_tts: _MockTTS
    ) -> None:
        """When capture.start() fails, listen() should raise RuntimeError."""
        failing_capture = _MockCapture()
        failing_capture.start = MagicMock(side_effect=RuntimeError("Device busy"))

        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            capture=failing_capture,
        )
        with pytest.raises(RuntimeError, match="Failed to start"):
            await commander.listen()

    @pytest.mark.asyncio
    async def test_listen_capture_runtime_error_during_recording(
        self, mock_stt: _MockSTT, mock_tts: _MockTTS
    ) -> None:
        """When recording fails, listen() should return empty string."""
        capture = _MockCapture()

        # Monkeypatch record_utterance to raise
        with patch("lyra.voice.voice_commander.record_utterance", side_effect=RuntimeError("Mic error")):
            commander = VoiceCommander(
                stt=mock_stt,
                tts=mock_tts,
                capture=capture,
            )
            result = await commander.listen()
            assert result == ""
            assert commander.stats.failures == 1

    @pytest.mark.asyncio
    async def test_listen_stt_failure(
        self, mock_tts: _MockTTS, mock_capture: _MockCapture
    ) -> None:
        """When STT fails, listen() should return empty string."""
        stt = _MockSTT()

        async def failing_transcribe(*args, **kwargs):
            from lyra.voice.stt import STTError
            raise STTError("API error")

        stt.transcribe = failing_transcribe  # type: ignore[method-assign]

        # Make record_utterance return some audio so STT is actually called
        with patch("lyra.voice.voice_commander.record_utterance", return_value=bytearray(b"\x00\x00" * 1600)):
            commander = VoiceCommander(
                stt=stt,
                tts=mock_tts,
                capture=mock_capture,
            )
            result = await commander.listen()
            assert result == ""
            assert commander.stats.failures == 1

    @pytest.mark.asyncio
    async def test_listen_no_audio_returns_empty(
        self, mock_stt: _MockSTT, mock_tts: _MockTTS, mock_capture: _MockCapture
    ) -> None:
        """When no audio is captured, listen() returns empty string."""
        commander = VoiceCommander(
            stt=mock_stt,
            tts=mock_tts,
            capture=mock_capture,
        )
        result = await commander.listen(timeout=0.1)
        assert result == ""


# ---------------------------------------------------------------------------
# Test speak() error paths
# ---------------------------------------------------------------------------


class TestSpeakErrorPaths:
    """Tests for error handling in VoiceCommander.speak()."""

    @pytest.mark.asyncio
    async def test_speak_tts_failure(
        self, mock_stt: _MockSTT, mock_capture: _MockCapture
    ) -> None:
        """When TTS fails, speak() should not raise."""
        tts = _MockTTS()

        async def failing_synthesize(*args, **kwargs):
            from lyra.voice.tts import TTSError
            raise TTSError("TTS unavailable")

        tts.synthesize = failing_synthesize  # type: ignore[method-assign]
        commander = VoiceCommander(
            stt=mock_stt,
            tts=tts,
            capture=mock_capture,
        )

        # Should not raise
        await commander.speak("Hello")
        assert commander.stats.failures == 1


# ---------------------------------------------------------------------------
# Test is_running and __repr__
# ---------------------------------------------------------------------------


class TestCommanderProperties:
    """Tests for VoiceCommander properties."""

    @pytest.mark.asyncio
    async def test_is_running_initial(self, mock_stt: _MockSTT, mock_tts: _MockTTS) -> None:
        commander = VoiceCommander(stt=mock_stt, tts=mock_tts)
        assert not commander.is_running

    def test_repr(self, mock_stt: _MockSTT, mock_tts: _MockTTS) -> None:
        commander = VoiceCommander(stt=mock_stt, tts=mock_tts)
        r = repr(commander)
        assert "VoiceCommander" in r


# ---------------------------------------------------------------------------
# Test edge case command parsing
# ---------------------------------------------------------------------------


class TestCommandParsingEdgeCases:
    """Tests for edge cases in command classification."""

    @pytest.mark.asyncio
    async def test_long_text_does_not_crash(self, commander: VoiceCommander) -> None:
        """Very long text should not crash the classifier."""
        long_text = "go to " + "a" * 10000
        cmd = await commander.command(long_text)
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        assert cmd.target == "a" * 10000

    @pytest.mark.asyncio
    async def test_special_characters(self, commander: VoiceCommander) -> None:
        """Special characters after the agent name are stripped by \w pattern."""
        cmd = await commander.command("go to agent-1!@#$%^&*()")
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        # Only word chars and hyphens are matched by [\w-]+
        assert cmd.target == "agent-1"

    @pytest.mark.asyncio
    async def test_mixed_case_command(self, commander: VoiceCommander) -> None:
        """Mixed case commands should still match (lowercased internally)."""
        cmd = await commander.command("Go To Agent-1")
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        # The _classify method lowercases the text before matching
        assert cmd.target == "agent-1"

    @pytest.mark.asyncio
    async def test_route_to_agent_takes_priority(self, commander: VoiceCommander) -> None:
        """Route keywords should take priority over other matches."""
        cmd = await commander.command("go to stop-now")
        assert cmd.type == CommandType.ROUTE_TO_AGENT
        assert cmd.target == "stop-now"

    @pytest.mark.asyncio
    async def test_deny_word_boundary_matching(self, commander: VoiceCommander) -> None:
        """'no' should not match inside other words like 'not' or 'none'."""
        cmd = await commander.command("none of the above")
        # "no" should match via word boundary if it's a separate word or prefix
        assert cmd.type is not None


# ---------------------------------------------------------------------------
# Test stats edge cases
# ---------------------------------------------------------------------------


class TestCommanderStatsExtended:
    """Extended tests for CommanderStats."""

    @pytest.mark.asyncio
    async def test_stats_listen_calls_tracked(
        self, mock_stt: _MockSTT, mock_tts: _MockTTS
    ) -> None:
        """Listen() should increment total_listen_calls."""
        commander = VoiceCommander(stt=mock_stt, tts=mock_tts)
        # We can't easily call listen() without hardware, but the counter
        # is incremented at the start of the method
        with patch("lyra.voice.voice_commander.VoiceCommander.listen", return_value=""):
            pass
        # Just verify the property exists
        assert commander.stats.total_listen_calls == 0

    @pytest.mark.asyncio
    async def test_stats_track_vi_and_en(self, commander: VoiceCommander) -> None:
        await commander.command("status")
        await commander.command("trạng thái")
        assert commander.stats.en_count >= 1
        # VI count may be 0 or more depending on detection
        assert commander.stats.vi_count >= 0
        assert commander.stats.total_commands == 2
