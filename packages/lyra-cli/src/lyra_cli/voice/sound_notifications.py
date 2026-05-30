"""Sound notifications for agent lifecycle states.

Provides configurable sound effects per agent state (task_complete, error,
warning, agent_ready, agent_thinking) using system beep or audio files.
"""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = [
    "AgentState",
    "SoundConfig",
    "SoundNotifier",
    "WARCRAFT3_THEME_PRESETS",
    "THEME_PRESETS",
    "get_sound_notifier",
]


class AgentState(str, Enum):
    """Agent lifecycle states that can trigger sound notifications."""

    STARTUP = "startup"
    TASK_COMPLETE = "task_complete"
    ERROR = "error"
    WARNING = "warning"
    AGENT_READY = "agent_ready"
    AGENT_THINKING = "agent_thinking"
    AGENT_SPAWN = "agent_spawn"
    COST_WARNING = "cost_warning"


AGENT_STATE_BEEP_PATTERNS: dict[AgentState, str] = {
    AgentState.STARTUP: "ready",
    AgentState.TASK_COMPLETE: "success",
    AgentState.ERROR: "error",
    AgentState.WARNING: "warning",
    AgentState.AGENT_READY: "ready",
    AgentState.AGENT_THINKING: "thinking",
    AgentState.AGENT_SPAWN: "ready",
    AgentState.COST_WARNING: "warning",
}


@dataclass
class SoundConfig:
    """Configuration for a single sound notification type.

    Parameters
    ----------
    enabled : bool
        Whether this notification type is active. Defaults to True.
    sound_path : str | None
        Path to an audio file. Uses system beep if None.
    duration_ms : int
        Duration of the beep/tone in milliseconds. Default 200.
    frequency : int
        Frequency of the beep in Hz. Default 440 (A4).
    repetitions : int
        Number of times to repeat the sound. Default 1.
    theme : str
        Optional theme identifier (e.g. ``"warcraft3"``). Defaults to empty.
    """

    enabled: bool = True
    sound_path: str | None = None
    duration_ms: int = 200
    frequency: int = 440
    repetitions: int = 1
    theme: str = ""

    def __post_init__(self) -> None:
        self.duration_ms = max(50, min(5000, self.duration_ms))
        self.frequency = max(20, min(20000, self.frequency))
        self.repetitions = max(1, min(20, self.repetitions))


# Standard presets per agent state
DEFAULT_SOUND_PRESETS: dict[AgentState, SoundConfig] = {
    AgentState.STARTUP: SoundConfig(
        frequency=660, duration_ms=200, repetitions=1,
    ),
    AgentState.TASK_COMPLETE: SoundConfig(
        frequency=880, duration_ms=300, repetitions=2,
    ),
    AgentState.ERROR: SoundConfig(
        frequency=220, duration_ms=500, repetitions=3,
    ),
    AgentState.WARNING: SoundConfig(
        frequency=440, duration_ms=300, repetitions=2,
    ),
    AgentState.AGENT_READY: SoundConfig(
        frequency=660, duration_ms=200, repetitions=1,
    ),
    AgentState.AGENT_THINKING: SoundConfig(
        frequency=330, duration_ms=150, repetitions=1,
    ),
    AgentState.AGENT_SPAWN: SoundConfig(
        frequency=660, duration_ms=200, repetitions=1,
    ),
    AgentState.COST_WARNING: SoundConfig(
        frequency=440, duration_ms=400, repetitions=3,
    ),
}

# Warcraft III theme presets — low grunt-like frequencies for peon feel
WARCRAFT3_THEME_PRESETS: dict[AgentState, SoundConfig] = {
    AgentState.STARTUP: SoundConfig(
        frequency=180, duration_ms=250, repetitions=1, theme="warcraft3",
    ),
    AgentState.TASK_COMPLETE: SoundConfig(
        frequency=220, duration_ms=400, repetitions=2, theme="warcraft3",
    ),
    AgentState.ERROR: SoundConfig(
        frequency=120, duration_ms=600, repetitions=3, theme="warcraft3",
    ),
    AgentState.WARNING: SoundConfig(
        frequency=150, duration_ms=350, repetitions=2, theme="warcraft3",
    ),
    AgentState.AGENT_READY: SoundConfig(
        frequency=200, duration_ms=200, repetitions=1, theme="warcraft3",
    ),
    AgentState.AGENT_THINKING: SoundConfig(
        frequency=160, duration_ms=180, repetitions=1, theme="warcraft3",
    ),
    AgentState.AGENT_SPAWN: SoundConfig(
        frequency=200, duration_ms=250, repetitions=1, theme="warcraft3",
    ),
    AgentState.COST_WARNING: SoundConfig(
        frequency=130, duration_ms=500, repetitions=3, theme="warcraft3",
    ),
}

THEME_PRESETS: dict[str, dict[AgentState, SoundConfig]] = {
    "warcraft3": WARCRAFT3_THEME_PRESETS,
}


class SoundNotifier:
    """Plays configurable sound effects for agent lifecycle states.

    Usage::

        notifier = SoundNotifier()
        notifier.notify(AgentState.TASK_COMPLETE)
        notifier.configure(AgentState.ERROR, SoundConfig(frequency=200, repetitions=3))
    """

    def __init__(
        self,
        configs: dict[AgentState, SoundConfig] | None = None,
    ) -> None:
        self._enabled: bool = True
        self._configs: dict[AgentState, SoundConfig] = {
            **DEFAULT_SOUND_PRESETS,
            **(configs or {}),
        }
        self._callbacks: dict[AgentState, list[Callable[[], None]]] = {}
        self._system = platform.system()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def toggle(self) -> bool:
        self._enabled = not self._enabled
        return self._enabled

    def configure(self, state: AgentState, config: SoundConfig) -> None:
        """Override the sound config for a specific agent state."""
        self._configs[state] = config

    def get_config(self, state: AgentState) -> SoundConfig:
        """Get the sound config for a specific agent state."""
        return self._configs.get(state, SoundConfig(enabled=False))

    def apply_theme(self, theme: str) -> bool:
        """Apply a theme's sound presets over the current configuration.

        Parameters
        ----------
        theme : str
            Theme name (e.g. ``"warcraft3"``).

        Returns
        -------
        bool
            ``True`` if the theme was found and applied.
        """
        presets = THEME_PRESETS.get(theme)
        if presets is None:
            return False
        for state, config in presets.items():
            self._configs[state] = config
        return True

    def on(self, state: AgentState, callback: Callable[[], None]) -> None:
        """Register a callback that fires when the given state is notified."""
        self._callbacks.setdefault(state, []).append(callback)

    def notify(self, state: AgentState) -> None:
        """Play the sound notification for an agent state.

        Falls back to system beep if no audio file is configured.
        """
        if not self._enabled:
            return

        config = self._configs.get(state)
        if config is None or not config.enabled:
            return

        if config.sound_path and Path(config.sound_path).exists():
            self._play_file(config.sound_path)
        else:
            self._play_beep(config)

        self._fire_callbacks(state)

    def _play_file(self, path: str) -> None:
        """Play an audio file using the OS-native player."""
        try:
            if self._system == "Darwin":
                subprocess.Popen(
                    ["afplay", path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif self._system == "Linux":
                for cmd in (["paplay", path], ["aplay", path]):
                    subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    break
            elif self._system == "Windows":
                subprocess.Popen(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass  # best-effort

    def _play_beep(self, config: SoundConfig) -> None:
        """Play a system beep or terminal bell.

        On macOS uses ``say`` with a short tone. On other systems,
        uses the terminal bell character.
        """
        for _ in range(config.repetitions):
            try:
                if self._system == "Darwin":
                    subprocess.run(
                        ["say", "beep"],
                        capture_output=True, check=False, timeout=1,
                    )
                elif self._system == "Linux":
                    subprocess.run(
                        ["speaker-test", "-t", "sine", "-f", str(config.frequency),
                         "-l", "1", "-p", str(max(1, config.duration_ms // 100))],
                        capture_output=True, check=False, timeout=2,
                    )
                else:
                    print("\a", end="", flush=True)
            except Exception:
                print("\a", end="", flush=True)

    def _fire_callbacks(self, state: AgentState) -> None:
        for cb in self._callbacks.get(state, []):
            try:
                cb()
            except Exception:
                pass


_notifier: SoundNotifier | None = None


def get_sound_notifier() -> SoundNotifier:
    """Get the global SoundNotifier singleton."""
    global _notifier
    if _notifier is None:
        _notifier = SoundNotifier()
    return _notifier
