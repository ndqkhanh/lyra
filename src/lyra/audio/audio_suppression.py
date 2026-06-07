"""Plan 8 Part 5: Audio Suppression — silent hours, meeting detection, spam protection.

Configurable suppression rules for when audio playback should be
automatically muted or deferred.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum


class SuppressionReason(Enum):
    """Why audio playback was suppressed."""

    NONE = "none"
    SILENT_HOURS = "silent_hours"
    MEETING_DETECTED = "meeting_detected"
    SPAM_THROTTLE = "spam_throttle"
    USER_ANNOYED = "user_annoyed"
    HEADPHONES_ONLY = "headphones_only"
    MANUAL_MUTE = "manual_mute"


@dataclass(frozen=True)
class SilentHours:
    """A silent time window.

    Attributes:
        start_hhmm: Start time in "HH:MM" format (inclusive).
        end_hhmm: End time in "HH:MM" format (exclusive).
    """

    start_hhmm: str  # e.g. "22:00"
    end_hhmm: str  # e.g. "07:00"

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        for val in (self.start_hhmm, self.end_hhmm):
            parts = val.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid time format: {val}, expected HH:MM")
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError(f"Invalid time: {val}")

    def contains(self, hour: int, minute: int) -> bool:
        """Check if the given time falls within this silent window."""
        sh, sm = map(int, self.start_hhmm.split(":"))
        eh, em = map(int, self.end_hhmm.split(":"))

        start_minutes = sh * 60 + sm
        end_minutes = eh * 60 + em
        current_minutes = hour * 60 + minute

        if start_minutes <= end_minutes:
            # Same-day window (e.g. 01:00 - 05:00)
            return start_minutes <= current_minutes < end_minutes
        else:
            # Overnight window (e.g. 22:00 - 07:00)
            return current_minutes >= start_minutes or current_minutes < end_minutes


@dataclass(frozen=True)
class SuppressionConfig:
    """Audio suppression configuration.

    Attributes:
        silent_hours: List of silent time windows.
        meeting_detect: Whether to attempt meeting detection.
        suppress_when_tab_focused: Mute when terminal has focus.
        headphones_only: Only play sound through headphones.
        annoyed_threshold: Number of rapid plays before treating as spam.
        annoyed_window_seconds: Time window for spam detection.
    """

    silent_hours: tuple[SilentHours, ...] = ()
    meeting_detect: bool = True
    suppress_when_tab_focused: bool = False
    headphones_only: bool = False
    annoyed_threshold: int = 5
    annoyed_window_seconds: float = 60.0


@dataclass(frozen=True)
class SuppressionResult:
    """Result of a suppression check.

    Attributes:
        suppressed: Whether playback should be suppressed.
        reason: Why it was suppressed (or NONE if allowed).
        detail: Human-readable explanation.
    """

    suppressed: bool
    reason: SuppressionReason
    detail: str = ""


class AudioSuppression:
    """Audio suppression manager.

    Enforces silent hours, spam throttling, and annoyed-user detection
    to prevent audio from becoming disruptive.

    Usage::

        suppression = AudioSuppression(config)
        result = suppression.check("task.complete")
        if not result.suppressed:
            player.play(sound)
    """

    def __init__(self, config: SuppressionConfig | None = None) -> None:
        self._config = config or SuppressionConfig()
        self._play_timestamps: deque[float] = deque()
        self._is_muted = False
        self._is_meeting = False
        self._headphones_connected = True

    # ── Configuration ─────────────────────────────────────────────────────

    @property
    def config(self) -> SuppressionConfig:
        return self._config

    def update_config(self, config: SuppressionConfig) -> None:
        self._config = config

    def set_muted(self, muted: bool) -> None:
        """Manually mute/unmute audio."""
        self._is_muted = muted

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_meeting_state(self, in_meeting: bool) -> None:
        """Update meeting detection state."""
        self._is_meeting = in_meeting

    def set_headphones_state(self, connected: bool) -> None:
        """Update headphones connection state."""
        self._headphones_connected = connected

    # ── Check ─────────────────────────────────────────────────────────────

    def check(self, _category: str = "") -> SuppressionResult:
        """Check whether audio playback should be suppressed.

        Checks run in order: manual mute → silent hours → meeting →
        headphones requirement → spam/annoyed threshold.
        """
        # Manual mute
        if self._is_muted:
            return SuppressionResult(
                suppressed=True,
                reason=SuppressionReason.MANUAL_MUTE,
                detail="Audio is manually muted",
            )

        # Silent hours
        now = time.localtime()
        for window in self._config.silent_hours:
            if window.contains(now.tm_hour, now.tm_min):
                return SuppressionResult(
                    suppressed=True,
                    reason=SuppressionReason.SILENT_HOURS,
                    detail=f"Silent hours: {window.start_hhmm}-{window.end_hhmm}",
                )

        # Meeting detection
        if self._config.meeting_detect and self._is_meeting:
            return SuppressionResult(
                suppressed=True,
                reason=SuppressionReason.MEETING_DETECTED,
                detail="Meeting in progress",
            )

        # Headphones only
        if self._config.headphones_only and not self._headphones_connected:
            return SuppressionResult(
                suppressed=True,
                reason=SuppressionReason.HEADPHONES_ONLY,
                detail="Headphones not connected",
            )

        # Spam / annoyed threshold
        if self._config.annoyed_threshold > 0:
            now_ts = time.time()
            cutoff = now_ts - self._config.annoyed_window_seconds

            # Prune old timestamps
            while self._play_timestamps and self._play_timestamps[0] < cutoff:
                self._play_timestamps.popleft()

            if len(self._play_timestamps) >= self._config.annoyed_threshold:
                return SuppressionResult(
                    suppressed=True,
                    reason=SuppressionReason.SPAM_THROTTLE,
                    detail=(
                        f"Annoyed threshold reached: {len(self._play_timestamps)} plays in "
                        f"{self._config.annoyed_window_seconds}s"
                    ),
                )

        return SuppressionResult(
            suppressed=False,
            reason=SuppressionReason.NONE,
            detail="Playback allowed",
        )

    def record_playback(self) -> None:
        """Record that a sound was played, for spam tracking."""
        self._play_timestamps.append(time.time())
        # Keep the deque bounded
        while len(self._play_timestamps) > self._config.annoyed_threshold * 2:
            self._play_timestamps.popleft()

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return suppression state for monitoring."""
        now_ts = time.time()
        cutoff = now_ts - self._config.annoyed_window_seconds
        recent_plays = sum(1 for t in self._play_timestamps if t >= cutoff)

        return {
            "is_muted": self._is_muted,
            "is_meeting": self._is_meeting,
            "headphones_connected": self._headphones_connected,
            "silent_hours_active": self._is_in_silent_hours(),
            "recent_play_count": recent_plays,
            "annoyed_threshold": self._config.annoyed_threshold,
            "spam_throttled": recent_plays >= self._config.annoyed_threshold,
        }

    def _is_in_silent_hours(self) -> bool:
        now = time.localtime()
        return any(w.contains(now.tm_hour, now.tm_min) for w in self._config.silent_hours)


# ── Factory ───────────────────────────────────────────────────────────────


def create_default_suppression() -> AudioSuppression:
    """Create suppression with default settings (Plan 8 config.json defaults)."""
    config = SuppressionConfig(
        silent_hours=(SilentHours(start_hhmm="22:00", end_hhmm="07:00"),),
        meeting_detect=True,
        suppress_when_tab_focused=False,
        headphones_only=False,
        annoyed_threshold=5,
        annoyed_window_seconds=60.0,
    )
    return AudioSuppression(config)
