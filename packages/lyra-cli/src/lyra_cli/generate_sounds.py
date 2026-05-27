"""Generate minimal WAV sound effects for built-in sound packs.

Produces short, distinct tones using only stdlib (wave + math).
Each sound is ~0.1-0.3s and <50 KB — unobtrusive notification cues.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22050
BITS_PER_SAMPLE = 16
MAX_AMPLITUDE = 32767


def _tone(freq: float, duration: float, volume: float = 0.5) -> list[int]:
    """Generate a pure sine tone."""
    n_samples = int(SAMPLE_RATE * duration)
    ampl = int(MAX_AMPLITUDE * volume)
    return [int(ampl * math.sin(2 * math.pi * freq * t / SAMPLE_RATE))
            for t in range(n_samples)]


def _chirp(f_start: float, f_end: float, duration: float, volume: float = 0.5) -> list[int]:
    """Frequency sweep from f_start to f_end."""
    n_samples = int(SAMPLE_RATE * duration)
    ampl = int(MAX_AMPLITUDE * volume)
    return [
        int(ampl * math.sin(2 * math.pi * (
            f_start + (f_end - f_start) * t / n_samples
        ) * t / SAMPLE_RATE))
        for t in range(n_samples)
    ]


def _envelope(samples: list[int], attack: float = 0.02, decay: float = 0.05) -> list[int]:
    """Apply ADSR-style attack/decay envelope."""
    n = len(samples)
    out = []
    for i, s in enumerate(samples):
        t = i / SAMPLE_RATE
        env = 1.0
        if t < attack:
            env = t / attack
        elif t > (n / SAMPLE_RATE) - decay:
            env = max(0, ((n / SAMPLE_RATE) - t) / decay)
        out.append(int(s * env))
    return out


def _write_wav(path: Path, samples: list[int]) -> None:
    """Write 16-bit mono PCM WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(BITS_PER_SAMPLE // 8)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(
            struct.pack("<h", max(-MAX_AMPLITUDE, min(MAX_AMPLITUDE - 1, s)))
            for s in samples
        ))


# ── Pack generators ───────────────────────────────────────────────────────────

def _gen_retro(base: Path) -> None:
    """8-bit retro game sounds — square-ish tones."""
    _write_wav(base / "retro" / "start.wav",
               _envelope(_chirp(440, 880, 0.2, 0.4)))
    _write_wav(base / "retro" / "input.wav",
               _envelope(_tone(660, 0.08, 0.3)))
    _write_wav(base / "retro" / "stop.wav",
               _envelope(_chirp(880, 220, 0.15, 0.4)))
    _write_wav(base / "retro" / "error.wav",
               _envelope(_tone(200, 0.2, 0.5)))
    _write_wav(base / "retro" / "complete.wav",
               _envelope(_chirp(523, 1047, 0.25, 0.4)))


def _gen_minimal(base: Path) -> None:
    """Subtle chimes — single soft tones."""
    _write_wav(base / "minimal" / "start.wav",
               _envelope(_tone(1047, 0.1, 0.2)))
    _write_wav(base / "minimal" / "stop.wav",
               _envelope(_tone(784, 0.12, 0.2)))
    _write_wav(base / "minimal" / "complete.wav",
               _envelope(_tone(1319, 0.15, 0.2)))


def _gen_scifi(base: Path) -> None:
    """Futuristic sci-fi effects."""
    _write_wav(base / "sci-fi" / "start.wav",
               _envelope(_chirp(200, 1200, 0.3, 0.3)))
    _write_wav(base / "sci-fi" / "success.wav",
               _envelope(_chirp(600, 1200, 0.15, 0.3)))
    _write_wav(base / "sci-fi" / "failure.wav",
               _envelope(_chirp(400, 100, 0.25, 0.4)))
    _write_wav(base / "sci-fi" / "stop.wav",
               _envelope(_chirp(1200, 300, 0.2, 0.3)))
    _write_wav(base / "sci-fi" / "compact.wav",
               _envelope(_tone(800, 0.1, 0.25)))
    _write_wav(base / "sci-fi" / "error.wav",
               _envelope(_chirp(300, 100, 0.3, 0.5)))


def generate_all_sounds(target_dir: str | Path | None = None) -> Path:
    """Generate all WAV files for the 3 built-in packs.

    Returns the base sounds directory.
    """
    if target_dir is None:
        target_dir = Path(__file__).parent / "sounds"
    base = Path(target_dir)

    _gen_retro(base)
    _gen_minimal(base)
    _gen_scifi(base)

    return base


__all__ = ["generate_all_sounds", "SAMPLE_RATE"]
