"""Tests for the lyra-speech package."""

from __future__ import annotations

import struct

import pytest

from lyra_speech import (
    AudioFormat,
    Emotion,
    EmotionResult,
    SpeakerIdentity,
    SpeechConfig,
    SpeechModule,
    SynthesisOptions,
    TranscriptionResult,
    VoiceGender,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def module() -> SpeechModule:
    """Return a default SpeechModule instance."""
    return SpeechModule()


@pytest.fixture
def wav_data() -> bytes:
    """Return a minimal valid WAV file with non-zero PCM samples (a 440 Hz tone)."""
    sample_rate = 16000
    channels = 1
    bits_per_sample = 16
    duration_ms = 200  # short tone
    num_samples = sample_rate * duration_ms // 1000

    block_align = channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    data_size = num_samples * block_align

    # PCM data — a brief 440 Hz sine wave at moderate amplitude
    pcm_data = b""
    amplitude = 8000
    for n in range(num_samples):
        t = n / sample_rate
        sample = int(amplitude * (2**0.5) * (t * 440 % 1 - 0.5) * 2)
        sample = max(-32768, min(32767, sample))
        pcm_data += struct.pack("<h", sample)

    # RIFF
    riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
    # fmt
    fmt_body = struct.pack(
        "<HHIIHH",
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )
    fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
    # data
    data_chunk = struct.pack("<4sI", b"data", data_size) + pcm_data

    return riff + fmt_chunk + data_chunk


# ---------------------------------------------------------------------------
# Data class instantiation
# ---------------------------------------------------------------------------


class TestDataClasses:
    """Verify all frozen dataclasses can be instantiated."""

    def test_voice_gender_enum(self) -> None:
        assert VoiceGender.MALE.value == "male"
        assert VoiceGender.FEMALE.value == "female"
        assert VoiceGender.NEUTRAL.value == "neutral"

    def test_emotion_enum(self) -> None:
        assert Emotion.NEUTRAL.value == "neutral"
        assert Emotion.HAPPY.value == "happy"
        assert Emotion.SAD.value == "sad"
        assert Emotion.ANGRY.value == "angry"
        assert Emotion.FEARFUL.value == "fearful"
        assert Emotion.SURPRISED.value == "surprised"
        assert Emotion.CALM.value == "calm"
        assert Emotion.EXCITED.value == "excited"

    def test_audio_format_enum(self) -> None:
        assert AudioFormat.WAV.value == "WAV"
        assert AudioFormat.MP3.value == "MP3"
        assert AudioFormat.OGG.value == "OGG"
        assert AudioFormat.FLAC.value == "FLAC"
        assert AudioFormat.RAW.value == "RAW"

    def test_speaker_identity(self) -> None:
        identity = SpeakerIdentity(
            speaker_id="spk_001",
            confidence=0.95,
            voice_print_hash="abc123",
            gender="male",
        )
        assert identity.speaker_id == "spk_001"
        assert identity.language == "en"  # default

    def test_speaker_identity_custom_language(self) -> None:
        identity = SpeakerIdentity(
            speaker_id="spk_002",
            confidence=0.8,
            voice_print_hash="def456",
            gender="female",
            language="fr",
        )
        assert identity.language == "fr"

    def test_transcription_result(self) -> None:
        result = TranscriptionResult(
            text="hello world",
            confidence=0.9,
            language="en",
            speaker_id="spk_001",
            words=(("hello", 0.0, 300.0), ("world", 300.0, 600.0)),
        )
        assert result.is_final is True
        assert len(result.words) == 2

    def test_transcription_result_interim(self) -> None:
        result = TranscriptionResult(
            text="partial",
            confidence=0.5,
            language="en",
            speaker_id=None,
            words=(),
            is_final=False,
        )
        assert result.is_final is False

    def test_emotion_result(self) -> None:
        er = EmotionResult(
            primary_emotion="happy",
            confidence=0.8,
            secondary_emotions=(("excited", 0.6),),
            arousal=0.7,
            valence=0.8,
        )
        assert er.primary_emotion == "happy"
        assert 0.0 <= er.arousal <= 1.0
        assert 0.0 <= er.valence <= 1.0

    def test_synthesis_options_defaults(self) -> None:
        opts = SynthesisOptions()
        assert opts.voice_id == "default"
        assert opts.speed == 1.0
        assert opts.pitch == 1.0
        assert opts.emotion == "neutral"
        assert opts.format == "WAV"
        assert opts.sample_rate == 24000

    def test_synthesis_options_custom(self) -> None:
        opts = SynthesisOptions(
            voice_id="custom_voice",
            speed=1.5,
            pitch=0.8,
            emotion="happy",
            sample_rate=48000,
        )
        assert opts.voice_id == "custom_voice"
        assert opts.sample_rate == 48000

    def test_speech_config_defaults(self) -> None:
        cfg = SpeechConfig()
        assert cfg.stt_enabled is True
        assert cfg.tts_enabled is True
        assert cfg.speaker_id_enabled is True
        assert cfg.emotion_detection_enabled is True
        assert cfg.default_language == "en"
        assert cfg.default_voice == "default"
        assert cfg.max_audio_length_seconds == 300.0

    def test_speech_config_custom(self) -> None:
        cfg = SpeechConfig(
            stt_enabled=False,
            default_language="fr",
            max_audio_length_seconds=60.0,
        )
        assert cfg.stt_enabled is False
        assert cfg.default_language == "fr"
        assert cfg.max_audio_length_seconds == 60.0


# ---------------------------------------------------------------------------
# SpeechModule
# ---------------------------------------------------------------------------


class TestSpeechModuleInit:
    """Verify SpeechModule initialization."""

    def test_default_config(self, module: SpeechModule) -> None:
        assert module._config.stt_enabled is True
        stats = module.get_stats()
        assert all(v == 0 for v in stats.values())

    def test_custom_config(self) -> None:
        cfg = SpeechConfig(stt_enabled=False, tts_enabled=False)
        mod = SpeechModule(cfg)
        assert mod._config.stt_enabled is False
        assert mod._config.tts_enabled is False

    def test_disabled_speaker_id(self) -> None:
        cfg = SpeechConfig(speaker_id_enabled=False)
        mod = SpeechModule(cfg)
        identity = mod.identify_speaker(b"some audio data")
        assert identity.speaker_id == "unknown"


class TestTranscribe:
    """Verify transcribe method."""

    def test_transcribe_wav(self, module: SpeechModule, wav_data: bytes) -> None:
        result = module.transcribe(wav_data, format="WAV")
        assert isinstance(result, TranscriptionResult)
        assert result.language == "en"
        assert result.is_final is True
        assert "[Stub:" in result.text

    def test_transcribe_empty(self, module: SpeechModule) -> None:
        result = module.transcribe(b"", format="WAV")
        assert result.confidence == 0.0
        assert result.text != ""

    def test_transcribe_non_wav(self, module: SpeechModule) -> None:
        result = module.transcribe(b"not a wav file", format="MP3")
        assert result.confidence == 0.0

    def test_transcribe_custom_language(
        self, module: SpeechModule, wav_data: bytes
    ) -> None:
        result = module.transcribe(wav_data, language="fr")
        assert result.language == "fr"

    def test_transcribe_stt_disabled(self) -> None:
        cfg = SpeechConfig(stt_enabled=False)
        mod = SpeechModule(cfg)
        result = mod.transcribe(b"some audio", format="WAV")
        assert result.text == ""
        assert result.confidence == 0.0


class TestSynthesize:
    """Verify synthesize method."""

    def test_synthesize_produces_wav_bytes(self, module: SpeechModule) -> None:
        audio = module.synthesize("Hello, world!")
        assert isinstance(audio, bytes)
        assert len(audio) > 44  # header + payload
        assert audio[:4] == b"RIFF"
        assert audio[8:12] == b"WAVE"

    def test_synthesize_with_options(self, module: SpeechModule) -> None:
        opts = SynthesisOptions(sample_rate=48000, speed=1.5)
        audio = module.synthesize("Test", options=opts)
        assert audio[:4] == b"RIFF"
        # Verify sample rate from header (offset 24, 4 bytes little-endian)
        sample_rate = struct.unpack("<I", audio[24:28])[0]
        assert sample_rate == 48000

    def test_synthesize_empty_text(self, module: SpeechModule) -> None:
        audio = module.synthesize("")
        assert len(audio) > 44

    def test_synthesize_tts_disabled(self) -> None:
        cfg = SpeechConfig(tts_enabled=False)
        mod = SpeechModule(cfg)
        audio = mod.synthesize("Hello")
        assert audio == b""


class TestIdentifySpeaker:
    """Verify identify_speaker method."""

    def test_identify_speaker_consistency(self, module: SpeechModule) -> None:
        audio = b"some consistent audio bytes for testing"
        id1 = module.identify_speaker(audio)
        id2 = module.identify_speaker(audio)
        assert id1.speaker_id == id2.speaker_id
        assert id1.voice_print_hash == id2.voice_print_hash

    def test_different_audio_different_speaker(self, module: SpeechModule) -> None:
        id1 = module.identify_speaker(b"audio clip one")
        id2 = module.identify_speaker(b"audio clip two")
        assert id1.speaker_id != id2.speaker_id

    def test_empty_audio(self, module: SpeechModule) -> None:
        identity = module.identify_speaker(b"")
        assert identity.confidence == 0.0

    def test_identify_wav(self, module: SpeechModule, wav_data: bytes) -> None:
        identity = module.identify_speaker(wav_data)
        assert isinstance(identity, SpeakerIdentity)
        assert len(identity.voice_print_hash) == 64  # SHA-256 hex


class TestDetectEmotion:
    """Verify detect_emotion method."""

    def test_detect_emotion_result_type(
        self, module: SpeechModule, wav_data: bytes
    ) -> None:
        result = module.detect_emotion(wav_data)
        assert isinstance(result, EmotionResult)
        assert 0.0 <= result.arousal <= 1.0
        assert 0.0 <= result.valence <= 1.0
        assert result.primary_emotion in [e.value for e in Emotion]

    def test_detect_emotion_empty(self, module: SpeechModule) -> None:
        result = module.detect_emotion(b"")
        assert result.primary_emotion == Emotion.NEUTRAL.value
        assert result.confidence == 0.0

    def test_detect_emotion_disabled(self) -> None:
        cfg = SpeechConfig(emotion_detection_enabled=False)
        mod = SpeechModule(cfg)
        result = mod.detect_emotion(b"some audio")
        assert result.primary_emotion == Emotion.NEUTRAL.value

    def test_high_amplitude_audio(self, module: SpeechModule) -> None:
        """High amplitude should map to higher arousal."""
        # Build WAV with large amplitude samples
        audio = _build_sine_wav_bytes(amplitude=30000, duration_ms=200)
        result = module.detect_emotion(audio)
        assert result.arousal > 0.1

    def test_silence_audio(self, module: SpeechModule) -> None:
        """Silence should map to low arousal."""
        sample_rate = 16000
        duration_ms = 200
        num_samples = sample_rate * duration_ms // 1000
        data_size = num_samples * 2
        riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
        fmt_body = struct.pack(
            "<I HHIIHH",
            16, 1, 1, sample_rate,
            sample_rate * 2, 2, 16,
        )
        fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
        data_chunk = struct.pack("<4sI", b"data", data_size) + b"\x00" * data_size
        silence_wav = riff + fmt_chunk + data_chunk

        result = module.detect_emotion(silence_wav)
        assert result.arousal < 0.1


class TestTranscribeStreaming:
    """Verify transcribe_streaming method."""

    def test_streaming_multiple_chunks(
        self, module: SpeechModule, wav_data: bytes
    ) -> None:
        chunks = [wav_data, wav_data, wav_data]
        results = module.transcribe_streaming(chunks)
        assert len(results) == 3
        assert results[0].is_final is False
        assert results[1].is_final is False
        assert results[2].is_final is True

    def test_streaming_empty(self, module: SpeechModule) -> None:
        results = module.transcribe_streaming([])
        assert results == []

    def test_streaming_single_chunk(
        self, module: SpeechModule, wav_data: bytes
    ) -> None:
        results = module.transcribe_streaming([wav_data])
        assert len(results) == 1
        assert results[0].is_final is True


class TestGetStats:
    """Verify get_stats method."""

    def test_initial_stats(self, module: SpeechModule) -> None:
        stats = module.get_stats()
        assert stats["total_transcriptions"] == 0
        assert stats["total_synthesis"] == 0
        assert stats["total_speaker_ids"] == 0
        assert stats["total_emotion_detections"] == 0

    def test_stats_after_operations(
        self, module: SpeechModule, wav_data: bytes
    ) -> None:
        module.transcribe(wav_data)
        module.synthesize("hello")
        module.identify_speaker(wav_data)
        module.detect_emotion(wav_data)

        stats = module.get_stats()
        assert stats["total_transcriptions"] == 1
        assert stats["total_synthesis"] == 1
        assert stats["total_speaker_ids"] == 1
        assert stats["total_emotion_detections"] == 1

    def test_stats_accumulate(
        self, module: SpeechModule, wav_data: bytes
    ) -> None:
        for _ in range(5):
            module.transcribe(wav_data, format="WAV")
        assert module.get_stats()["total_transcriptions"] == 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_sine_wav_bytes(
    amplitude: int = 8000,
    duration_ms: int = 200,
    sample_rate: int = 16000,
) -> bytes:
    """Build a WAV file with a simple square-like wave at given amplitude."""
    channels = 1
    bits_per_sample = 16
    num_samples = sample_rate * duration_ms // 1000

    block_align = channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    data_size = num_samples * block_align

    pcm_data = b""
    for n in range(num_samples):
        t = n / sample_rate
        sample = int(amplitude * (2**0.5) * (t * 440 % 1 - 0.5) * 2)
        sample = max(-32768, min(32767, sample))
        pcm_data += struct.pack("<h", sample)

    riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
    fmt_body = struct.pack(
        "<HHIIHH",
        1, channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
    )
    fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
    data_chunk = struct.pack("<4sI", b"data", data_size) + pcm_data

    return riff + fmt_chunk + data_chunk
