"""
Sound Effects System — optional hook-based audio cues for lifecycle events.

Plays OS-native audio on SessionStart, UserPromptSubmit, Stop, PreCompact,
and other lifecycle events. Ships with curated sound packs users can cycle
through via ``/sound <pack>``. Default: off (opt-in).

Source: Deep Research — UI/UX & Voice Repos (alexop.dev, War3 voice article).
"""

from __future__ import annotations

import os
import platform
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SoundEvent(str, Enum):
    """Lifecycle events that can trigger sounds."""

    SESSION_START = "session_start"
    USER_PROMPT = "user_prompt"
    TOOL_START = "tool_start"
    TOOL_SUCCESS = "tool_success"
    TOOL_FAILURE = "tool_failure"
    STOP = "stop"
    PRE_COMPACT = "pre_compact"
    ERROR = "error"
    TASK_COMPLETE = "task_complete"
    AGENT_SPAWN = "agent_spawn"
    COST_WARNING = "cost_warning"


@dataclass
class SoundPack:
    """A curated set of sound effects for lifecycle events."""

    name: str
    description: str
    sounds: dict[SoundEvent, str] = field(default_factory=dict)

    def get(self, event: SoundEvent) -> str | None:
        return self.sounds.get(event)


class AudioPlayer:
    """Cross-platform audio player using OS-native commands."""

    _player: str
    _available: bool

    def __init__(self) -> None:
        self._player = self._detect_player()
        self._available = self._player != ""

    @staticmethod
    def _detect_player() -> str:
        system = platform.system()
        if system == "Darwin":
            return "afplay"
        elif system == "Linux":
            for cmd in ("paplay", "aplay", "mpg123"):
                if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                    return cmd
            return ""
        elif system == "Windows":
            return "powershell -c (New-Object Media.SoundPlayer"
        return ""

    @property
    def available(self) -> bool:
        return self._available

    def play(self, path: str) -> None:
        """Play a sound file. Non-blocking (backgrounded)."""
        if not self._available:
            return
        try:
            cmd = [self._player, path]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except Exception:
            pass


class SoundManager:
    """Manages sound packs and dispatch on lifecycle events.

    Usage::

        sm = SoundManager()
        sm.load_pack("retro")
        sm.enable()
        sm.dispatch(SoundEvent.SESSION_START)
    """

    def __init__(self) -> None:
        self._player = AudioPlayer()
        self._enabled: bool = False
        self._active_pack: SoundPack | None = None
        self._packs: dict[str, SoundPack] = {}
        self._event_hooks: dict[SoundEvent, list[Callable[[], None]]] = {}
        self._register_builtin_packs()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def active_pack_name(self) -> str | None:
        return self._active_pack.name if self._active_pack else None

    @property
    def active_pack(self) -> SoundPack | None:
        return self._active_pack

    @property
    def available_packs(self) -> list[str]:
        return list(self._packs.keys())

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def toggle(self) -> bool:
        self._enabled = not self._enabled
        return self._enabled

    def load_pack(self, name: str) -> bool:
        """Load a sound pack by name."""
        pack = self._packs.get(name)
        if pack is None:
            return False
        self._active_pack = pack
        return True

    def register_pack(self, pack: SoundPack) -> None:
        self._packs[pack.name] = pack

    def dispatch(self, event: SoundEvent) -> None:
        """Play sound for a lifecycle event if enabled."""
        if not self._enabled:
            return
        if self._active_pack is None:
            return

        sound_path = self._active_pack.get(event)
        if sound_path and os.path.exists(sound_path):
            self._player.play(sound_path)

        for hook in self._event_hooks.get(event, []):
            try:
                hook()
            except Exception:
                pass

    def on(self, event: SoundEvent, callback: Callable[[], None]) -> None:
        """Register a custom callback for a sound event."""
        self._event_hooks.setdefault(event, []).append(callback)

    def _register_builtin_packs(self) -> None:
        """Register built-in sound packs (no audio files bundled — paths must exist)."""
        base = Path(__file__).parent / "sounds"

        retro = SoundPack(
            name="retro",
            description="8-bit retro game sounds",
            sounds={
                SoundEvent.SESSION_START: str(base / "retro" / "start.wav"),
                SoundEvent.USER_PROMPT: str(base / "retro" / "input.wav"),
                SoundEvent.STOP: str(base / "retro" / "stop.wav"),
                SoundEvent.ERROR: str(base / "retro" / "error.wav"),
                SoundEvent.TASK_COMPLETE: str(base / "retro" / "complete.wav"),
            },
        )

        minimal = SoundPack(
            name="minimal",
            description="Subtle chimes — unobtrusive",
            sounds={
                SoundEvent.SESSION_START: str(base / "minimal" / "start.wav"),
                SoundEvent.STOP: str(base / "minimal" / "stop.wav"),
                SoundEvent.TASK_COMPLETE: str(base / "minimal" / "complete.wav"),
            },
        )

        sci_fi = SoundPack(
            name="sci-fi",
            description="Futuristic sci-fi effects",
            sounds={
                SoundEvent.SESSION_START: str(base / "sci-fi" / "start.wav"),
                SoundEvent.TOOL_SUCCESS: str(base / "sci-fi" / "success.wav"),
                SoundEvent.TOOL_FAILURE: str(base / "sci-fi" / "failure.wav"),
                SoundEvent.STOP: str(base / "sci-fi" / "stop.wav"),
                SoundEvent.PRE_COMPACT: str(base / "sci-fi" / "compact.wav"),
                SoundEvent.ERROR: str(base / "sci-fi" / "error.wav"),
            },
        )

        warcraft3 = SoundPack(
            name="warcraft3",
            description="Warcraft III peon grunts and work sounds",
            sounds={
                SoundEvent.SESSION_START: str(base / "warcraft3" / "ready_to_work.wav"),
                SoundEvent.ERROR: str(base / "warcraft3" / "not_ready.wav"),
                SoundEvent.TASK_COMPLETE: str(base / "warcraft3" / "work_complete.wav"),
                SoundEvent.AGENT_SPAWN: str(base / "warcraft3" / "zug_zug.wav"),
                SoundEvent.COST_WARNING: str(base / "warcraft3" / "not_enough_gold.wav"),
            },
        )

        self._packs = {"retro": retro, "minimal": minimal, "sci-fi": sci_fi, "warcraft3": warcraft3}

    def generate_pack_skeleton(self, name: str, target_dir: str | Path) -> Path:
        """Create a skeleton directory for a custom sound pack."""
        target = Path(target_dir) / name
        target.mkdir(parents=True, exist_ok=True)
        events = [
            "start.wav", "input.wav", "stop.wav", "error.wav",
            "success.wav", "failure.wav", "complete.wav", "compact.wav",
        ]
        for evt in events:
            (target / evt).touch()
        readme = target / "README.md"
        readme.write_text(
            f"# {name} Sound Pack\n\n"
            "Replace these placeholder files with your own .wav audio clips.\n"
            "Keep files short (< 2 seconds recommended).\n"
        )
        return target


_sound_manager: SoundManager | None = None


def get_sound_manager() -> SoundManager:
    """Get the global sound manager singleton."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
