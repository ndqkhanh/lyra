"""Wave-E Task 11b: text-to-speech pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable


__all__ = ["TTSBackend", "TTSError", "synthesise_speech"]


class TTSError(Exception):
    pass


@runtime_checkable
class TTSBackend(Protocol):
    """Tiny surface every TTS backend implements."""

    name: str

    def synthesise(self, *, text: str, dest: Path) -> Path: ...


def synthesise_speech(text: str, *, dest: Path | str, backend: TTSBackend) -> Path:
    if not text:
        raise TTSError("synthesise_speech: text must be non-empty")
    out = Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    return backend.synthesise(text=text, dest=out)
