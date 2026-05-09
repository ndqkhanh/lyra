"""Wave-E Task 11a: speech-to-text pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable


__all__ = ["STTBackend", "STTError", "transcribe_audio"]


class STTError(Exception):
    pass


@runtime_checkable
class STTBackend(Protocol):
    """Tiny surface every STT backend implements."""

    name: str

    def transcribe(self, *, audio_path: Path) -> str: ...


def _validate_audio(path: Path) -> None:
    if not path.exists():
        raise STTError(f"audio not found: {path}")
    if path.suffix.lower() not in {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}:
        raise STTError(f"unsupported audio format: {path.suffix}")


def transcribe_audio(path: Path | str, *, backend: STTBackend) -> str:
    p = Path(path)
    _validate_audio(p)
    return backend.transcribe(audio_path=p)
