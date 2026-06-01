"""Stagnation detection and re-discussion triggers.

Monitors team activity and hypothesis age to detect stagnation.
When teams or hypotheses have been inactive too long, triggers
re-discussion or re-evaluation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
class StagnationLevel(str, Enum):
    """Severity of detected stagnation."""
    NONE = "none"
    WARNING = "warning"      # Approaching threshold
    STAGNANT = "stagnant"    # Past threshold, needs attention
    CRITICAL = "critical"    # Severely overdue, requires intervention


@dataclass
class ActivityRecord:
    """Timestamped record of team activity."""
    team_id: str
    action: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class StagnationStatus:
    """Current stagnation assessment for a team or hypothesis."""

    target_id: str
    level: StagnationLevel = StagnationLevel.NONE
    idle_s: float = 0.0
    last_activity: float = 0.0
    warning_threshold_s: float = 1800.0   # 30 min
    stagnant_threshold_s: float = 3600.0  # 1 hour
    critical_threshold_s: float = 7200.0  # 2 hours

    @property
    def is_stagnant(self) -> bool:
        return self.level in (StagnationLevel.STAGNANT, StagnationLevel.CRITICAL)

    @property
    def needs_attention(self) -> bool:
        return self.level != StagnationLevel.NONE


@dataclass
class RediscussionTrigger:
    """A trigger to re-open or re-discuss a stalled topic."""

    trigger_id: str
    target_id: str                     # team or thread ID
    reason: str
    level: StagnationLevel
    suggested_action: str = ""
    created_at: float = field(default_factory=time.time)
    acknowledged: bool = False


class StagnationDetector:
    """Detects team/hypothesis stagnation and generates re-discussion triggers.

    Tracks per-team activity timestamps and compares against configurable
    thresholds. When stagnation is detected, generates actionable triggers
    for automatic or manual intervention.

    Usage::

        detector = StagnationDetector()
        detector.record_activity("team-1", "hypothesis_proposed")
        status = detector.check("team-1")
        if status.is_stagnant:
            trigger = detector.create_trigger("team-1", "No activity for 2 hours")
    """

    def __init__(
        self,
        *,
        warning_threshold_s: float = 1800.0,
        stagnant_threshold_s: float = 3600.0,
        critical_threshold_s: float = 7200.0,
    ) -> None:
        self.warning_threshold_s = warning_threshold_s
        self.stagnant_threshold_s = stagnant_threshold_s
        self.critical_threshold_s = critical_threshold_s

        self._activities: dict[str, list[ActivityRecord]] = {}
        self._last_activity: dict[str, float] = {}
        self._triggers: list[RediscussionTrigger] = []

    def record_activity(self, target_id: str, action: str) -> None:
        """Record a timestamped activity for a target."""
        now = time.time()
        record = ActivityRecord(team_id=target_id, action=action, timestamp=now)
        if target_id not in self._activities:
            self._activities[target_id] = []
        self._activities[target_id].append(record)
        self._last_activity[target_id] = now

    def check(self, target_id: str) -> StagnationStatus:
        """Assess stagnation level for a target."""
        last = self._last_activity.get(target_id, 0.0)
        now = time.time()
        idle_s = now - last if last > 0 else 0.0

        if last == 0.0:
            level = StagnationLevel.NONE
        elif idle_s >= self.critical_threshold_s:
            level = StagnationLevel.CRITICAL
        elif idle_s >= self.stagnant_threshold_s:
            level = StagnationLevel.STAGNANT
        elif idle_s >= self.warning_threshold_s:
            level = StagnationLevel.WARNING
        else:
            level = StagnationLevel.NONE

        return StagnationStatus(
            target_id=target_id,
            level=level,
            idle_s=idle_s,
            last_activity=last,
            warning_threshold_s=self.warning_threshold_s,
            stagnant_threshold_s=self.stagnant_threshold_s,
            critical_threshold_s=self.critical_threshold_s,
        )

    def check_all(self) -> dict[str, StagnationStatus]:
        """Check stagnation for all tracked targets."""
        return {tid: self.check(tid) for tid in self._last_activity}

    def stagnant_targets(self) -> list[str]:
        """Return IDs of all stagnant targets."""
        return [
            tid for tid, status in self.check_all().items()
            if status.is_stagnant
        ]

    def create_trigger(
        self,
        target_id: str,
        reason: str,
        *,
        suggested_action: str = "",
    ) -> RediscussionTrigger:
        """Create a re-discussion trigger for a stagnant target."""
        status = self.check(target_id)
        trigger = RediscussionTrigger(
            trigger_id=f"retrigger_{uuid.uuid4().hex[:12]}",
            target_id=target_id,
            reason=reason,
            level=status.level,
            suggested_action=suggested_action,
        )
        self._triggers.append(trigger)
        return trigger

    def acknowledge_trigger(self, trigger_id: str) -> bool:
        """Mark a trigger as acknowledged."""
        for t in self._triggers:
            if t.trigger_id == trigger_id:
                t.acknowledged = True
                return True
        return False

    def pending_triggers(self) -> list[RediscussionTrigger]:
        """Return all unacknowledged triggers."""
        return [t for t in self._triggers if not t.acknowledged]

    def reset_activity(self, target_id: str) -> None:
        """Clear activity history for a target."""
        self._activities.pop(target_id, None)
        self._last_activity.pop(target_id, None)

    def target_count(self) -> int:
        return len(self._last_activity)

    def total_activities(self) -> int:
        return sum(len(acts) for acts in self._activities.values())
