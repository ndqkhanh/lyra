"""Tests for SoundNotifier, AgentState, SoundConfig, and get_sound_notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lyra_cli.voice.sound_notifications import (
    DEFAULT_SOUND_PRESETS,
    AgentState,
    SoundConfig,
    SoundNotifier,
    get_sound_notifier,
)


class TestAgentState:
    def test_values(self):
        assert AgentState.TASK_COMPLETE.value == "task_complete"
        assert AgentState.ERROR.value == "error"
        assert AgentState.WARNING.value == "warning"
        assert AgentState.AGENT_READY.value == "agent_ready"
        assert AgentState.AGENT_THINKING.value == "agent_thinking"

    def test_is_string_enum(self):
        assert isinstance(AgentState.TASK_COMPLETE.value, str)


class TestSoundConfig:
    def test_default_values(self):
        cfg = SoundConfig()
        assert cfg.enabled
        assert cfg.sound_path is None
        assert cfg.duration_ms == 200
        assert cfg.frequency == 440
        assert cfg.repetitions == 1

    def test_values_clamped(self):
        cfg = SoundConfig(duration_ms=0, frequency=10, repetitions=100)
        assert cfg.duration_ms == 50
        assert cfg.frequency == 20
        assert cfg.repetitions == 20

    def test_custom_values(self):
        cfg = SoundConfig(enabled=False, frequency=1000, duration_ms=500, repetitions=3)
        assert not cfg.enabled
        assert cfg.frequency == 1000
        assert cfg.duration_ms == 500
        assert cfg.repetitions == 3


class TestDefaultSoundPresets:
    def test_all_states_have_presets(self):
        for state in AgentState:
            assert state in DEFAULT_SOUND_PRESETS
            preset = DEFAULT_SOUND_PRESETS[state]
            assert isinstance(preset, SoundConfig)
            assert preset.enabled

    def test_preset_values_in_range(self):
        for state in AgentState:
            preset = DEFAULT_SOUND_PRESETS[state]
            assert 20 <= preset.frequency <= 20000
            assert 50 <= preset.duration_ms <= 5000
            assert 1 <= preset.repetitions <= 20


class TestSoundNotifier:
    def test_enabled_by_default(self):
        notifier = SoundNotifier()
        assert notifier.enabled

    def test_enable_disable_toggle(self):
        notifier = SoundNotifier()
        notifier.disable()
        assert not notifier.enabled
        notifier.enable()
        assert notifier.enabled
        assert notifier.toggle() is False
        assert notifier.toggle() is True

    def test_notify_does_nothing_when_disabled(self):
        notifier = SoundNotifier()
        notifier.disable()
        with patch.object(notifier, "_play_beep") as mock_beep:
            notifier.notify(AgentState.TASK_COMPLETE)
            mock_beep.assert_not_called()

    def test_notify_plays_default_beep(self):
        notifier = SoundNotifier()
        with patch.object(notifier, "_play_beep") as mock_beep:
            notifier.notify(AgentState.TASK_COMPLETE)
            mock_beep.assert_called_once()

    def test_notify_with_disabled_state_config(self):
        notifier = SoundNotifier()
        notifier.configure(AgentState.WARNING, SoundConfig(enabled=False))
        with patch.object(notifier, "_play_beep") as mock_beep:
            notifier.notify(AgentState.WARNING)
            mock_beep.assert_not_called()

    def test_configure_override(self):
        notifier = SoundNotifier()
        custom = SoundConfig(frequency=2000, repetitions=3)
        notifier.configure(AgentState.ERROR, custom)
        assert notifier.get_config(AgentState.ERROR).frequency == 2000
        assert notifier.get_config(AgentState.ERROR).repetitions == 3

    def test_get_config_returns_preset(self):
        notifier = SoundNotifier()
        for state in AgentState:
            cfg = notifier.get_config(state)
            assert isinstance(cfg, SoundConfig)
            assert cfg.enabled  # all presets are enabled by default

    def test_on_callback(self):
        notifier = SoundNotifier()
        callback = MagicMock()
        notifier.on(AgentState.TASK_COMPLETE, callback)

        with patch.object(notifier, "_play_beep"):
            notifier.notify(AgentState.TASK_COMPLETE)
            callback.assert_called_once()

    def test_on_callback_error_does_not_crash(self):
        notifier = SoundNotifier()
        def broken():
            raise RuntimeError("boom")
        notifier.on(AgentState.TASK_COMPLETE, broken)
        with patch.object(notifier, "_play_beep"):
            notifier.notify(AgentState.TASK_COMPLETE)  # should not raise

    @patch("subprocess.Popen")
    def test_play_file_macos(self, mock_popen):
        notifier = SoundNotifier()
        notifier._system = "Darwin"
        notifier._play_file("/tmp/test.wav")
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "afplay" in args

    def test_notify_with_unknown_state(self):
        """Unknown state should not raise."""
        notifier = SoundNotifier()
        with patch.object(notifier, "_play_beep") as mock_beep:
            notifier.notify(AgentState.AGENT_THINKING)
            mock_beep.assert_called_once()


class TestGetSoundNotifier:
    def test_returns_singleton(self):
        n1 = get_sound_notifier()
        n2 = get_sound_notifier()
        assert n1 is n2
        assert isinstance(n1, SoundNotifier)
