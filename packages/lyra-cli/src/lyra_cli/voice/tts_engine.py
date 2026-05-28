"""Text-to-Speech engine with multiple backend support.

Backends (priority order):
1. SystemSayBackend — macOS ``say`` command via subprocess (always available on macOS)
2. Pyttsx3Backend — offline TTS via ``pyttsx3`` if installed
3. EdgeTTSBackend — cloud TTS via ``edge-tts`` if installed

All backends fall back gracefully when dependencies are missing.
"""

from __future__ import annotations

import asyncio
import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = [
    "TTSConfig",
    "VoiceConfig",
    "TTSBackend",
    "SystemSayBackend",
    "Pyttsx3Backend",
    "EdgeTTSBackend",
    "TTSError",
    "get_tts_engine",
    "synthesize_speech",
]


class TTSError(Exception):
    """Raised when TTS synthesis fails."""


@dataclass(frozen=True)
class VoiceConfig:
    """Voice selection and speed configuration."""

    name: str = "default"
    speed: float = 1.0

    def __post_init__(self) -> None:
        if self.speed <= 0:
            object.__setattr__(self, "speed", 1.0)


@dataclass(frozen=True)
class TTSConfig:
    """Global TTS engine configuration."""

    backend: str = "auto"
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    output_dir: str | None = None


@runtime_checkable
class TTSBackend(Protocol):
    """Interface every TTS backend must satisfy."""

    name: str

    def synthesize(
        self,
        text: str,
        dest: Path,
        voice: VoiceConfig | None = None,
    ) -> Path: ...


class SystemSayBackend:
    """Uses the system ``say`` command (macOS) or ``espeak`` (Linux).

    This is the default fallback that requires no extra dependencies.
    """

    def __init__(self) -> None:
        self.name = "system-say"
        self._available = self._check_available()

    @staticmethod
    def _check_available() -> bool:
        system = platform.system()
        if system == "Darwin":
            return True  # say is built-in on macOS
        if system == "Linux":
            try:
                subprocess.run(
                    ["which", "espeak"],
                    capture_output=True,
                    check=False,
                )
                return True
            except OSError:
                return False
        return False

    @property
    def available(self) -> bool:
        return self._available

    def _build_command(
        self,
        text: str,
        dest: Path,
        voice: VoiceConfig | None,
    ) -> list[str]:
        system = platform.system()
        cmd: list[str] = []
        if system == "Darwin":
            cmd = ["say", "-o", str(dest)]
            if voice and voice.name != "default":
                cmd.extend(["-v", voice.name])
            if voice and voice.speed != 1.0:
                rate = max(50, int(175 * voice.speed))
                cmd.extend(["-r", str(rate)])
            cmd.append(text)
        elif system == "Linux":
            cmd = ["espeak", "-w", str(dest)]
            if voice and voice.speed != 1.0:
                speed = max(80, int(160 * voice.speed))
                cmd.extend(["-s", str(speed)])
            cmd.append(text)
        else:
            cmd = ["espeak", "-w", str(dest), text]
        return cmd

    def synthesize(
        self,
        text: str,
        dest: Path,
        voice: VoiceConfig | None = None,
    ) -> Path:
        if not text.strip():
            raise TTSError("Cannot synthesize empty text")
        cfg = voice or VoiceConfig()
        cmd = self._build_command(text, dest, cfg)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise TTSError(
                f"SystemSayBackend failed: {exc.stderr.decode().strip()}"
            ) from exc
        except FileNotFoundError as exc:
            raise TTSError(
                "SystemSayBackend: say/espeak command not found"
            ) from exc
        return dest


class Pyttsx3Backend:
    """Offline TTS via the ``pyttsx3`` library.

    Falls back gracefully if pyttsx3 is not installed.
    """

    def __init__(self) -> None:
        self.name = "pyttsx3"
        self._engine = None
        self._available = self._try_import()

    def _try_import(self) -> bool:
        try:
            import pyttsx3  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def available(self) -> bool:
        return self._available

    def _get_engine(self):
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
        return self._engine

    def synthesize(
        self,
        text: str,
        dest: Path,
        voice: VoiceConfig | None = None,
    ) -> Path:
        if not self._available:
            raise TTSError("pyttsx3 is not installed")
        if not text.strip():
            raise TTSError("Cannot synthesize empty text")

        import pyttsx3

        engine = self._get_engine()
        cfg = voice or VoiceConfig()

        engine.setProperty("rate", int(200 * cfg.speed))
        if cfg.name != "default":
            voices = engine.getProperty("voices")
            for v in voices:
                if cfg.name.lower() in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break

        dest.parent.mkdir(parents=True, exist_ok=True)
        engine.save_to_file(text, str(dest))
        engine.runAndWait()
        return dest


class EdgeTTSBackend:
    """Cloud-based TTS via ``edge-tts`` (Microsoft Edge TTS).

    Falls back gracefully if edge-tts is not installed.
    """

    def __init__(self) -> None:
        self.name = "edge-tts"
        self._available = self._try_import()

    @staticmethod
    def _try_import() -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def available(self) -> bool:
        return self._available

    def synthesize(
        self,
        text: str,
        dest: Path,
        voice: VoiceConfig | None = None,
    ) -> Path:
        if not self._available:
            raise TTSError("edge-tts is not installed")
        if not text.strip():
            raise TTSError("Cannot synthesize empty text")

        import edge_tts

        cfg = voice or VoiceConfig()
        voice_id = self._resolve_voice(cfg.name)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            asyncio.run(
                edge_tts.Communicate(text, voice=voice_id, rate=f"+{int((cfg.speed - 1) * 100)}%")
                .save(str(dest))
            )
        except Exception as exc:
            raise TTSError(f"EdgeTTSBackend failed: {exc}") from exc
        return dest

    @staticmethod
    def _resolve_voice(name: str) -> str:
        voices = {
            "default": "en-US-AriaNeural",
            "male": "en-US-GuyNeural",
            "female": "en-US-AriaNeural",
            "uk": "en-GB-SoniaNeural",
            "au": "en-AU-NatashaNeural",
        }
        return voices.get(name.lower(), name)


def get_tts_engine(preferred: str = "auto") -> TTSBackend:
    """Return the best available TTS backend.

    Priority: edge-tts > pyttsx3 > system-say.
    Pass a specific backend name (``system-say``, ``pyttsx3``, ``edge-tts``)
    to force a particular backend.
    """
    backends: dict[str, TTSBackend] = {
        "system-say": SystemSayBackend(),
        "pyttsx3": Pyttsx3Backend(),
        "edge-tts": EdgeTTSBackend(),
    }

    if preferred != "auto":
        backend = backends.get(preferred)
        if backend is None:
            raise TTSError(f"Unknown TTS backend: {preferred!r}")
        return backend

    for name in ("edge-tts", "pyttsx3", "system-say"):
        backend = backends[name]
        if getattr(backend, "available", True):
            return backend

    # Last resort — always available on macOS, may fail at runtime
    return backends["system-say"]


def synthesize_speech(
    text: str,
    *,
    dest: Path | str | None = None,
    voice: VoiceConfig | None = None,
    backend: TTSBackend | None = None,
    config: TTSConfig | None = None,
) -> Path:
    """Synthesize text to speech and return the output file path.

    Parameters
    ----------
    text : str
        Text to synthesize (must be non-empty).
    dest : Path | str | None
        Output file path. Auto-generated if not provided.
    voice : VoiceConfig | None
        Voice and speed configuration.
    backend : TTSBackend | None
        Specific TTS backend. Auto-detected if not provided.
    config : TTSConfig | None
        Full TTS engine configuration.

    Returns
    -------
    Path to the generated audio file.
    """
    if not text.strip():
        raise TTSError("synthesize_speech: text must be non-empty")

    engine = backend or get_tts_engine()
    resolved_voice = voice or (config.voice if config else None) or VoiceConfig()

    if dest is None:
        base = Path(config.output_dir) if (config and config.output_dir) else Path.cwd()
        dest = base / f"lyra_tts_{hash(text) & 0xFFFFFFFF:08x}.wav"

    out = Path(dest)
    return engine.synthesize(text=text, dest=out, voice=resolved_voice)
