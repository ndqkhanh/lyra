"""Tests for STT engine — WhisperBackend, SpeechRecognitionBackend, transcribe_audio."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra_cli.voice.stt_engine import (
    STTError,
    STTResult,
    SpeechRecognitionBackend,
    WhisperBackend,
    detect_audio_format,
    transcribe_audio,
)


class TestSTTResult:
    def test_default_values(self):
        result = STTResult(text="hello")
        assert result.text == "hello"
        assert result.confidence == 0.0
        assert result.language == "en"

    def test_confidence_clamped(self):
        result = STTResult(text="test", confidence=2.0)
        assert result.confidence == 0.0

    def test_valid_confidence(self):
        result = STTResult(text="test", confidence=0.85)
        assert result.confidence == 0.85


class TestDetectAudioFormat:
    def test_supported_formats(self):
        for ext in [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"]:
            assert detect_audio_format(Path(f"test{ext}")) == ext

    def test_unsupported_format(self):
        assert detect_audio_format(Path("test.txt")) is None
        assert detect_audio_format(Path("test.mp4")) is None

    def test_case_insensitive(self):
        assert detect_audio_format(Path("test.WAV")) is not None


class TestWhisperBackend:
    def test_name(self):
        backend = WhisperBackend()
        assert backend.name == "whisper"

    def test_not_available_if_not_installed(self):
        with patch(
            "lyra_cli.voice.stt_engine.WhisperBackend._try_import",
            return_value=False,
        ):
            backend = WhisperBackend()
            assert not backend.available

    @patch(
        "lyra_cli.voice.stt_engine.WhisperBackend._try_import",
        return_value=False,
    )
    def test_transcribe_raises_when_not_available(self, _mock):
        backend = WhisperBackend()
        with pytest.raises(STTError, match="not installed"):
            backend.transcribe(audio_path=Path("/tmp/test.wav"))

    def test_transcribe_with_faster_whisper(self):
        backend = WhisperBackend()
        backend._available = True
        backend._use_faster = True

        with patch.object(backend, "_transcribe_faster") as mock_method:
            mock_method.return_value = STTResult(
                text="hello world", confidence=0.75, language="en",
            )
            result = backend.transcribe(audio_path=Path("/tmp/test.wav"))

        assert result.text == "hello world"
        assert result.language == "en"
        assert result.confidence == 0.75

    def test_transcribe_with_regular_whisper(self):
        backend = WhisperBackend()
        backend._available = True

        with patch.object(backend, "_transcribe_whisper") as mock_method:
            expected = STTResult(
                text="hello world", confidence=0.92, language="en", duration_seconds=2.5,
            )
            mock_method.return_value = expected
            result = backend.transcribe(audio_path=Path("/tmp/test.wav"))

        assert result.text == "hello world"
        assert result.confidence == 0.92
        assert result.duration_seconds == 2.5


class TestSpeechRecognitionBackend:
    def test_name(self):
        backend = SpeechRecognitionBackend()
        assert backend.name == "speech-recognition"

    def test_not_available_if_not_installed(self):
        with patch(
            "lyra_cli.voice.stt_engine.SpeechRecognitionBackend._try_import",
            return_value=False,
        ):
            backend = SpeechRecognitionBackend()
            assert not backend.available

    @patch(
        "lyra_cli.voice.stt_engine.SpeechRecognitionBackend._try_import",
        return_value=False,
    )
    def test_transcribe_raises_when_not_available(self, _mock):
        backend = SpeechRecognitionBackend()
        with pytest.raises(STTError, match="not installed"):
            backend.transcribe(audio_path=Path("/tmp/test.wav"))

    def test_transcribe_success(self):
        backend = SpeechRecognitionBackend()
        backend._available = True

        with patch.object(backend, "transcribe") as mock_method:
            mock_method.return_value = STTResult(text="hello world", confidence=0.95)
            result = backend.transcribe(audio_path=Path("/tmp/test.wav"))

        assert result.text == "hello world"
        assert result.confidence == 0.95

    def test_transcribe_no_result(self):
        backend = SpeechRecognitionBackend()
        backend._available = True

        with patch.object(backend, "transcribe") as mock_method:
            mock_method.return_value = STTResult(text="", confidence=0.0)
            result = backend.transcribe(audio_path=Path("/tmp/test.wav"))

        assert result.text == ""
        assert result.confidence == 0.0


class TestTranscribeAudio:
    def test_unsupported_format_raises(self):
        with pytest.raises(STTError, match="Unsupported audio format"):
            transcribe_audio("/tmp/test.txt")

    @patch("lyra_cli.voice.stt_engine._auto_detect_backend")
    def test_with_auto_backend(self, mock_auto):
        mock_backend = MagicMock()
        mock_backend.transcribe.return_value = STTResult(text="hello", confidence=0.9)
        mock_auto.return_value = mock_backend

        result = transcribe_audio("/tmp/test.wav")
        assert result.text == "hello"
        assert result.confidence == 0.9

    def test_with_explicit_backend(self):
        mock_backend = MagicMock()
        mock_backend.name = "mock"
        mock_backend.transcribe.return_value = STTResult(text="explicit", confidence=0.8)

        result = transcribe_audio("/tmp/test.wav", backend=mock_backend)
        assert result.text == "explicit"
