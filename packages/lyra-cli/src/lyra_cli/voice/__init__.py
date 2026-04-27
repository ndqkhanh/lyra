"""Wave-E Task 11: voice substrate (STT + TTS + ``/voice`` toggle).

Both pipelines accept injectable backends so unit tests stay
network-free. The default ``faster-whisper`` (CPU) /
``openai-whisper`` (GPU) STT and ``pyttsx3`` (offline) /
``openai.audio.speech`` (cloud) TTS install via ``pip install
lyra[voice]``.
"""
from __future__ import annotations

from .stt import STTBackend, STTError, transcribe_audio
from .tts import TTSBackend, TTSError, synthesise_speech

__all__ = [
    "STTBackend",
    "STTError",
    "TTSBackend",
    "TTSError",
    "synthesise_speech",
    "transcribe_audio",
]
