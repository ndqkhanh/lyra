"""Voice Hook Integration — hook-based audio playback (P0-B5 HIGH×LOW).

Connects Lyra's hook pipeline (PreToolUse, PostToolUse, Stop) to the
SFX personality layer for low-latency audio feedback on tool events.

See: plan-phase0-voice-mode.md §4.2, Claude Code hooks + sounddevice
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from lyra_voice.sfx import HOOK_TO_SFX, SFXCategory, SFXManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HookEvent(str, Enum):
    """Hook events that can trigger SFX playback."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR = "error"
    AGENT_HANDOFF = "agent_handoff"
    WAKE_WORD = "wake_word"
    BARGE_IN = "barge_in"
    NOTIFICATION = "notification"


class PlaybackMode(str, Enum):
    """How audio is played back for hook events."""

    SYNC = "sync"  # Block until playback completes
    ASYNC = "async"  # Fire-and-forget
    QUEUED = "queued"  # Queue and play sequentially


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VoiceHookMapping:
    """Maps a hook event to an SFX category with optional condition.

    Parameters
    ----------
    hook_event : str
        Hook event name (e.g., "PreToolUse", "PostToolUse").
    sfx_category : SFXCategory
        SFX to play when this hook fires.
    condition : str
        Optional condition for conditional playback.
        Empty string means always play.
    cooldown_ms : int
        Minimum time between repeated triggers of this hook (0 = no limit).
    """

    hook_event: str
    sfx_category: SFXCategory
    condition: str = ""
    cooldown_ms: int = 0


@dataclass
class VoiceHookStats:
    """Statistics for voice hook playback."""

    total_triggers: int = 0
    total_played: int = 0
    total_skipped: int = 0
    per_hook: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Default hook mappings
# ---------------------------------------------------------------------------


DEFAULT_HOOK_MAPPINGS: tuple[VoiceHookMapping, ...] = (
    VoiceHookMapping("PreToolUse", SFXCategory.PRE_TOOL_USE, cooldown_ms=200),
    VoiceHookMapping("PostToolUse", SFXCategory.POST_TOOL_USE, cooldown_ms=200),
    VoiceHookMapping("Stop", SFXCategory.STOP),
    VoiceHookMapping("session_start", SFXCategory.SESSION_START),
    VoiceHookMapping("session_end", SFXCategory.SESSION_END),
    VoiceHookMapping("error", SFXCategory.ERROR),
    VoiceHookMapping("agent_handoff", SFXCategory.AGENT_HANDOFF),
    VoiceHookMapping("wake_word", SFXCategory.WAKE_WORD_DETECTED),
    VoiceHookMapping("barge_in", SFXCategory.BARGE_IN),
    VoiceHookMapping("thinking", SFXCategory.THINKING, cooldown_ms=500),
    VoiceHookMapping("tool_call", SFXCategory.TOOL_CALL, cooldown_ms=200),
    VoiceHookMapping("tool_result", SFXCategory.TOOL_RESULT, cooldown_ms=200),
    VoiceHookMapping("workflow_complete", SFXCategory.WORKFLOW_COMPLETE),
    VoiceHookMapping("turn_complete", SFXCategory.TURN_COMPLETE, cooldown_ms=300),
)


# ---------------------------------------------------------------------------
# Voice Hook Manager
# ---------------------------------------------------------------------------


@dataclass
class VoiceHookManager:
    """Integrates Lyra hooks with voice SFX playback.

    Parameters
    ----------
    sfx_manager : SFXManager | None
        SFX manager for audio generation. Creates a default if None.
    mode : PlaybackMode
        Playback strategy for hook events. Default ASYNC.
    """

    sfx_manager: SFXManager = field(default_factory=SFXManager)
    mode: PlaybackMode = PlaybackMode.ASYNC
    _mappings: dict[str, VoiceHookMapping] = field(default_factory=dict)
    _stats: VoiceHookStats = field(default_factory=VoiceHookStats)
    _last_triggered: dict[str, float] = field(default_factory=dict)
    _muted_hooks: set[str] = field(default_factory=set)
    _hook_handlers: dict[str, list] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for mapping in DEFAULT_HOOK_MAPPINGS:
            self._mappings[mapping.hook_event] = mapping

    # -- Hook registration -----------------------------------------------------

    def register_hook(self, mapping: VoiceHookMapping) -> None:
        """Register or override a hook→SFX mapping."""
        self._mappings[mapping.hook_event] = mapping
        logger.debug("Hook registered: %s → %s", mapping.hook_event, mapping.sfx_category)

    def unregister_hook(self, hook_event: str) -> None:
        """Remove a hook→SFX mapping."""
        self._mappings.pop(hook_event, None)

    def get_mapping(self, hook_event: str) -> VoiceHookMapping | None:
        """Get the SFX mapping for a hook event."""
        return self._mappings.get(hook_event)

    # -- Playback control ------------------------------------------------------

    def mute_hook(self, hook_event: str) -> None:
        """Mute SFX for a specific hook event."""
        self._muted_hooks.add(hook_event)

    def unmute_hook(self, hook_event: str) -> None:
        """Unmute SFX for a specific hook event."""
        self._muted_hooks.discard(hook_event)

    def is_muted(self, hook_event: str) -> bool:
        """Check if a hook event is muted."""
        return hook_event in self._muted_hooks

    # -- Hook handler ----------------------------------------------------------

    def on_hook(
        self,
        hook_event: str,
        context: dict | None = None,
    ) -> bytes:
        """Handle a hook event — play the mapped SFX if applicable.

        Parameters
        ----------
        hook_event : str
            The hook event name (e.g., "PreToolUse", "PostToolUse").
        context : dict | None
            Optional context from the hook (tool name, error message, etc.).

        Returns
        -------
        bytes
            Raw 16-bit PCM audio data, or empty bytes if SFX was skipped.
        """
        import time

        self._stats.total_triggers += 1
        self._stats.per_hook[hook_event] = self._stats.per_hook.get(hook_event, 0) + 1

        # Check if muted
        if hook_event in self._muted_hooks:
            self._stats.total_skipped += 1
            return b""

        # Check for mapping
        mapping = self._mappings.get(hook_event)
        if mapping is None:
            # Try HOOK_TO_SFX fallback
            sfx_cat = HOOK_TO_SFX.get(hook_event)
            if sfx_cat is None:
                self._stats.total_skipped += 1
                return b""
            mapping = VoiceHookMapping(hook_event, sfx_cat)

        # Cooldown check
        if mapping.cooldown_ms > 0:
            now = time.time()
            last = self._last_triggered.get(hook_event, 0.0)
            if (now - last) * 1000 < mapping.cooldown_ms:
                self._stats.total_skipped += 1
                return b""
            self._last_triggered[hook_event] = now

        # Condition check
        if mapping.condition and context:
            if not self._evaluate_condition(mapping.condition, context):
                self._stats.total_skipped += 1
                return b""

        # Play SFX
        audio = self.sfx_manager.play(mapping.sfx_category)
        self._stats.total_played += 1
        return audio

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a simple condition string against hook context.

        Supports: ``tool_name==<name>`` and ``status==<status>``.
        """
        try:
            if "==" in condition:
                key, value = condition.split("==", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                return str(context.get(key, "")) == value
            if "!=" in condition:
                key, value = condition.split("!=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                return str(context.get(key, "")) != value
        except Exception:
            logger.debug("Condition evaluation failed: %s", condition)
        return True  # Default to playing if condition can't be evaluated

    # -- Statistics ------------------------------------------------------------

    @property
    def stats(self) -> VoiceHookStats:
        return self._stats

    def reset_stats(self) -> None:
        """Reset hook playback statistics."""
        self._stats = VoiceHookStats()
        self._last_triggered.clear()

    # -- Lifecycle -------------------------------------------------------------

    def on_session_start(self) -> bytes:
        """Play session start SFX."""
        return self.on_hook("session_start")

    def on_session_end(self) -> bytes:
        """Play session end SFX."""
        return self.on_hook("session_end")

    def on_error(self, error_msg: str = "") -> bytes:
        """Play error SFX."""
        return self.on_hook("error", {"error": error_msg})


__all__ = [
    "DEFAULT_HOOK_MAPPINGS",
    "HookEvent",
    "PlaybackMode",
    "VoiceHookManager",
    "VoiceHookMapping",
    "VoiceHookStats",
]
