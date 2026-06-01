"""Targeted tests for uncovered lines in lyra-speech internals.

Covers lines that previous tests missed:
- _parse_wav_header: unknown chunks loop increment (lines 299-300)
- _extract_pcm_samples: second sanity check on WAV structure (line 322)
- _extract_pcm_samples: 16-bit truncated data boundary check (line 345)
- _extract_pcm_samples: fallback for non-8/16 bit (lines 354-357)
- identify_speaker: NEUTRAL gender path (line 590)
"""
from __future__ import annotations

import struct

import pytest

from lyra_speech import (
    Emotion,
    SpeechModule,
    VoiceGender,
    _build_wav_bytes,
    _extract_pcm_samples,
    _parse_wav_header,
)


# ═══════════════════════════════════════════════════════════════════════════
# _parse_wav_header: unknown chunk loop end (lines 299-300)
# ═══════════════════════════════════════════════════════════════════════════


class TestParseWavHeaderUnknownChunks:
    def test_multiple_unknown_chunks_before_fmt(self):
        """Multiple unknown chunks before fmt should still find fmt."""
        sample_rate = 16000
        channels = 1
        bits = 16
        num_samples = 160
        block_align = channels * (bits // 8)
        byte_rate = sample_rate * block_align
        data_size = num_samples * block_align

        riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
        # Insert 3 junk chunks before fmt
        chunks = b""
        for _ in range(3):
            chunks += struct.pack("<4sI", b"JUNK", 4) + b"\x00" * 4

        fmt_body = struct.pack(
            "<HHIIHH", 1, channels, sample_rate, byte_rate, block_align, bits
        )
        fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body

        data_chunk = struct.pack("<4sI", b"data", data_size) + b"\x00" * data_size
        wav = riff + chunks + fmt_chunk + data_chunk

        h = _parse_wav_header(wav)
        assert h["sample_rate"] == 16000
        assert h["channels"] == 1

    def test_no_fmt_chunk_returns_empty(self):
        """A WAV with no fmt chunk returns empty dict (line 300)."""
        riff = b"RIFF" + struct.pack("<I", 100) + b"WAVE"
        junk = struct.pack("<4sI", b"JUNK", 4) + b"\x00" * 4
        data_chunk = struct.pack("<4sI", b"data", 20) + b"\x00" * 20
        wav = riff + junk + data_chunk
        h = _parse_wav_header(wav)
        assert h == {}


# ═══════════════════════════════════════════════════════════════════════════
# _extract_pcm_samples: WAV structure sanity check (line 322)
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractPcmSamplesStructureCheck:
    """The redundant header check in _extract_pcm_samples (leftover from refactoring?)."""

    def test_partial_wav_returns_empty(self):
        """A WAV with valid header but truncated RIFF structure returns empty."""
        # Build a valid WAV then truncate to remove 'data' chunk
        wav = _build_wav_bytes(sample_rate=16000, channels=1, duration_ms=50)

        # Overwrite the RIFF descriptor so the _extract_pcm_samples
        # redundancy check fails: make it look like a non-RIFF stream
        bad_wav = b"RIFF" + struct.pack("<I", 36) + b"NOTW" + wav[12:]
        # header parses successfully but second check fails
        samples = _extract_pcm_samples(bad_wav)
        assert samples == []


# ═══════════════════════════════════════════════════════════════════════════
# _extract_pcm_samples: truncated 16-bit data (line 345)
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractPcmSamplesTruncated:
    def test_truncated_last_sample_skipped(self):
        """If the last sample is only 1 byte, it should be skipped."""
        sample_rate = 16000
        channels = 1
        bits = 16
        num_samples = 10
        block_align = channels * (bits // 8)
        byte_rate = sample_rate * block_align
        data_size = num_samples * block_align

        # Build PCM with one incomplete sample at the end
        pcm = b""
        for n in range(num_samples):
            pcm += struct.pack("<h", 1000)
        # Add one extra byte to make it odd-length
        pcm += b"\x01"  # one extra byte

        riff = struct.pack("<4sI4s", b"RIFF", 36 + len(pcm), b"WAVE")
        fmt_body = struct.pack("<HHIIHH", 1, channels, sample_rate, byte_rate, block_align, bits)
        fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
        data_chunk = struct.pack("<4sI", b"data", len(pcm)) + pcm
        wav = riff + fmt_chunk + data_chunk

        samples = _extract_pcm_samples(wav)
        # Should have 10 samples (the extra odd byte is ignored)
        assert len(samples) == num_samples
        assert all(s == 1000 for s in samples)

    def test_truncated_data_chunk_handled(self):
        """Data chunk with odd byte count should not crash."""
        wav = _build_wav_bytes(sample_rate=16000, channels=1, duration_ms=100)
        # Truncate one byte from the end of the data chunk
        pos = wav.find(b"data")
        if pos >= 0:
            wav = wav[:pos + 8 + 7999]  # truncate data
        samples = _extract_pcm_samples(wav)
        # Should return what it can without crashing
        assert isinstance(samples, list)


# ═══════════════════════════════════════════════════════════════════════════
# _extract_pcm_samples: fallback for non-8/16 bit (lines 354-357)
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractPcmSamplesFallback:
    def test_24bit_fallback_to_16bit_read(self):
        """24-bit audio should fall through to the 16-bit fallback path."""
        sample_rate = 16000
        channels = 1
        bits = 24
        num_samples = 10
        block_align = channels * ((bits + 7) // 8)  # 3 bytes per sample
        byte_rate = sample_rate * block_align
        data_size = num_samples * block_align

        # 24-bit PCM samples (little-endian)
        pcm = b""
        for n in range(num_samples):
            val = 1000
            pcm += struct.pack("<i", val)[:3]  # 3 bytes per 24-bit sample

        riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
        fmt_body = struct.pack("<HHIIHH", 1, channels, sample_rate, byte_rate, block_align, bits)
        fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
        data_chunk = struct.pack("<4sI", b"data", data_size) + pcm
        wav = riff + fmt_chunk + data_chunk

        samples = _extract_pcm_samples(wav)
        # Fallback reads 2 bytes at a time from 3-byte samples
        assert len(samples) > 0

    def test_32bit_float_fallback(self):
        """32-bit float WAV should not crash the fallback parser."""
        sample_rate = 48000
        channels = 2
        bits = 32
        num_samples = 10
        block_align = channels * (bits // 8)  # 8 bytes per frame
        byte_rate = sample_rate * block_align
        data_size = num_samples * block_align

        pcm = struct.pack("<10f", *[0.5, -0.3, 0.8, -0.1, 0.0, 0.2, -0.7, 0.9, -0.4, 0.6])

        riff = struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE")
        fmt_body = struct.pack("<HHIIHH", 3, channels, sample_rate, byte_rate, block_align, bits)
        fmt_chunk = struct.pack("<4sI", b"fmt ", 16) + fmt_body
        data_chunk = struct.pack("<4sI", b"data", data_size) + pcm
        wav = riff + fmt_chunk + data_chunk

        samples = _extract_pcm_samples(wav)
        assert len(samples) > 0


# ═══════════════════════════════════════════════════════════════════════════
# identify_speaker: NEUTRAL gender (line 590)
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentifySpeakerGenderEdgeCases:
    """Exercise all three gender branches in identify_speaker."""

    @pytest.fixture
    def module(self):
        return SpeechModule()

    def test_male_gender_first_byte_below_85(self, module):
        identity = module.identify_speaker(b"\x00" * 100)
        assert identity.gender == VoiceGender.MALE.value

    def test_female_gender_first_byte_85_to_169(self, module):
        # Build audio where first byte is in [85, 170)
        identity = module.identify_speaker(b"\x90" * 100)
        assert identity.gender == VoiceGender.FEMALE.value

    def test_neutral_gender_first_byte_170_plus(self, module):
        # Build audio where first byte >= 170
        identity = module.identify_speaker(b"\xaa" * 100)
        assert identity.gender == VoiceGender.NEUTRAL.value  # 170 >= 170

    def test_consistent_speaker_id(self, module):
        id1 = module.identify_speaker(b"\xaa" * 100)
        id2 = module.identify_speaker(b"\xaa" * 100)
        assert id1.speaker_id == id2.speaker_id
        assert id1.gender == id2.gender
