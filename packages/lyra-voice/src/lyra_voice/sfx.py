"""SFX Personality Layer — voice packs, SFX themes, hook-triggered sounds (P0-B4 HIGH×LOW).

Provides themed sound effect collections (voice packs) that map pipeline
events to SFX assets. Supports built-in packs: Minimal, SciFi, Warcraft Peon.

See: plan-phase0-voice-mode.md §4, §5.3 Voice/Sound UX
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SFXCategory(str, Enum):
    """Categories of sound effects in a voice pack."""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    TURN_COMPLETE = "turn_complete"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    AGENT_HANDOFF = "agent_handoff"
    WORKFLOW_COMPLETE = "workflow_complete"
    WAKE_WORD_DETECTED = "wake_word_detected"
    BARGE_IN = "barge_in"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    STOP = "stop"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SFXAsset:
    """A single sound effect asset in a voice pack.

    Parameters
    ----------
    name : str
        Human-readable name (e.g., "Startup Chime").
    category : SFXCategory
        When this SFX is triggered.
    description : str
        Short description of the sound.
    file_path : str
        Path to audio file. Empty string means use generated tone.
    tone_frequency : float
        Frequency in Hz for generated tones. Default 440.0.
    tone_duration_ms : int
        Duration in ms for generated tones. Default 200.
    """

    name: str
    category: SFXCategory
    description: str = ""
    file_path: str = ""
    tone_frequency: float = 440.0
    tone_duration_ms: int = 200


@dataclass(frozen=True)
class VoicePack:
    """A themed collection of SFX assets and TTS voice profile.

    Parameters
    ----------
    pack_id : str
        Unique identifier (e.g., "minimal", "scifi", "warcraft_peon").
    name : str
        Display name.
    description : str
        Human-readable description of the pack's theme.
    tts_voice : str
        Default TTS voice for this pack.
    sfx : tuple[SFXAsset, ...]
        Sound effects in this pack.
    theme_colors : tuple[str, str]
        Primary and background colors as hex strings.
    """

    pack_id: str
    name: str
    description: str = ""
    tts_voice: str = "default"
    sfx: tuple[SFXAsset, ...] = ()
    theme_colors: tuple[str, str] = ("#4A90D9", "#1C1C1C")


# ---------------------------------------------------------------------------
# Built-in voice packs
# ---------------------------------------------------------------------------


def _build_minimal_pack() -> VoicePack:
    """Minimal pack — subtle clicks and beeps for professional use."""
    return VoicePack(
        pack_id="minimal",
        name="Minimal",
        description="Clean, professional sounds — subtle clicks and beeps",
        tts_voice="kokoro-default",
        theme_colors=("#4A90D9", "#F5F5F5"),
        sfx=(
            SFXAsset("Session Start", SFXCategory.SESSION_START,
                     "Soft ascending chime", tone_frequency=523.0, tone_duration_ms=150),
            SFXAsset("Session End", SFXCategory.SESSION_END,
                     "Soft descending chime", tone_frequency=392.0, tone_duration_ms=200),
            SFXAsset("Turn Complete", SFXCategory.TURN_COMPLETE,
                     "Subtle click", tone_frequency=800.0, tone_duration_ms=50),
            SFXAsset("Thinking", SFXCategory.THINKING,
                     "Soft low hum", tone_frequency=220.0, tone_duration_ms=100),
            SFXAsset("Tool Call", SFXCategory.TOOL_CALL,
                     "Quiet beep", tone_frequency=660.0, tone_duration_ms=60),
            SFXAsset("Tool Result", SFXCategory.TOOL_RESULT,
                     "Quiet double-beep", tone_frequency=880.0, tone_duration_ms=50),
            SFXAsset("Error", SFXCategory.ERROR,
                     "Low buzz", tone_frequency=200.0, tone_duration_ms=300),
            SFXAsset("Agent Handoff", SFXCategory.AGENT_HANDOFF,
                     "Transfer whoosh", tone_frequency=440.0, tone_duration_ms=150),
            SFXAsset("Workflow Complete", SFXCategory.WORKFLOW_COMPLETE,
                     "Success chime", tone_frequency=1047.0, tone_duration_ms=250),
            SFXAsset("Wake Word", SFXCategory.WAKE_WORD_DETECTED,
                     "Attention ping", tone_frequency=1200.0, tone_duration_ms=100),
            SFXAsset("Barge In", SFXCategory.BARGE_IN,
                     "Quick interrupt tone", tone_frequency=300.0, tone_duration_ms=80),
            SFXAsset("PreToolUse", SFXCategory.PRE_TOOL_USE,
                     "Tool start click", tone_frequency=700.0, tone_duration_ms=40),
            SFXAsset("PostToolUse", SFXCategory.POST_TOOL_USE,
                     "Tool done tick", tone_frequency=900.0, tone_duration_ms=40),
            SFXAsset("Stop", SFXCategory.STOP,
                     "Session end tone", tone_frequency=350.0, tone_duration_ms=200),
        ),
    )


def _build_scifi_pack() -> VoicePack:
    """SciFi pack — futuristic synth chimes and hums."""
    return VoicePack(
        pack_id="scifi",
        name="SciFi",
        description="Futuristic AI assistant — synth chimes and processing hums",
        tts_voice="orpheus-neural",
        theme_colors=("#00FF41", "#0D0D0D"),
        sfx=(
            SFXAsset("Startup Chime", SFXCategory.SESSION_START,
                     "Ascending arpeggio", tone_frequency=800.0, tone_duration_ms=300),
            SFXAsset("Shutdown", SFXCategory.SESSION_END,
                     "Descending sweep", tone_frequency=300.0, tone_duration_ms=400),
            SFXAsset("Confirmation Beep", SFXCategory.TURN_COMPLETE,
                     "Sci-fi confirmation", tone_frequency=1000.0, tone_duration_ms=80),
            SFXAsset("Processing Hum", SFXCategory.THINKING,
                     "Low frequency hum", tone_frequency=150.0, tone_duration_ms=200),
            SFXAsset("Tool Engage", SFXCategory.TOOL_CALL,
                     "Energy pulse", tone_frequency=1200.0, tone_duration_ms=100),
            SFXAsset("Tool Complete", SFXCategory.TOOL_RESULT,
                     "Task resolved ping", tone_frequency=1400.0, tone_duration_ms=80),
            SFXAsset("Error Alert", SFXCategory.ERROR,
                     "Alarm pulse", tone_frequency=250.0, tone_duration_ms=500),
            SFXAsset("Transfer", SFXCategory.AGENT_HANDOFF,
                     "Teleport sound", tone_frequency=600.0, tone_duration_ms=200),
            SFXAsset("Mission Complete", SFXCategory.WORKFLOW_COMPLETE,
                     "Fanfare", tone_frequency=1600.0, tone_duration_ms=400),
            SFXAsset("Attention", SFXCategory.WAKE_WORD_DETECTED,
                     "Alert ping", tone_frequency=2000.0, tone_duration_ms=120),
            SFXAsset("Interrupt", SFXCategory.BARGE_IN,
                     "Static burst", tone_frequency=180.0, tone_duration_ms=100),
            SFXAsset("PreToolUse", SFXCategory.PRE_TOOL_USE,
                     "Startup blip", tone_frequency=1100.0, tone_duration_ms=50),
            SFXAsset("PostToolUse", SFXCategory.POST_TOOL_USE,
                     "Shutdown blip", tone_frequency=900.0, tone_duration_ms=50),
            SFXAsset("Stop", SFXCategory.STOP,
                     "Shutdown sweep", tone_frequency=400.0, tone_duration_ms=300),
        ),
    )


def _build_warcraft_pack() -> VoicePack:
    """Warcraft III Peon pack — nostalgic RTS worker sounds."""
    return VoicePack(
        pack_id="warcraft_peon",
        name="Warcraft III Peon",
        description="Nostalgic Warcraft III Peon voice notifications — 'Ready to work!', 'Job's done!'",
        tts_voice="kokoro-default",
        theme_colors=("#8B4513", "#2F1F0E"),
        sfx=(
            SFXAsset("Ready to Work", SFXCategory.SESSION_START,
                     "\"Ready to work!\" — Peon spawning", tone_frequency=260.0, tone_duration_ms=500),
            SFXAsset("Job's Done", SFXCategory.SESSION_END,
                     "\"Job's done!\" — Task complete", tone_frequency=220.0, tone_duration_ms=400),
            SFXAsset("Work Complete", SFXCategory.TURN_COMPLETE,
                     "\"Work complete!\" — Turn done", tone_frequency=300.0, tone_duration_ms=300),
            SFXAsset("Something Need Doing?", SFXCategory.THINKING,
                     "\"Something need doing?\" — Agent thinking", tone_frequency=200.0, tone_duration_ms=600),
            SFXAsset("Yes M'lord", SFXCategory.TOOL_CALL,
                     "\"Yes m'lord?\" — Tool invocation", tone_frequency=280.0, tone_duration_ms=350),
            SFXAsset("Alright", SFXCategory.TOOL_RESULT,
                     "\"Alright.\" — Tool result", tone_frequency=320.0, tone_duration_ms=250),
            SFXAsset("I Can't Build There", SFXCategory.ERROR,
                     "\"I can't build there!\" — Error", tone_frequency=180.0, tone_duration_ms=450),
            SFXAsset("More Work?", SFXCategory.AGENT_HANDOFF,
                     "\"More work?\" — Handoff", tone_frequency=250.0, tone_duration_ms=300),
            SFXAsset("Work Complete", SFXCategory.WORKFLOW_COMPLETE,
                     "\"Work complete!\" — Workflow done", tone_frequency=330.0, tone_duration_ms=400),
            SFXAsset("Yes?", SFXCategory.WAKE_WORD_DETECTED,
                     "\"Yes?\" — Wake word", tone_frequency=350.0, tone_duration_ms=200),
            SFXAsset("What?", SFXCategory.BARGE_IN,
                     "\"What?\" — Interruption", tone_frequency=290.0, tone_duration_ms=200),
            SFXAsset("Yes M'lord", SFXCategory.PRE_TOOL_USE,
                     "\"Yes m'lord\" — Pre-tool", tone_frequency=310.0, tone_duration_ms=200),
            SFXAsset("Alright", SFXCategory.POST_TOOL_USE,
                     "\"Alright\" — Post-tool", tone_frequency=340.0, tone_duration_ms=200),
            SFXAsset("Job's Done", SFXCategory.STOP,
                     "\"Job's done!\" — Stop", tone_frequency=270.0, tone_duration_ms=300),
        ),
    )


BUILTIN_PACKS: tuple[VoicePack, ...] = (
    _build_minimal_pack(),
    _build_scifi_pack(),
    _build_warcraft_pack(),
)


# ---------------------------------------------------------------------------
# SFX Manager
# ---------------------------------------------------------------------------


@dataclass
class SFXManager:
    """Manages voice packs and routes pipeline events to SFX playback.

    Parameters
    ----------
    volume : float
        Master volume for all SFX (0.0–1.0). Default 0.7.
    enabled : bool
        Whether SFX playback is enabled. Default True.
    """

    volume: float = 0.7
    enabled: bool = True
    _packs: dict[str, VoicePack] = field(default_factory=dict)
    _active_pack_id: str = "minimal"
    _disabled_categories: set[SFXCategory] = field(default_factory=set)

    def __post_init__(self) -> None:
        for pack in BUILTIN_PACKS:
            self._packs[pack.pack_id] = pack

    # -- Pack management -------------------------------------------------------

    @property
    def active_pack(self) -> VoicePack:
        return self._packs[self._active_pack_id]

    @property
    def available_packs(self) -> tuple[str, ...]:
        return tuple(self._packs.keys())

    def set_pack(self, pack_id: str) -> VoicePack:
        """Switch to a different voice pack by ID.

        Raises ValueError if the pack_id is not found.
        """
        if pack_id not in self._packs:
            raise ValueError(
                f"Voice pack {pack_id!r} not found. Available: {self.available_packs}"
            )
        self._active_pack_id = pack_id
        logger.info("Voice pack switched to %s", pack_id)
        return self._packs[pack_id]

    def register_pack(self, pack: VoicePack) -> None:
        """Register a custom voice pack."""
        self._packs[pack.pack_id] = pack
        logger.info("Voice pack registered: %s", pack.pack_id)

    def unregister_pack(self, pack_id: str) -> None:
        """Remove a custom voice pack. Built-in packs cannot be removed."""
        if pack_id in {p.pack_id for p in BUILTIN_PACKS}:
            raise ValueError(f"Cannot unregister built-in pack: {pack_id!r}")
        if pack_id == self._active_pack_id:
            self._active_pack_id = "minimal"
        self._packs.pop(pack_id, None)

    # -- SFX routing -----------------------------------------------------------

    def get_sfx(self, category: SFXCategory) -> SFXAsset | None:
        """Get the SFX asset for a given category from the active pack."""
        pack = self.active_pack
        for sfx in pack.sfx:
            if sfx.category == category:
                return sfx
        return None

    def disable_category(self, category: SFXCategory) -> None:
        """Mute a specific SFX category."""
        self._disabled_categories.add(category)

    def enable_category(self, category: SFXCategory) -> None:
        """Unmute a specific SFX category."""
        self._disabled_categories.discard(category)

    # -- Playback --------------------------------------------------------------

    def play(self, category: SFXCategory) -> bytes:
        """Generate audio for an SFX category. Returns raw 16-bit PCM bytes.

        Returns empty bytes if SFX is disabled, the category is muted,
        or no asset is mapped.
        """
        if not self.enabled or category in self._disabled_categories:
            return b""

        asset = self.get_sfx(category)
        if asset is None:
            return b""

        return self._generate_tone(asset)

    def _generate_tone(self, asset: SFXAsset) -> bytes:
        """Generate a simple sine tone for an SFX asset."""
        import math
        import struct

        sample_rate = 24000
        num_samples = int(sample_rate * asset.tone_duration_ms / 1000)
        # Apply volume envelope (fade in/out)
        fade_samples = min(num_samples // 4, 200)

        samples: list[int] = []
        for i in range(num_samples):
            amplitude = int(16000 * self.volume)
            # Fade in
            if i < fade_samples:
                amplitude = int(amplitude * i / fade_samples)
            # Fade out
            elif i >= num_samples - fade_samples:
                amplitude = int(amplitude * (num_samples - i) / fade_samples)

            sample = amplitude * math.sin(
                2 * math.pi * asset.tone_frequency * i / sample_rate
            )
            samples.append(int(sample))

        return struct.pack(f"<{len(samples)}h", *samples)


# ---------------------------------------------------------------------------
# Hook event → SFX category mapping
# ---------------------------------------------------------------------------


# Maps Lyra hook events to SFX categories for P0-B5 integration
HOOK_TO_SFX: dict[str, SFXCategory] = {
    "PreToolUse": SFXCategory.PRE_TOOL_USE,
    "PostToolUse": SFXCategory.POST_TOOL_USE,
    "Stop": SFXCategory.STOP,
    "session_start": SFXCategory.SESSION_START,
    "session_end": SFXCategory.SESSION_END,
    "error": SFXCategory.ERROR,
    "agent_handoff": SFXCategory.AGENT_HANDOFF,
    "wake_word": SFXCategory.WAKE_WORD_DETECTED,
    "barge_in": SFXCategory.BARGE_IN,
    "thinking": SFXCategory.THINKING,
    "tool_call": SFXCategory.TOOL_CALL,
    "tool_result": SFXCategory.TOOL_RESULT,
    "workflow_complete": SFXCategory.WORKFLOW_COMPLETE,
    "turn_complete": SFXCategory.TURN_COMPLETE,
}


__all__ = [
    "BUILTIN_PACKS",
    "HOOK_TO_SFX",
    "SFXAsset",
    "SFXCategory",
    "SFXManager",
    "VoicePack",
]
