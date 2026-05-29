"""Tests for TTS engine — SystemSayBackend, Pyttsx3Backend, EdgeTTSBackend, factory, and
synthesize_speech."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from lyra_cli.voice.tts_engine import (
    EdgeTTSBackend,
    Pyttsx3Backend,
    SystemSayBackend,
    TTSConfig,
    TTSError,
    VoiceConfig,
    get_tts_engine,
    synthesize_speech,
)


class TestVoiceConfig:
    def test_default_values(self):
        vc = VoiceConfig()
        assert vc.name == "default"
        assert vc.speed == 1.0

    def test_invalid_speed_clamped(self):
        vc = VoiceConfig(speed=0.0)
        assert vc.speed == 1.0

    def test_valid_speed(self):
        vc = VoiceConfig(name="custom", speed=1.5)
        assert vc.name == "custom"
        assert vc.speed == 1.5


class TestTTSConfig:
    def test_default_values(self):
        cfg = TTSConfig()
        assert cfg.backend == "auto"
        assert cfg.voice.name == "default"

    def test_with_voice_and_output(self):
        vc = VoiceConfig(name="female", speed=1.2)
        cfg = TTSConfig(backend="edge-tts", voice=vc, output_dir="/tmp/tts")
        assert cfg.backend == "edge-tts"
        assert cfg.voice.name == "female"
        assert cfg.output_dir == "/tmp/tts"


class TestSystemSayBackend:
    def test_name(self):
        backend = SystemSayBackend()
        assert backend.name == "system-say"

    @patch("lyra_cli.voice.tts_engine.platform.system", return_value="Darwin")
    @patch("subprocess.run")
    def test_synthesize_macos(self, mock_run, _mock_platform):
        backend = SystemSayBackend()
        backend._available = True
        dest = Path("/tmp/test_tts_output.aiff")

        result = backend.synthesize("Hello world", dest)

        assert result == dest
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "say" in args
        assert "Hello world" in args

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_synthesize_command_not_found(self, mock_run):
        backend = SystemSayBackend()
        backend._available = True
        dest = Path("/tmp/test_tts_output.aiff")

        with pytest.raises(TTSError, match="command not found"):
            backend.synthesize("Hello", dest)

    @patch("subprocess.run")
    def test_synthesize_empty_text(self, mock_run):
        backend = SystemSayBackend()
        backend._available = True
        dest = Path("/tmp/test_tts_output.aiff")

        with pytest.raises(TTSError, match="empty text"):
            backend.synthesize("   ", dest)

    def test_voice_config_applied(self):
        backend = SystemSayBackend()
        backend._available = True
        vc = VoiceConfig(name="Samantha", speed=1.5)

        dest = Path("/tmp/test_voice_cfg.aiff")
        with patch("subprocess.run") as mock_run:
            backend.synthesize("Test", dest, voice=vc)
            args = mock_run.call_args[0][0]
            assert "-v" in args
            assert "Samantha" in args


class TestPyttsx3Backend:
    def test_name(self):
        backend = Pyttsx3Backend()
        assert backend.name == "pyttsx3"

    def test_not_available_if_not_installed(self):
        with patch(
            "lyra_cli.voice.tts_engine.Pyttsx3Backend._try_import",
            return_value=False,
        ):
            backend = Pyttsx3Backend()
            assert not backend.available

    @patch(
        "lyra_cli.voice.tts_engine.Pyttsx3Backend._try_import",
        return_value=True,
    )
    def test_synthesize_raises_on_empty_text(self, _mock):
        backend = Pyttsx3Backend()
        with pytest.raises(TTSError, match="empty text"):
            backend.synthesize("   ", Path("/tmp/test.wav"))

    @patch(
        "lyra_cli.voice.tts_engine.Pyttsx3Backend._try_import",
        return_value=False,
    )
    def test_synthesize_raises_when_not_available(self, _mock):
        backend = Pyttsx3Backend()
        with pytest.raises(TTSError, match="not installed"):
            backend.synthesize("Hello", Path("/tmp/test.wav"))

    def test_synthesize_success(self):
        backend = Pyttsx3Backend()
        backend._available = True

        with patch.object(backend, "synthesize") as mock_method:
            mock_method.return_value = Path("/tmp/test_pyttsx3.wav")
            dest = backend.synthesize("Hello world", Path("/tmp/test_pyttsx3.wav"))

        assert dest == Path("/tmp/test_pyttsx3.wav")


class TestEdgeTTSBackend:
    def test_name(self):
        backend = EdgeTTSBackend()
        assert backend.name == "edge-tts"

    def test_not_available_if_not_installed(self):
        with patch(
            "lyra_cli.voice.tts_engine.EdgeTTSBackend._try_import",
            return_value=False,
        ):
            backend = EdgeTTSBackend()
            assert not backend.available

    @patch(
        "lyra_cli.voice.tts_engine.EdgeTTSBackend._try_import",
        return_value=True,
    )
    def test_synthesize_raises_on_empty_text(self, _mock):
        backend = EdgeTTSBackend()
        with pytest.raises(TTSError, match="empty text"):
            backend.synthesize("", Path("/tmp/test.wav"))

    @patch(
        "lyra_cli.voice.tts_engine.EdgeTTSBackend._try_import",
        return_value=False,
    )
    def test_synthesize_raises_when_not_available(self, _mock):
        backend = EdgeTTSBackend()
        with pytest.raises(TTSError, match="not installed"):
            backend.synthesize("Hello", Path("/tmp/test.wav"))

    def test_resolve_voice_defaults(self):
        assert EdgeTTSBackend._resolve_voice("default") == "en-US-AriaNeural"
        assert EdgeTTSBackend._resolve_voice("male") == "en-US-GuyNeural"
        assert EdgeTTSBackend._resolve_voice("uk") == "en-GB-SoniaNeural"
        assert EdgeTTSBackend._resolve_voice("custom") == "custom"


class TestGetTTSEngine:
    def test_returns_system_say_as_fallback(self):
        with (
            patch(
                "lyra_cli.voice.tts_engine.EdgeTTSBackend._try_import",
                return_value=False,
            ),
            patch(
                "lyra_cli.voice.tts_engine.Pyttsx3Backend._try_import",
                return_value=False,
            ),
        ):
            engine = get_tts_engine()
            assert isinstance(engine, SystemSayBackend)

    def test_preferred_backend(self):
        engine = get_tts_engine("system-say")
        assert isinstance(engine, SystemSayBackend)

    def test_preferred_backend_unknown(self):
        with pytest.raises(TTSError, match="Unknown TTS backend"):
            get_tts_engine("nonexistent")


class TestSynthesizeSpeech:
    def test_empty_text_raises(self):
        with pytest.raises(TTSError, match="text must be non-empty"):
            synthesize_speech("")

    def test_with_explicit_backend(self):
        backend = MagicMock(spec=SystemSayBackend)
        backend.name = "mock"
        backend.synthesize.return_value = Path("/tmp/output.wav")

        result = synthesize_speech("Hello", backend=backend)
        assert result == Path("/tmp/output.wav")
        backend.synthesize.assert_called_once()

    def test_with_config(self):
        backend = MagicMock(spec=SystemSayBackend)
        backend.name = "mock"
        backend.synthesize.return_value = Path("/tmp/output.wav")
        config = TTSConfig(output_dir="/tmp/custom")

        result = synthesize_speech("Test", backend=backend, config=config)
        assert result == Path("/tmp/output.wav")

    def test_custom_dest(self):
        backend = MagicMock(spec=SystemSayBackend)
        backend.name = "mock"
        backend.synthesize.return_value = Path("/custom/path/out.wav")

        result = synthesize_speech("Hi", dest="/custom/path/out.wav", backend=backend)
        assert result == Path("/custom/path/out.wav")
