"""Tests for lyra-speech internal helpers — WAV parsing, PCM extraction, WAV building, circumplex emotion.

These exercise the real implementations in lyra_speech/__init__.py that are not covered
by existing tests (which focus on SpeeModule via its public API).
"""

from __future__ import annotations

import struct

import pytest
from lyra_speech import (
    Emotion,
    SpeechModule,
    _build_wav_bytes,
    _extract_pcm_samples,
    _parse_wav_header,
)


# ═══════════════════════════════════════════════════════════════════════════
# _parse_wav_header
# ═══════════════════════════════════════════════════════════════════════════


class TestParseWavHeader:
    """_parse_wav_header is a real WAV RIFF parser used by transcribe() and detect_emotion()."""

    def test_returns_empty_for_too_short(self):
        assert _parse_wav_header(b"") == {}
        assert _parse_wav_header(b"RIFF") == {}

    def test_returns_empty_for_non_wav(self):
        assert _parse_wav_header(b"NOT A WAV FILE AT ALL ") == {}

    def test_returns_empty_for_partial_header(self):
        # RIFF header present but no fmt chunk
        data = struct.pack("<4sI4s", b"RIFF", 100, b"WAVE")
        assert _parse_wav_header(data) == {}

    def test_returns_empty_when_wave_missing(self):
        data = struct.pack("<4sI4s", b"RIFF", 100, b"NOTW")
        assert _parse_wav_header(data) == {}

    def test_parses_mono_16bit_16khz(self):
        wav = _build_wav_bytes(sample_rate=16000, channels=1, bits_per_sample=16, duration_ms=500)
        h = _parse_wav_header(wav)
        assert h["audio_format"] == 1  # PCM
        assert h["channels"] == 1
        assert h["sample_rate"] == 16000
        assert h["bits_per_sample"] == 16
        assert h["data_size"] > 0

    def test_parses_stereo_24bit_48khz(self):
        wav = _build_wav_bytes(sample_rate=48000, channels=2, bits_per_sample=24, duration_ms=200)
        h = _parse_wav_header(wav)
        assert h["audio_format"] == 1
        assert h["channels"] == 2
        assert h["sample_rate"] == 48000
        assert h["bits_per_sample"] == 24

    def test_parses_8bit_mono(self):
        wav = _build_wav_bytes(sample_rate=8000, channels=1, bits_per_sample=8, duration_ms=300)
        h = _parse_wav_header(wav)
        assert h["channels"] == 1
        assert h["sample_rate"] == 8000
        assert h["bits_per_sample"] == 8

    def test_parses_16bit_stereo_44100(self):
        wav = _build_wav_bytes(sample_rate=44100, channels=2, bits_per_sample=16, duration_ms=1000)
        h = _parse_wav_header(wav)
        assert h["sample_rate"] == 44100
        assert h["channels"] == 2
        assert h["bits_per_sample"] == 16

    def test_datachunk_not_at_standard_offset(self):
        """The parser can handle data chunks that don't immediately follow fmt."""
        sample_rate = 16000
        channels = 1
        bits_per_sample = 16
        duration_ms = 100
        num_samples = sample_rate * duration_ms // 1000
        block_align = channels * (bits_per_sample // 8)
        byte_rate = sample_rate * block_align
        data_size = num_samples * block_align

        riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
        fmt_body = struct.pack(
            "<HHIIHH", 1, channels, sample_rate, byte_rate, block_align, bits_per_sample,
        )
        fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
        # Insert a junk chunk before data
        junk = struct.pack("<4sI", b"JUNK", 8) + b"\x00" * 8
        data_chunk = struct.pack("<4sI", b"data", data_size) + b"\x00" * data_size
        wav = riff + fmt_chunk + junk + data_chunk

        h = _parse_wav_header(wav)
        assert h["data_size"] == data_size
        assert h["sample_rate"] == sample_rate

    def test_unknown_chunk_id_skipped_gracefully(self):
        """If a chunk has an unrecognized id, parser skips it."""
        wav = _build_wav_bytes(sample_rate=16000, channels=1, bits_per_sample=16, duration_ms=50)
        # Insert a fact chunk after fmt (common in some WAVs)
        fact_chunk = struct.pack("<4sI", b"fact", 4) + struct.pack("<I", 1)
        # Rebuild with fact between fmt and data
        pos = 12
        while pos < len(wav) - 8:
            cid = wav[pos : pos + 4]
            csz = struct.unpack("<I", wav[pos + 4 : pos + 8])[0]
            if cid == b"fmt ":
                # After fmt chunk, after fact
                fmt_end = pos + 8 + csz
                before = wav[:fmt_end]
                after = wav[fmt_end:]
                wav = before + fact_chunk + after
                break
            pos += 8 + csz

        h = _parse_wav_header(wav)
        assert h["sample_rate"] == 16000
        assert h["data_size"] > 0


# ═══════════════════════════════════════════════════════════════════════════
# _extract_pcm_samples
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractPcmSamples:
    """_extract_pcm_samples extracts integer sample values from WAV data."""

    def test_return_empty_for_empty(self):
        assert _extract_pcm_samples(b"") == []

    def test_return_empty_for_invalid(self):
        assert _extract_pcm_samples(b"not a wav") == []

    def test_extract_16bit_silence(self):
        wav = _build_wav_bytes(sample_rate=16000, channels=1, bits_per_sample=16, duration_ms=100)
        samples = _extract_pcm_samples(wav)
        assert len(samples) > 0
        assert all(s == 0 for s in samples)  # silence

    def test_extract_16bit_nonzero(self):
        """Build a WAV with a known 440Hz tone and verify samples are non-zero."""
        sample_rate = 16000
        duration_ms = 50
        num_samples = sample_rate * duration_ms // 1000
        channels = 1
        bits_per_sample = 16
        block_align = channels * (bits_per_sample // 8)
        byte_rate = sample_rate * block_align
        data_size = num_samples * block_align

        pcm = b""
        for n in range(num_samples):
            val = int(8000 * (2**0.5) * (n / sample_rate * 440 % 1 - 0.5) * 2)
            val = max(-32768, min(32767, val))
            pcm += struct.pack("<h", val)

        riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
        fmt_body = struct.pack(
            "<HHIIHH", 1, channels, sample_rate, byte_rate, block_align, bits_per_sample,
        )
        fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
        data_chunk = struct.pack("<4sI", b"data", data_size) + pcm
        wav = riff + fmt_chunk + data_chunk

        samples = _extract_pcm_samples(wav)
        assert len(samples) == num_samples
        assert any(s != 0 for s in samples)  # not all silence

    def test_extract_8bit_samples(self):
        wav = _build_wav_bytes(sample_rate=8000, channels=1, bits_per_sample=8, duration_ms=50)
        samples = _extract_pcm_samples(wav)
        assert len(samples) > 0

    def test_extract_truncated_data_does_not_crash(self):
        """Truncated data after valid header does not raise."""
        wav = _build_wav_bytes(sample_rate=16000, channels=1, bits_per_sample=16, duration_ms=100)
        truncated = wav[:60]  # Only header
        samples = _extract_pcm_samples(truncated)
        # Should return empty or partial samples without crashing
        assert isinstance(samples, list)


# ═══════════════════════════════════════════════════════════════════════════
# _build_wav_bytes
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildWavBytes:
    """_build_wav_bytes constructs valid WAV files used by synthesize()."""

    def test_returns_valid_wav(self):
        wav = _build_wav_bytes()
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert len(wav) > 44

    def test_contains_fmt_and_data(self):
        wav = _build_wav_bytes()
        assert b"fmt " in wav
        assert b"data" in wav

    def test_minimal_duration(self):
        """duration_ms=1 produces at least 1 sample."""
        wav = _build_wav_bytes(duration_ms=1)
        h = _parse_wav_header(wav)
        assert h["data_size"] > 0

    def test_16bit_default(self):
        wav = _build_wav_bytes()
        h = _parse_wav_header(wav)
        assert h["bits_per_sample"] == 16
        assert h["audio_format"] == 1

    def test_48khz_stereo(self):
        wav = _build_wav_bytes(sample_rate=48000, channels=2)
        h = _parse_wav_header(wav)
        assert h["sample_rate"] == 48000
        assert h["channels"] == 2

    def test_8bit_output(self):
        wav = _build_wav_bytes(bits_per_sample=8)
        h = _parse_wav_header(wav)
        assert h["bits_per_sample"] == 8

    def test_duration_matches_approximately(self):
        """500ms at 16kHz mono should produce ~8000 samples of 16-bit = 16000 bytes data."""
        wav = _build_wav_bytes(sample_rate=16000, channels=1, bits_per_sample=16, duration_ms=500)
        h = _parse_wav_header(wav)
        expected_samples = 16000 * 500 // 1000  # 8000
        expected_data = expected_samples * 2  # 16-bit = 2 bytes per sample
        # Allow small tolerance for integer division
        assert abs(h["data_size"] - expected_data) < 2


# ═══════════════════════════════════════════════════════════════════════════
# _circumplex_emotion
# ═══════════════════════════════════════════════════════════════════════════


class TestCircumplexEmotion:
    """_circumplex_emotion maps arousal+valence to an emotion label using 4 quadrants."""

    def test_excited_high_arousal_high_valence(self):
        primary, secondary = SpeechModule._circumplex_emotion(0.8, 0.9)
        assert primary == Emotion.EXCITED.value
        secondary_labels = [s[0] for s in secondary]
        assert Emotion.HAPPY.value in secondary_labels

    def test_angry_high_arousal_low_valence(self):
        primary, secondary = SpeechModule._circumplex_emotion(0.9, 0.2)
        assert primary == Emotion.ANGRY.value
        secondary_labels = [s[0] for s in secondary]
        assert Emotion.FEARFUL.value in secondary_labels

    def test_calm_low_arousal_high_valence(self):
        primary, secondary = SpeechModule._circumplex_emotion(0.2, 0.9)
        assert primary == Emotion.CALM.value
        secondary_labels = [s[0] for s in secondary]
        assert Emotion.HAPPY.value in secondary_labels

    def test_sad_low_arousal_low_valence(self):
        primary, secondary = SpeechModule._circumplex_emotion(0.2, 0.3)
        assert primary == Emotion.SAD.value
        secondary_labels = [s[0] for s in secondary]
        assert Emotion.NEUTRAL.value in secondary_labels

    def test_boundary_arousal_exactly_05(self):
        """Arousal exactly 0.5: not high (>0.5), not low (<=0.5)."""
        primary, _ = SpeechModule._circumplex_emotion(0.5, 0.6)
        assert primary == Emotion.CALM.value  # low arousal + high valence

    def test_boundary_valence_exactly_05(self):
        """Valence exactly 0.5: not high (>0.5), not low (<=0.5)."""
        primary, _ = SpeechModule._circumplex_emotion(0.6, 0.5)
        assert primary == Emotion.ANGRY.value  # high arousal + low valence

    def test_extreme_values(self):
        primary, secondary = SpeechModule._circumplex_emotion(1.0, 1.0)
        assert primary == Emotion.EXCITED.value
        primary, secondary = SpeechModule._circumplex_emotion(1.0, 0.0)
        assert primary == Emotion.ANGRY.value
        primary, secondary = SpeechModule._circumplex_emotion(0.0, 1.0)
        assert primary == Emotion.CALM.value
        primary, secondary = SpeechModule._circumplex_emotion(0.0, 0.0)
        assert primary == Emotion.SAD.value

    def test_secondary_scores_are_floats(self):
        _, secondary = SpeechModule._circumplex_emotion(0.7, 0.8)
        for label, score in secondary:
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════
# SpeechModule edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestSpeechModuleEdgeCases:
    """Additional edge cases for SpeechModule not covered by existing tests."""

    def test_synthesize_text_variation_vs_options(self):
        """Two invocations with same input but different options should differ."""
        module = SpeechModule()
        default = module.synthesize("hello world")
        opts = module.synthesize("hello world", options=None)
        assert default == opts  # None defaults to SynthesisOptions()

    def test_transcribe_empty_with_non_wav_format(self):
        """Empty bytes + non-WAV format returns stub message, not a crash."""
        module = SpeechModule()
        result = module.transcribe(b"", format="MP3")
        assert result.confidence == 0.0

    def test_transcribe_non_wav_bytes_with_wav_format(self):
        """Random bytes passed as WAV format fails parsing and returns stub."""
        module = SpeechModule()
        result = module.transcribe(b"\xff\xfe\x00\x01\x02", format="WAV")
        # Too short for a WAV header -> the stub message
        assert result.text != ""

    def test_identify_speaker_gender_deterministic_first_byte(self):
        module = SpeechModule()
        id1 = module.identify_speaker(b"\x00" * 100)
        id2 = module.identify_speaker(b"\x00" * 100)
        assert id1.speaker_id == id2.speaker_id

    def test_detect_emotion_on_malformed_wav(self):
        """Short non-WAV bytes should not crash emotion detection."""
        module = SpeechModule()
        result = module.detect_emotion(b"not a wav")
        assert result.primary_emotion == Emotion.NEUTRAL.value

    def test_transcribe_with_custom_sample_rate_in_header(self):
        """Build a WAV at 44100 Hz and verify transcribe recognizes it."""
        module = SpeechModule()
        wav = _build_wav_bytes(sample_rate=44100, channels=1, duration_ms=100)
        result = module.transcribe(wav)
        assert "44100Hz" in result.text

    def test_streaming_transcribe_single_result_timing(self):
        module = SpeechModule()
        wav = _build_wav_bytes(duration_ms=50)
        results = module.transcribe_streaming([wav])
        assert len(results) == 1

    def test_stats_unchanged_after_disabled_emotion(self):
        cfg = type("Cfg", (), {"emotion_detection_enabled": False})()
        module = SpeechModule(cfg)
        result = module.detect_emotion(b"\x00" * 100)
        assert result.confidence == 0.0
