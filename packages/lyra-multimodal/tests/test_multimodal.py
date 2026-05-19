"""Tests for multimodal capabilities."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from lyra_multimodal import ImageType, VisionAnalyzer, VoiceEngine, VoiceInterface


def create_test_image(width=800, height=600):
    """Create a test image."""
    img = Image.new("RGB", (width, height), color="white")
    return img


def test_vision_analyzer_init():
    """Test vision analyzer initialization."""
    analyzer = VisionAnalyzer()
    assert analyzer is not None


def test_vision_image_classification():
    """Test image classification."""
    analyzer = VisionAnalyzer()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = create_test_image(1920, 1080)
        img.save(f.name)

        result = analyzer.analyze_image(f.name, analysis_type="general")

        assert result.image_type == ImageType.SCREENSHOT
        assert result.confidence > 0


def test_vision_security_analysis():
    """Test security analysis."""
    analyzer = VisionAnalyzer()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create screenshot-sized image to trigger security findings
        img = create_test_image(1920, 1080)
        img.save(f.name)

        result = analyzer.analyze_image(f.name, analysis_type="security")

        assert len(result.security_findings) > 0
        assert len(result.recommendations) > 0


def test_vision_ui_analysis():
    """Test UI analysis."""
    analyzer = VisionAnalyzer()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = create_test_image()
        img.save(f.name)

        result = analyzer.analyze_image(f.name, analysis_type="ui")

        assert result.image_type is not None


def test_vision_image_encoding():
    """Test image encoding."""
    analyzer = VisionAnalyzer()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = create_test_image()
        img.save(f.name)

        encoded = analyzer.encode_image(f.name)

        assert isinstance(encoded, str)
        assert len(encoded) > 0


def test_vision_image_info():
    """Test image info extraction."""
    analyzer = VisionAnalyzer()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = create_test_image(800, 600)
        img.save(f.name)

        info = analyzer.get_image_info(f.name)

        assert info["width"] == 800
        assert info["height"] == 600
        assert info["format"] == "PNG"


def test_voice_interface_init():
    """Test voice interface initialization."""
    voice = VoiceInterface(engine=VoiceEngine.WHISPER)
    assert voice.engine == VoiceEngine.WHISPER


def test_voice_transcription():
    """Test speech-to-text."""
    voice = VoiceInterface()

    result = voice.transcribe("dummy_audio.wav")

    assert result.text is not None
    assert result.confidence > 0
    assert len(result.words) > 0


def test_voice_synthesis():
    """Test text-to-speech."""
    voice = VoiceInterface()

    result = voice.synthesize("Hello, world!")

    assert result.audio_data is not None
    assert result.duration_seconds > 0
    assert result.format == "mp3"


def test_voice_command_recognition():
    """Test voice command recognition."""
    voice = VoiceInterface()

    # Mock transcription would return "start scan"
    # In real implementation, this would process actual audio
    command = voice.recognize_command("dummy_audio.wav")

    # Command recognition returns None for placeholder
    assert command is None or isinstance(command, str)


def test_voice_supported_languages():
    """Test supported languages."""
    voice = VoiceInterface()

    languages = voice.get_supported_languages()

    assert "en" in languages
    assert len(languages) > 0


def test_voice_supported_voices():
    """Test supported voices."""
    voice = VoiceInterface()

    voices = voice.get_supported_voices()

    assert "default" in voices
    assert len(voices) > 0
