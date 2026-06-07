"""
Voice Pack / Sound Effects — personality layer for Lyra's voice mode.

Implements §5.3 Voice/Sound UX: configurable sound effects triggered by
hook events (session start, answer complete, error, long task done).

Bundled voice packs:
- "Warcraft Peon" — funny Warcraft-themed sounds
- "JARVIS" — professional British-accent announcements
- "Samantha" — warm conversational voice
- "Minimal" — subtle chimes only, no speech

References
----------
- §5.3 Voice/Sound UX Plan: plans/5.3-voice-sound-ux.md
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Warcraft peon sound effects via Claude Code hooks:
  https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class HookEvent(str, Enum):
    """Hook events that can trigger sound effects."""

    SESSION_START = "session_start"
    ANSWER_COMPLETE = "answer_complete"
    ERROR = "error"
    LONG_TASK_DONE = "long_task_done"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_PAUSED = "agent_paused"
    AGENT_NEEDS_INPUT = "agent_needs_input"
    SESSION_END = "session_end"


@dataclass(frozen=True)
class SoundMapping:
    """Maps a hook event to an audio file and optional TTS phrase.

    Attributes:
        event: The hook event that triggers this sound.
        audio_file: Path to a ``.wav`` / ``.mp3`` file, relative to the
            voice pack directory. ``None`` if TTS should be used instead.
        tts_phrase: TTS-generated announcement text. ``None`` if audio
            file should be used instead. If both are set, audio_file wins.
        volume: Playback volume multiplier (0.0–1.0). Default 1.0.
    """

    event: HookEvent
    audio_file: Optional[str] = None
    tts_phrase: Optional[str] = None
    volume: float = 1.0

    def __post_init__(self) -> None:
        if self.audio_file is None and self.tts_phrase is None:
            raise ValueError(
                f"SoundMapping for {self.event.value} must have "
                "either audio_file or tts_phrase"
            )


@dataclass
class VoicePack:
    """A named collection of sound mappings.

    Attributes:
        name: Unique pack identifier (e.g. ``"warcraft-peon"``).
        display_name: Human-readable name.
        description: One-line description of the pack's personality.
        sounds: List of ``SoundMapping`` entries.
    """

    name: str
    display_name: str
    description: str = ""
    sounds: list[SoundMapping] = field(default_factory=list)

    def get_sound(self, event: HookEvent) -> Optional[SoundMapping]:
        """Get the sound mapping for a specific event, if defined."""
        for s in self.sounds:
            if s.event == event:
                return s
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "sounds": [
                {
                    "event": s.event.value,
                    "audio_file": s.audio_file,
                    "tts_phrase": s.tts_phrase,
                    "volume": s.volume,
                }
                for s in self.sounds
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoicePack":
        sounds = [
            SoundMapping(
                event=HookEvent(s["event"]),
                audio_file=s.get("audio_file"),
                tts_phrase=s.get("tts_phrase"),
                volume=s.get("volume", 1.0),
            )
            for s in data.get("sounds", [])
        ]
        return cls(
            name=data["name"],
            display_name=data["display_name"],
            description=data.get("description", ""),
            sounds=sounds,
        )


# ---------------------------------------------------------------------------
# Bundled voice packs
# ---------------------------------------------------------------------------


def _bundled_warcraft_peon() -> VoicePack:
    """Warcraft Peon — funny Warcraft-themed sound pack."""
    return VoicePack(
        name="warcraft-peon",
        display_name="Warcraft Peon",
        description="Zug zug! Work complete!",
        sounds=[
            SoundMapping(
                event=HookEvent.SESSION_START,
                tts_phrase="Work complete!",
                volume=0.8,
            ),
            SoundMapping(
                event=HookEvent.ANSWER_COMPLETE,
                tts_phrase="Job's done!",
                volume=0.7,
            ),
            SoundMapping(
                event=HookEvent.ERROR,
                tts_phrase="Something need doing?",
                volume=0.7,
            ),
            SoundMapping(
                event=HookEvent.LONG_TASK_DONE,
                tts_phrase="Zug zug!",
                volume=0.6,
            ),
            SoundMapping(
                event=HookEvent.SESSION_END,
                tts_phrase="Me not that kind of orc!",
                volume=0.6,
            ),
        ],
    )


def _bundled_jarvis() -> VoicePack:
    """JARVIS — professional British-accent announcements."""
    return VoicePack(
        name="jarvis",
        display_name="JARVIS",
        description="At your service, sir.",
        sounds=[
            SoundMapping(
                event=HookEvent.SESSION_START,
                tts_phrase="At your service.",
                volume=0.7,
            ),
            SoundMapping(
                event=HookEvent.ANSWER_COMPLETE,
                tts_phrase="Task accomplished.",
                volume=0.6,
            ),
            SoundMapping(
                event=HookEvent.ERROR,
                tts_phrase="Anomaly detected. Reviewing.",
                volume=0.7,
            ),
            SoundMapping(
                event=HookEvent.LONG_TASK_DONE,
                tts_phrase="Long-running task complete, sir.",
                volume=0.6,
            ),
            SoundMapping(
                event=HookEvent.AGENT_NEEDS_INPUT,
                tts_phrase="Your input is required.",
                volume=0.6,
            ),
        ],
    )


def _bundled_samantha() -> VoicePack:
    """Samantha — warm, conversational voice."""
    return VoicePack(
        name="samantha",
        display_name="Samantha",
        description="Hey there, ready to work.",
        sounds=[
            SoundMapping(
                event=HookEvent.SESSION_START,
                tts_phrase="Hey there! Ready to work.",
                volume=0.75,
            ),
            SoundMapping(
                event=HookEvent.ANSWER_COMPLETE,
                tts_phrase="All done!",
                volume=0.65,
            ),
            SoundMapping(
                event=HookEvent.ERROR,
                tts_phrase="Hmm, that didn't work. Let me try again.",
                volume=0.7,
            ),
            SoundMapping(
                event=HookEvent.LONG_TASK_DONE,
                tts_phrase="That took a while, but it's done!",
                volume=0.65,
            ),
            SoundMapping(
                event=HookEvent.AGENT_NEEDS_INPUT,
                tts_phrase="Hey, I need your input on something.",
                volume=0.7,
            ),
        ],
    )


def _bundled_minimal() -> VoicePack:
    """Minimal — subtle chimes only, no speech announcements."""
    return VoicePack(
        name="minimal",
        display_name="Minimal",
        description="Subtle chimes only. No speech.",
        sounds=[
            SoundMapping(
                event=HookEvent.SESSION_START,
                audio_file="chimes/start.wav",
                volume=0.3,
            ),
            SoundMapping(
                event=HookEvent.ANSWER_COMPLETE,
                audio_file="chimes/complete.wav",
                volume=0.2,
            ),
            SoundMapping(
                event=HookEvent.ERROR,
                audio_file="chimes/error.wav",
                volume=0.4,
            ),
        ],
    )


BUNDLED_PACKS: dict[str, VoicePack] = {
    "warcraft-peon": _bundled_warcraft_peon(),
    "jarvis": _bundled_jarvis(),
    "samantha": _bundled_samantha(),
    "minimal": _bundled_minimal(),
}


# ---------------------------------------------------------------------------
# Sound effect engine
# ---------------------------------------------------------------------------


@dataclass
class SoundEffectEngine:
    """Plays sound effects on hook events.

    Usage::

        engine = SoundEffectEngine(active_pack="warcraft-peon")
        engine.on_event(HookEvent.SESSION_START)

    The engine supports:
    - Bundled voice packs (Warcraft Peon, JARVIS, Samantha, Minimal)
    - Custom voice packs loaded from disk (``~/.lyra/voice-packs/``)
    - TTS fallback for packs that use phrases instead of audio files
    - Volume control per event
    """

    active_pack: str = "minimal"
    _custom_packs: dict[str, VoicePack] = field(default_factory=dict)
    _tts_callback: Any = None  # (phrase: str) -> None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_event(self, event: HookEvent) -> Optional[SoundMapping]:
        """Trigger sound for a hook event.

        Args:
            event: The hook event that occurred.

        Returns:
            The ``SoundMapping`` that was triggered, or ``None`` if the
            active pack has no mapping for this event.
        """
        pack = self._get_active_pack()
        if pack is None:
            return None

        sound = pack.get_sound(event)
        if sound is None:
            return None

        self._play(sound)
        return sound

    def set_pack(self, name: str) -> None:
        """Switch the active voice pack.

        Args:
            name: Pack identifier (e.g. ``"jarvis"``).

        Raises:
            ValueError: If the pack is not found.
        """
        if name not in BUNDLED_PACKS and name not in self._custom_packs:
            available = list(BUNDLED_PACKS.keys()) + list(self._custom_packs.keys())
            raise ValueError(
                f"Unknown voice pack '{name}'. Available: {', '.join(available)}"
            )
        self.active_pack = name

    def load_custom_pack(self, path: Path) -> VoicePack:
        """Load a custom voice pack from a JSON file.

        Args:
            path: Path to a ``.json`` file with voice pack definition.

        Returns:
            The loaded ``VoicePack``.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the JSON is malformed.
        """
        if not path.is_file():
            raise FileNotFoundError(f"Voice pack not found: {path}")

        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        pack = VoicePack.from_dict(data)
        self._custom_packs[pack.name] = pack
        return pack

    def register_tts_callback(self, callback: Any) -> None:
        """Register a TTS callback for packs that use phrases.

        Args:
            callback: A callable ``(phrase: str) -> None`` that speaks
                the given phrase through the configured TTS provider.
        """
        self._tts_callback = callback

    def list_packs(self) -> list[dict[str, str]]:
        """List all available voice packs."""
        result = []
        for name, pack in BUNDLED_PACKS.items():
            result.append({
                "name": name,
                "display_name": pack.display_name,
                "description": pack.description,
                "source": "bundled",
            })
        for name, pack in self._custom_packs.items():
            result.append({
                "name": name,
                "display_name": pack.display_name,
                "description": pack.description,
                "source": "custom",
            })
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_active_pack(self) -> Optional[VoicePack]:
        """Get the currently active voice pack."""
        if self.active_pack in BUNDLED_PACKS:
            return BUNDLED_PACKS[self.active_pack]
        return self._custom_packs.get(self.active_pack)

    def _play(self, sound: SoundMapping) -> None:
        """Play a sound mapping (audio file or TTS phrase)."""
        if sound.audio_file is not None:
            self._play_audio_file(sound)
        elif sound.tts_phrase is not None and self._tts_callback is not None:
            self._tts_callback(sound.tts_phrase)

    @staticmethod
    def _play_audio_file(sound: SoundMapping) -> None:
        """Play an audio file. Placeholder — integrate with system audio."""
        # Integration point: use ``pygame.mixer``, ``playsound``,
        # or ``pydub`` + ``simpleaudio`` for actual playback.
        # For now this is a documented integration point.
        pass
