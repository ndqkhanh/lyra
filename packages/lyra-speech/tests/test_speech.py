"""Tests for lyra-speech."""
import pytest
from lyra_speech import SpeechModule


class TestSpeechModule:
    @pytest.mark.asyncio
    async def test_synthesize(self):
        s = SpeechModule()
        data = await s.synthesize("Hello world")
        assert isinstance(data, bytes)
        assert s.stats["synthesized"] >= 1

    @pytest.mark.asyncio
    async def test_transcribe(self):
        s = SpeechModule()
        cmd = await s.transcribe(b"fake_audio")
        assert cmd.transcript is not None
        assert cmd.confidence > 0

    @pytest.mark.asyncio
    async def test_identify_speaker(self):
        s = SpeechModule()
        profile = await s.identify_speaker(b"fake_audio")
        assert profile.speaker_id is not None

    @pytest.mark.asyncio
    async def test_detect_emotion(self):
        s = SpeechModule()
        emotion = await s.detect_emotion(b"fake_audio")
        assert isinstance(emotion, str)
