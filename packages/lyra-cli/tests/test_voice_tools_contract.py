"""Wave-E Task 11: contract tests for the voice toolkit."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from lyra_cli.voice import (
    STTBackend,
    STTError,
    TTSBackend,
    TTSError,
    synthesise_speech,
    transcribe_audio,
)
from lyra_cli.interactive.session import InteractiveSession


# ---------------------------------------------------------------------------
# Stub backends
# ---------------------------------------------------------------------------


@dataclass
class _StubSTT:
    name: str = "stub-stt"
    last_path: Path | None = None
    response: str = "transcribed text"

    def transcribe(self, *, audio_path: Path) -> str:
        self.last_path = audio_path
        return self.response


@dataclass
class _StubTTS:
    name: str = "stub-tts"
    written: list[Path] = field(default_factory=list)

    def synthesise(self, *, text: str, dest: Path) -> Path:
        dest.write_bytes(b"FAKEAUDIO" + text.encode())
        self.written.append(dest)
        return dest


# ---------------------------------------------------------------------------
# STT
# ---------------------------------------------------------------------------


def test_transcribe_audio_calls_backend(tmp_path: Path) -> None:
    audio = tmp_path / "snippet.wav"
    audio.write_bytes(b"\x00")
    backend = _StubSTT(response="hello lyra")
    text = transcribe_audio(audio, backend=backend)
    assert text == "hello lyra"
    assert backend.last_path == audio


def test_transcribe_audio_rejects_missing(tmp_path: Path) -> None:
    backend = _StubSTT()
    with pytest.raises(STTError):
        transcribe_audio(tmp_path / "no.wav", backend=backend)


def test_transcribe_audio_rejects_unsupported_format(tmp_path: Path) -> None:
    audio = tmp_path / "x.txt"
    audio.write_text("nope")
    with pytest.raises(STTError):
        transcribe_audio(audio, backend=_StubSTT())


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------


def test_synthesise_speech_writes_file(tmp_path: Path) -> None:
    backend = _StubTTS()
    out = synthesise_speech("hello", dest=tmp_path / "out" / "hello.wav", backend=backend)
    assert out.exists()
    assert out.read_bytes().startswith(b"FAKEAUDIO")


def test_synthesise_speech_rejects_empty_text(tmp_path: Path) -> None:
    with pytest.raises(TTSError):
        synthesise_speech("", dest=tmp_path / "x.wav", backend=_StubTTS())


# ---------------------------------------------------------------------------
# /voice slash
# ---------------------------------------------------------------------------


def _session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="claude")


def test_slash_voice_status_default_is_off(tmp_path: Path) -> None:
    session = _session(tmp_path)
    result = session.dispatch("/voice")
    assert "off" in result.output


def test_slash_voice_on_then_off(tmp_path: Path) -> None:
    session = _session(tmp_path)
    on_res = session.dispatch("/voice on")
    assert session.voice_mode is True
    assert "on" in on_res.output

    off_res = session.dispatch("/voice off")
    assert session.voice_mode is False
    assert "off" in off_res.output
