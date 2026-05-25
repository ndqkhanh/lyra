"""Plan 8 Part 2: CESP Engine — Cross-Environment Sound Protocol event mapping.

Provides CESP v1.0 event categories, Hook→CESP mapping, no-repeat sound
selection with cooldown enforcement, and 6-layer pack selection hierarchy.
"""

from __future__ import annotations

import fnmatch
import random
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CespCategory(Enum):
    """CESP v1.0 standard event categories."""

    SESSION_START = "session.start"
    SESSION_END = "session.end"
    TASK_START = "task.start"
    TASK_COMPLETE = "task.complete"
    TASK_ERROR = "task.error"
    INPUT_REQUIRED = "input.required"
    THINKING_START = "thinking.start"
    THINKING_END = "thinking.end"
    RESOURCE_LIMIT = "resource.limit"
    PERMISSION_CHECK = "permission.check"
    USER_SPAM = "user.spam"
    GOAL_COMPLETE = "goal.complete"


# Hook event → CESP category mapping (per Plan 8 Part 2.1)
HOOK_TO_CESP: dict[str, CespCategory] = {
    "SessionStart": CespCategory.SESSION_START,
    "SessionEnd": CespCategory.SESSION_END,
    "UserPromptSubmit": CespCategory.TASK_START,
    "Stop": CespCategory.TASK_COMPLETE,
    "PostToolUseFailure": CespCategory.TASK_ERROR,
    "PermissionRequest": CespCategory.INPUT_REQUIRED,
    "PreCompact": CespCategory.RESOURCE_LIMIT,
    "Notification": CespCategory.TASK_COMPLETE,  # deduplicated
}

# Categories that should be deduplicated within N seconds
DEDUP_WINDOW_SECONDS = 3.0
DEDUP_CATEGORIES: set[CespCategory] = {CespCategory.TASK_COMPLETE}


class PackSelectionLayer(Enum):
    """6-layer pack selection hierarchy (Plan 8 Part 1.3)."""

    SESSION_OVERRIDE = 1
    PATH_RULES = 2
    IDE_RULES = 3
    PACK_ROTATION = 4
    DEFAULT_PACK = 5
    HARDCODED_FALLBACK = 6


@dataclass(frozen=True)
class SelectionResult:
    """Result of sound selection for a CESP category.

    Attributes:
        filepath: Path to the selected sound file, or None if unavailable.
        category: The CESP category that was matched.
        pack_id: The pack that provided the sound.
        selection_layer: Which layer of the hierarchy was used.
    """

    filepath: Path | None
    category: CespCategory
    pack_id: str
    selection_layer: PackSelectionLayer


@dataclass(frozen=True)
class PlaybackRecord:
    """Tracks playback history for no-repeat and cooldown enforcement."""

    category: CespCategory
    filename: str
    timestamp: float
    pack_id: str


# ── CESP Engine ───────────────────────────────────────────────────────────


class CespEngine:
    """CESP event mapping and sound selection engine.

    Handles hook→CESP event mapping, no-repeat sound selection with
    cooldown enforcement, and deduplication of rapid-fire events.

    Usage::

        engine = CespEngine(pack_loader)
        result = engine.select("fantasy", CespCategory.TASK_COMPLETE)
        if result.filepath:
            player.play(result.filepath)
    """

    def __init__(self, pack_loader: object | None = None) -> None:
        """Initialize the CESP engine.

        Args:
            pack_loader: A SoundPackLoader-compatible instance for resolving pack files.
        """
        self._pack_loader = pack_loader
        self._history: list[PlaybackRecord] = []
        self._session_override: str | None = None
        self._default_pack = "minimal"
        self._enabled_packs: list[str] = []
        self._rotation_mode = "random"
        self._path_rules: dict[str, str] = {}
        self._ide_rules: dict[str, str] = {}
        self._rotation_index: dict[str, int] = {}

    # ── Hierarchy Configuration ──────────────────────────────────────────

    def set_session_override(self, pack_id: str | None) -> None:
        """Set per-session pack override (Layer 1)."""
        self._session_override = pack_id

    def set_default_pack(self, pack_id: str) -> None:
        """Set the default fallback pack (Layer 5)."""
        self._default_pack = pack_id

    def set_enabled_packs(self, pack_ids: list[str], rotation: str = "random") -> None:
        """Set enabled packs and rotation mode (Layer 4)."""
        self._enabled_packs = list(pack_ids)
        self._rotation_mode = rotation

    def set_path_rules(self, rules: dict[str, str]) -> None:
        """Set glob-based path rules (Layer 2)."""
        self._path_rules = dict(rules)

    def set_ide_rules(self, rules: dict[str, str]) -> None:
        """Set IDE-based rules (Layer 3)."""
        self._ide_rules = dict(rules)

    # ── Event Mapping ────────────────────────────────────────────────────

    def map_hook(self, hook_name: str) -> CespCategory:
        """Map a Lyra hook event name to its CESP category."""
        return HOOK_TO_CESP.get(hook_name, CespCategory.TASK_COMPLETE)

    def should_deduplicate(self, category: CespCategory, now: float | None = None) -> bool:
        """Check if this category event should be suppressed due to dedup."""
        if category not in DEDUP_CATEGORIES:
            return False
        now = now or time.time()
        for record in reversed(self._history):
            if record.category == category:
                return (now - record.timestamp) < DEDUP_WINDOW_SECONDS
        return False

    # ── Pack Selection (6-Layer Hierarchy) ────────────────────────────────

    def select_pack(self, working_dir: str | None = None, ide_name: str | None = None) -> str:
        """Select the active pack using the 6-layer hierarchy.

        Returns the resolved pack_id.
        """
        # Layer 1: Session override
        if self._session_override:
            return self._session_override

        # Layer 2: Path rules (glob match on working directory)
        if working_dir and self._path_rules:
            for pattern, pack_id in self._path_rules.items():
                if fnmatch.fnmatch(working_dir, pattern):
                    return pack_id

        # Layer 3: IDE rules
        if ide_name and ide_name in self._ide_rules:
            return self._ide_rules[ide_name]

        # Layer 4: Pack rotation
        if self._enabled_packs:
            if self._rotation_mode == "random":
                return random.choice(self._enabled_packs)
            else:
                # Round-robin
                key = "global"
                idx = self._rotation_index.get(key, 0)
                chosen = self._enabled_packs[idx % len(self._enabled_packs)]
                self._rotation_index[key] = idx + 1
                return chosen

        # Layer 5: Default pack
        if self._default_pack:
            return self._default_pack

        # Layer 6: Hardcoded fallback
        return "minimal"

    # ── Sound Selection ──────────────────────────────────────────────────

    def select(
        self,
        pack_id: str,
        category: CespCategory,
        candidates: dict[str, list[str]] | None = None,
        no_repeat: bool = True,
        cooldown_ms: int = 3000,
    ) -> SelectionResult:
        """Select a sound file for a category using no-repeat/cooldown logic.

        Args:
            pack_id: The active pack identifier.
            category: The CESP event category.
            candidates: Dict mapping category values to lists of filenames.
            no_repeat: Whether to avoid repeating the last-played file.
            cooldown_ms: Minimum time between plays of the same category.
        """
        now = time.time()

        # Cooldown check
        if cooldown_ms > 0:
            for record in reversed(self._history):
                if record.category == category:
                    elapsed = (now - record.timestamp) * 1000
                    if elapsed < cooldown_ms:
                        return SelectionResult(
                            filepath=None,
                            category=category,
                            pack_id=pack_id,
                            selection_layer=PackSelectionLayer.SESSION_OVERRIDE,
                        )
                    break

        # Get available files
        cat_key = category.value
        available: list[str] = []
        if candidates and cat_key in candidates:
            available = list(candidates[cat_key])

        if not available:
            return SelectionResult(
                filepath=None,
                category=category,
                pack_id=pack_id,
                selection_layer=PackSelectionLayer.SESSION_OVERRIDE,
            )

        # No-repeat: exclude last-played
        if no_repeat and len(available) > 1:
            last_played: str | None = None
            for record in reversed(self._history):
                if record.category == category and record.pack_id == pack_id:
                    last_played = record.filename
                    break
            if last_played and last_played in available:
                filtered = [f for f in available if f != last_played]
                if filtered:
                    available = filtered

        chosen = random.choice(available)

        # Record playback
        self._history.append(PlaybackRecord(
            category=category,
            filename=chosen,
            timestamp=now,
            pack_id=pack_id,
        ))

        # Trim history
        if len(self._history) > 200:
            self._history = self._history[-100:]

        # Resolve filepath (delegate to pack_loader if available)
        filepath: Path | None = None
        if self._pack_loader and hasattr(self._pack_loader, "resolve_sound"):
            filepath = self._pack_loader.resolve_sound(pack_id, chosen)  # type: ignore[union-attr]
        elif self._pack_loader and hasattr(self._pack_loader, "get_pack_path"):
            base = Path(self._pack_loader.get_pack_path(pack_id))  # type: ignore[union-attr]
            filepath = base / chosen

        return SelectionResult(
            filepath=filepath,
            category=category,
            pack_id=pack_id,
            selection_layer=PackSelectionLayer.SESSION_OVERRIDE,
        )

    # ── History ──────────────────────────────────────────────────────────

    @property
    def playback_history(self) -> tuple[PlaybackRecord, ...]:
        return tuple(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    def get_last_played(self, category: CespCategory) -> PlaybackRecord | None:
        for record in reversed(self._history):
            if record.category == category:
                return record
        return None
