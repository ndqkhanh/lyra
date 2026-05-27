"""Tests for generate_sounds — WAV tone/chirp/envelope generation."""

import tempfile
from pathlib import Path

from lyra_cli.generate_sounds import (
    SAMPLE_RATE,
    _chirp,
    _envelope,
    _tone,
    _write_wav,
    generate_all_sounds,
)


class TestTone:
    def test_tone_length(self):
        samples = _tone(440, 0.1, 0.5)
        assert len(samples) == int(SAMPLE_RATE * 0.1)

    def test_tone_zero_duration(self):
        samples = _tone(440, 0.0, 0.5)
        assert len(samples) == 0

    def test_tone_amplitude_bounded(self):
        samples = _tone(440, 0.1, 1.0)
        for s in samples:
            assert -32767 <= s <= 32767

    def test_tone_volume_attenuates(self):
        loud = _tone(440, 0.05, 1.0)
        quiet = _tone(440, 0.05, 0.1)
        assert max(abs(s) for s in loud) > max(abs(s) for s in quiet)


class TestChirp:
    def test_chirp_length(self):
        samples = _chirp(200, 1200, 0.3, 0.3)
        assert len(samples) == int(SAMPLE_RATE * 0.3)

    def test_chirp_different_frequencies(self):
        low = _chirp(100, 200, 0.1, 0.5)
        high = _chirp(1000, 2000, 0.1, 0.5)
        assert len(low) == len(high)

    def test_chirp_amplitude_bounded(self):
        samples = _chirp(100, 5000, 0.2, 1.0)
        for s in samples:
            assert -32767 <= s <= 32767


class TestEnvelope:
    def test_envelope_length_preserved(self):
        samples = _tone(440, 0.2, 0.8)
        env = _envelope(samples)
        assert len(env) == len(samples)

    def test_envelope_attack_fades_in(self):
        samples = _tone(440, 0.3, 0.8)
        env = _envelope(samples, attack=0.1, decay=0.1)
        mid = len(samples) // 4
        assert abs(env[mid]) < abs(samples[mid])

    def test_envelope_no_overflow(self):
        samples = _tone(440, 0.2, 1.0)
        env = _envelope(samples)
        for s in env:
            assert -32767 <= s <= 32767


class TestWriteWav:
    def test_writes_valid_wav(self):
        samples = _tone(440, 0.05, 0.5)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.wav"
            _write_wav(path, samples)
            assert path.exists()
            assert path.stat().st_size > 44

    def test_wav_is_readable(self):
        import wave

        samples = _tone(880, 0.05, 0.3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "readable.wav"
            _write_wav(path, samples)
            with wave.open(str(path), "r") as wf:
                assert wf.getnchannels() == 1
                assert wf.getsampwidth() == 2
                assert wf.getframerate() == SAMPLE_RATE

    def test_empty_samples_produces_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.wav"
            _write_wav(path, [])
            assert path.exists()


class TestGenerateAllSounds:
    def test_generates_all_packs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = generate_all_sounds(tmp)
            assert base.exists()

            retro = base / "retro"
            assert retro.is_dir()
            assert (retro / "start.wav").exists()
            assert (retro / "input.wav").exists()
            assert (retro / "stop.wav").exists()
            assert (retro / "error.wav").exists()
            assert (retro / "complete.wav").exists()

            minimal = base / "minimal"
            assert minimal.is_dir()
            assert (minimal / "start.wav").exists()
            assert (minimal / "stop.wav").exists()
            assert (minimal / "complete.wav").exists()

            scifi = base / "sci-fi"
            assert scifi.is_dir()
            assert (scifi / "start.wav").exists()
            assert (scifi / "success.wav").exists()
            assert (scifi / "failure.wav").exists()
            assert (scifi / "stop.wav").exists()
            assert (scifi / "compact.wav").exists()
            assert (scifi / "error.wav").exists()

    def test_wav_files_are_not_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = generate_all_sounds(tmp)
            for pack in ["retro", "minimal", "sci-fi"]:
                for wav in (base / pack).iterdir():
                    if wav.suffix == ".wav":
                        assert wav.stat().st_size > 44, f"{wav} is too small"
