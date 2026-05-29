"""Tests for the lyra-voice package."""

from __future__ import annotations

import math
import struct
import time

import pytest
from lyra_voice import (
    ParsedCommand,
    VADMode,
    VADResult,
    VoiceCommand,
    VoiceCommandAction,
    VoiceConfig,
    VoiceInterface,
    VoiceSession,
    WakeWordConfig,
    WakeWordModel,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def interface() -> VoiceInterface:
    """Return a default VoiceInterface instance."""
    return VoiceInterface()


@pytest.fixture
def speech_chunk() -> bytes:
    """Return a raw PCM chunk simulating speech-level audio (RMS ~2000)."""
    return _build_pcm_chunk(rms=2000, num_samples=1600)


@pytest.fixture
def silence_chunk() -> bytes:
    """Return a raw PCM chunk with silence (RMS ~0)."""
    return _build_pcm_chunk(rms=0, num_samples=1600)


@pytest.fixture
def low_energy_chunk() -> bytes:
    """Return a raw PCM chunk with very low energy (RMS ~30)."""
    return _build_pcm_chunk(rms=30, num_samples=1600)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Verify all enum members and values."""

    def test_voice_command_action(self) -> None:
        assert VoiceCommandAction.EXECUTE.value == "EXECUTE"
        assert VoiceCommandAction.SEARCH.value == "SEARCH"
        assert VoiceCommandAction.NAVIGATE.value == "NAVIGATE"
        assert VoiceCommandAction.CREATE.value == "CREATE"
        assert VoiceCommandAction.EDIT.value == "EDIT"
        assert VoiceCommandAction.DELETE.value == "DELETE"
        assert VoiceCommandAction.QUERY.value == "QUERY"
        assert VoiceCommandAction.CANCEL.value == "CANCEL"
        assert VoiceCommandAction.HELP.value == "HELP"
        assert VoiceCommandAction.PAUSE.value == "PAUSE"
        assert VoiceCommandAction.RESUME.value == "RESUME"
        assert len(VoiceCommandAction) == 11

    def test_wake_word_model(self) -> None:
        assert WakeWordModel.PORCUPINE.value == "PORCUPINE"
        assert WakeWordModel.SNOWBOY.value == "SNOWBOY"
        assert WakeWordModel.OPENWAKEWORD.value == "OPENWAKEWORD"
        assert WakeWordModel.CUSTOM.value == "CUSTOM"
        assert WakeWordModel.NONE.value == "NONE"
        assert len(WakeWordModel) == 5

    def test_vad_mode(self) -> None:
        assert VADMode.ENERGY_THRESHOLD.value == "ENERGY_THRESHOLD"
        assert VADMode.WEBRTC.value == "WEBRTC"
        assert VADMode.SILERO.value == "SILERO"
        assert VADMode.HYBRID.value == "HYBRID"
        assert len(VADMode) == 4


# ---------------------------------------------------------------------------
# Data class tests
# ---------------------------------------------------------------------------


class TestDataClasses:
    """Verify all frozen dataclasses can be instantiated."""

    def test_wake_word_config_defaults(self) -> None:
        cfg = WakeWordConfig()
        assert cfg.model == "PORCUPINE"
        assert cfg.sensitivity == 0.5
        assert cfg.custom_keywords == ("hey lyra",)
        assert cfg.require_confirmation is True
        assert cfg.cooldown_ms == 2000

    def test_wake_word_config_custom(self) -> None:
        cfg = WakeWordConfig(
            model="CUSTOM",
            sensitivity=0.8,
            custom_keywords=("hello lyra", "ok lyra"),
            require_confirmation=False,
            cooldown_ms=1000,
        )
        assert cfg.model == "CUSTOM"
        assert cfg.sensitivity == 0.8
        assert cfg.custom_keywords == ("hello lyra", "ok lyra")
        assert cfg.require_confirmation is False
        assert cfg.cooldown_ms == 1000

    def test_voice_command(self) -> None:
        cmd = VoiceCommand(
            command_id="cmd_001",
            raw_text="search for documents",
            action="SEARCH",
            confidence=0.85,
            params=(("target", "documents"),),
        )
        assert cmd.command_id == "cmd_001"
        assert cmd.raw_text == "search for documents"
        assert cmd.action == "SEARCH"
        assert cmd.context == ""
        assert cmd.timestamp == 0.0

    def test_voice_command_with_context(self) -> None:
        now = time.time()
        cmd = VoiceCommand(
            command_id="cmd_002",
            raw_text="edit the file",
            action="EDIT",
            confidence=0.72,
            params=(("target", "file"),),
            context="dashboard_view",
            timestamp=now,
        )
        assert cmd.context == "dashboard_view"
        assert cmd.timestamp == now

    def test_parsed_command(self) -> None:
        parsed = ParsedCommand(
            original_text="create a new report",
            action="CREATE",
            intent="a new report",
            entities=(("target", "report"),),
            confidence=0.9,
            alternative_actions=("EXECUTE", "EDIT"),
        )
        assert parsed.original_text == "create a new report"
        assert parsed.action == "CREATE"
        assert parsed.intent == "a new report"
        assert len(parsed.entities) == 1
        assert parsed.entities[0] == ("target", "report")
        assert parsed.confidence == 0.9

    def test_parsed_command_empty_alternatives(self) -> None:
        parsed = ParsedCommand(
            original_text="help",
            action="HELP",
            intent="help",
            entities=(),
            confidence=0.5,
            alternative_actions=(),
        )
        assert parsed.alternative_actions == ()

    def test_vad_result(self) -> None:
        vad = VADResult(
            is_speech=True,
            confidence=0.87,
            energy_level=0.65,
            duration_ms=200.0,
            segment_start_ms=0.0,
            segment_end_ms=200.0,
        )
        assert vad.is_speech is True
        assert vad.confidence == 0.87
        assert vad.energy_level == 0.65
        assert vad.duration_ms == 200.0

    def test_vad_result_non_speech(self) -> None:
        vad = VADResult(
            is_speech=False,
            confidence=0.92,
            energy_level=0.01,
            duration_ms=100.0,
        )
        assert vad.is_speech is False
        assert vad.segment_start_ms == 0.0
        assert vad.segment_end_ms == 0.0

    def test_voice_session(self) -> None:
        session = VoiceSession(
            session_id="sess_001",
            start_time=1000.0,
            is_active=True,
            command_count=3,
            last_command="query the database",
            total_audio_processed_ms=5000.0,
        )
        assert session.session_id == "sess_001"
        assert session.is_active is True
        assert session.command_count == 3
        assert session.total_audio_processed_ms == 5000.0

    def test_voice_session_defaults(self) -> None:
        session = VoiceSession(
            session_id="sess_002",
            start_time=2000.0,
            is_active=False,
            command_count=0,
            last_command="",
            total_audio_processed_ms=0.0,
        )
        assert session.is_active is False
        assert session.last_command == ""

    def test_voice_config_defaults(self) -> None:
        cfg = VoiceConfig()
        assert cfg.vad_mode == "ENERGY_THRESHOLD"
        assert cfg.vad_sensitivity == 0.5
        assert cfg.wake_word_enabled is True
        assert cfg.auto_punctuate is True
        assert cfg.max_command_length == 500
        assert cfg.language == "en"
        assert cfg.echo_cancellation is True

    def test_voice_config_custom(self) -> None:
        cfg = VoiceConfig(
            vad_mode="WEBRTC",
            vad_sensitivity=0.3,
            wake_word_enabled=False,
            auto_punctuate=False,
            max_command_length=200,
            language="fr",
            echo_cancellation=False,
        )
        assert cfg.vad_mode == "WEBRTC"
        assert cfg.wake_word_enabled is False
        assert cfg.max_command_length == 200
        assert cfg.language == "fr"
        assert cfg.echo_cancellation is False


# ---------------------------------------------------------------------------
# VoiceInterface initialization
# ---------------------------------------------------------------------------


class TestVoiceInterfaceInit:
    """Verify VoiceInterface initialization."""

    def test_default_config(self, interface: VoiceInterface) -> None:
        assert interface._config.vad_mode == "ENERGY_THRESHOLD"
        assert interface._config.wake_word_enabled is True
        stats = interface.get_stats()
        assert all(v == 0 for v in stats.values())

    def test_custom_config(self) -> None:
        cfg = VoiceConfig(wake_word_enabled=False, vad_mode="SILERO")
        vi = VoiceInterface(config=cfg)
        assert vi._config.wake_word_enabled is False
        assert vi._config.vad_mode == "SILERO"

    def test_custom_wake_word_config(self) -> None:
        ww_cfg = WakeWordConfig(model="SNOWBOY", sensitivity=0.9)
        vi = VoiceInterface(wake_word_config=ww_cfg)
        assert vi._wake_word_config.model == "SNOWBOY"
        assert vi._wake_word_config.sensitivity == 0.9

    def test_both_configs(self) -> None:
        cfg = VoiceConfig(wake_word_enabled=True)
        ww_cfg = WakeWordConfig(cooldown_ms=500)
        vi = VoiceInterface(config=cfg, wake_word_config=ww_cfg)
        assert vi._config.wake_word_enabled is True
        assert vi._wake_word_config.cooldown_ms == 500


# ---------------------------------------------------------------------------
# Wake word detection
# ---------------------------------------------------------------------------


class TestDetectWakeWord:
    """Verify detect_wake_word method."""

    def test_detect_wake_word_speech(self, interface: VoiceInterface, speech_chunk: bytes) -> None:
        result = interface.detect_wake_word(speech_chunk)
        assert result is True

    def test_detect_wake_word_silence(self, interface: VoiceInterface, silence_chunk: bytes) -> None:
        result = interface.detect_wake_word(silence_chunk)
        assert result is False

    def test_detect_wake_word_low_energy(self, interface: VoiceInterface, low_energy_chunk: bytes) -> None:
        result = interface.detect_wake_word(low_energy_chunk)
        assert result is False

    def test_detect_wake_word_disabled(self, speech_chunk: bytes) -> None:
        cfg = VoiceConfig(wake_word_enabled=False)
        vi = VoiceInterface(config=cfg)
        result = vi.detect_wake_word(speech_chunk)
        assert result is False

    def test_detect_wake_word_empty(self, interface: VoiceInterface) -> None:
        result = interface.detect_wake_word(b"")
        assert result is False

    def test_detect_wake_word_short_chunk(self, interface: VoiceInterface) -> None:
        result = interface.detect_wake_word(b"\x00\x01")
        assert result is False

    def test_detect_wake_word_cooldown(self, interface: VoiceInterface, speech_chunk: bytes) -> None:
        """First detection should succeed, second should fail due to cooldown."""
        first = interface.detect_wake_word(speech_chunk)
        assert first is True
        # Immediately retry — should be blocked by cooldown
        second = interface.detect_wake_word(speech_chunk)
        assert second is False

    def test_detect_wake_word_custom_sensitivity(self, speech_chunk: bytes) -> None:
        """Very low sensitivity should prevent detection of moderate audio."""
        ww_cfg = WakeWordConfig(sensitivity=0.01)
        vi = VoiceInterface(wake_word_config=ww_cfg)
        result = vi.detect_wake_word(speech_chunk)
        assert result is False


# ---------------------------------------------------------------------------
# Voice activity detection
# ---------------------------------------------------------------------------


class TestDetectVoiceActivity:
    """Verify detect_voice_activity method."""

    def test_vad_speech(self, interface: VoiceInterface, speech_chunk: bytes) -> None:
        result = interface.detect_voice_activity(speech_chunk)
        assert isinstance(result, VADResult)
        assert result.is_speech is True
        assert result.energy_level > 0.1
        assert result.duration_ms > 0

    def test_vad_silence(self, interface: VoiceInterface, silence_chunk: bytes) -> None:
        result = interface.detect_voice_activity(silence_chunk)
        assert result.is_speech is False
        assert result.energy_level == 0.0

    def test_vad_low_energy(self, interface: VoiceInterface, low_energy_chunk: bytes) -> None:
        result = interface.detect_voice_activity(low_energy_chunk)
        assert result.is_speech is False
        assert result.energy_level < 0.05

    def test_vad_empty(self, interface: VoiceInterface) -> None:
        result = interface.detect_voice_activity(b"")
        assert result.is_speech is False
        assert result.confidence == 0.0
        assert result.duration_ms == 0.0

    def test_vad_high_sensitivity(self, low_energy_chunk: bytes) -> None:
        """Increased sensitivity should detect lower energy speech."""
        cfg = VoiceConfig(vad_sensitivity=1.0)
        vi = VoiceInterface(config=cfg)
        result = vi.detect_voice_activity(low_energy_chunk)
        # High sensitivity: very low energy may still be classified as speech
        assert result.is_speech is True

    def test_vad_very_low_sensitivity(self, speech_chunk: bytes) -> None:
        """Very low sensitivity may miss speech."""
        cfg = VoiceConfig(vad_sensitivity=0.01)
        vi = VoiceInterface(config=cfg)
        result = vi.detect_voice_activity(speech_chunk)
        assert result.is_speech is True

    def test_vad_duration_accuracy(self, interface: VoiceInterface) -> None:
        """Verify duration calculation for a known-length chunk."""
        chunk = _build_pcm_chunk(rms=1000, num_samples=1600)
        result = interface.detect_voice_activity(chunk, sample_rate=16000)
        # 1600 samples / 16000 Hz = 0.1 seconds = 100 ms
        assert result.duration_ms == pytest.approx(100.0, rel=0.01)


# ---------------------------------------------------------------------------
# Command parsing
# ---------------------------------------------------------------------------


class TestParseCommand:
    """Verify parse_command method."""

    def test_parse_search(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("search for documents")
        assert result.action == "SEARCH"
        assert result.intent != ""
        assert result.confidence > 0.5

    def test_parse_navigate(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("navigate to home")
        assert result.action == "NAVIGATE"

    def test_parse_create(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("create a new file")
        assert result.action == "CREATE"

    def test_parse_query(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("what is the weather")
        assert result.action == "QUERY"

    def test_parse_help(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("help me")
        assert result.action == "HELP"

    def test_parse_empty(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("")
        assert result.confidence == 0.0
        assert result.action == "QUERY"
        assert result.intent == "unknown"

    def test_parse_with_entities(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("search for quarterly report")
        assert len(result.entities) >= 1
        entity_types = [e[0] for e in result.entities]
        assert "target" in entity_types

    def test_parse_with_context(self, interface: VoiceInterface) -> None:
        result_no_ctx = interface.parse_command("find reports", context="")
        result_with_ctx = interface.parse_command("find reports", context="dashboard")
        # Context should boost confidence
        assert result_with_ctx.confidence >= result_no_ctx.confidence

    def test_parse_alternative_actions(self, interface: VoiceInterface) -> None:
        result = interface.parse_command("delete the file")
        assert result.action == "DELETE"
        assert len(result.alternative_actions) == len(VoiceCommandAction) - 1
        assert "DELETE" not in result.alternative_actions

    def test_parse_truncates_long_commands(self) -> None:
        cfg = VoiceConfig(max_command_length=20)
        vi = VoiceInterface(config=cfg)
        result = vi.parse_command("a" * 100)
        # Intent should be short, action still detected
        assert result.action is not None


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------


class TestExecuteCommand:
    """Verify execute_command method."""

    def test_execute_search(self, interface: VoiceInterface) -> None:
        parsed = interface.parse_command("search for documents")
        result = interface.execute_command(parsed)
        assert result["status"] == "ok"
        assert result["action"] == "SEARCH"
        assert result["executed"] is True
        assert "results" in result

    def test_execute_create(self, interface: VoiceInterface) -> None:
        parsed = interface.parse_command("create a report")
        result = interface.execute_command(parsed)
        assert result["action"] == "CREATE"
        assert "resource_id" in result

    def test_execute_cancel(self, interface: VoiceInterface) -> None:
        parsed = interface.parse_command("cancel the task")
        result = interface.execute_command(parsed)
        assert result["action"] == "CANCEL"
        assert result["cancelled"] is True

    def test_execute_increments_counter(self, interface: VoiceInterface) -> None:
        parsed = interface.parse_command("search for files")
        stats_before = interface.get_stats()
        interface.execute_command(parsed)
        stats_after = interface.get_stats()
        assert stats_after["total_commands"] == stats_before["total_commands"] + 1


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    """Verify session start, command tracking, and end."""

    def test_start_session(self, interface: VoiceInterface) -> None:
        session = interface.start_session()
        assert session.is_active is True
        assert session.session_id != ""
        assert session.command_count == 0
        assert interface._active_session is not None

    def test_session_tracks_commands(self, interface: VoiceInterface) -> None:
        interface.start_session()
        parsed = interface.parse_command("search for items")
        interface.execute_command(parsed)
        assert interface._active_session is not None
        assert interface._active_session.command_count == 1

    def test_end_session(self, interface: VoiceInterface) -> None:
        interface.start_session()
        parsed = interface.parse_command("find reports")
        interface.execute_command(parsed)
        final = interface.end_session()
        assert final.is_active is False
        assert final.command_count == 1
        assert interface._active_session is None

    def test_end_session_no_active(self, interface: VoiceInterface) -> None:
        with pytest.raises(RuntimeError, match="No active session"):
            interface.end_session()

    def test_multiple_sessions(self, interface: VoiceInterface) -> None:
        interface.start_session()
        interface.end_session()
        interface.start_session()
        session2 = interface.end_session()
        assert session2.is_active is False
        assert interface.get_stats()["total_sessions"] == 2


# ---------------------------------------------------------------------------
# Audio stream processing
# ---------------------------------------------------------------------------


class TestProcessAudioStream:
    """Verify process_audio_stream method."""

    def test_process_speech_stream(self, interface: VoiceInterface) -> None:
        interface.start_session()
        chunks = [_build_pcm_chunk(rms=3000, num_samples=1600) for _ in range(3)]
        commands = interface.process_audio_stream(chunks)
        assert len(commands) >= 1
        for cmd in commands:
            assert isinstance(cmd, VoiceCommand)
            assert cmd.command_id != ""
            assert cmd.action != ""

    def test_process_silence_stream(self, interface: VoiceInterface) -> None:
        interface.start_session()
        chunks = [_build_pcm_chunk(rms=0, num_samples=1600) for _ in range(3)]
        commands = interface.process_audio_stream(chunks)
        assert commands == []

    def test_process_empty_stream(self, interface: VoiceInterface) -> None:
        interface.start_session()
        commands = interface.process_audio_stream([])
        assert commands == []

    def test_process_without_session(self, interface: VoiceInterface) -> None:
        """process_audio_stream should work even without an active session."""
        chunks = [_build_pcm_chunk(rms=3000, num_samples=1600) for _ in range(2)]
        commands = interface.process_audio_stream(chunks)
        assert isinstance(commands, list)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestGetStats:
    """Verify get_stats method."""

    def test_initial_stats(self, interface: VoiceInterface) -> None:
        stats = interface.get_stats()
        assert stats["total_sessions"] == 0
        assert stats["total_commands"] == 0
        assert stats["total_wake_words_detected"] == 0
        assert stats["total_speech_segments"] == 0

    def test_stats_after_session(self, interface: VoiceInterface) -> None:
        interface.start_session()
        interface.end_session()
        stats = interface.get_stats()
        assert stats["total_sessions"] == 1

    def test_stats_after_wake_word(self, interface: VoiceInterface, speech_chunk: bytes) -> None:
        interface.detect_wake_word(speech_chunk)
        stats = interface.get_stats()
        assert stats["total_wake_words_detected"] == 1

    def test_stats_after_vad(self, interface: VoiceInterface, speech_chunk: bytes) -> None:
        interface.detect_voice_activity(speech_chunk)
        stats = interface.get_stats()
        assert stats["total_speech_segments"] == 1

    def test_stats_accumulate(self, interface: VoiceInterface) -> None:
        speech = _build_pcm_chunk(rms=2000, num_samples=1600)
        for _ in range(5):
            interface.detect_voice_activity(speech)
        assert interface.get_stats()["total_speech_segments"] == 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_pcm_chunk(rms: float, num_samples: int = 1600) -> bytes:
    """Build raw 16-bit mono PCM audio data with a target RMS energy.

    Generates a sine wave at 440 Hz with amplitude scaled to achieve the
    requested RMS value. A sine wave ``A * sin(t)`` has RMS = ``A / sqrt(2)``.

    Parameters
    ----------
    rms : float
        Desired RMS energy value.
    num_samples : int
        Number of 16-bit samples to generate. Defaults to 1600.

    Returns
    -------
    bytes
        Raw PCM bytes (little-endian 16-bit signed).
    """
    if rms <= 0:
        return b"\x00" * (num_samples * 2)

    amplitude = int(rms * math.sqrt(2))
    samples: list[int] = []
    for i in range(num_samples):
        sample = int(amplitude * math.sin(2 * math.pi * 440 * i / 16000))
        sample = max(-32768, min(32767, sample))
        samples.append(sample)

    return struct.pack(f"<{num_samples}h", *samples)
