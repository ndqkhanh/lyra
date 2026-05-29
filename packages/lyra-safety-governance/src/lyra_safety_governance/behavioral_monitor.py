from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AnomalyAction(Enum):
    LOG = "log"
    NOTIFY = "notify"
    THROTTLE = "throttle"
    BLOCK = "block"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class BehaviorEvent:
    event_id: str
    agent_id: str
    event_type: str
    details: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    severity: float = 0.5


@dataclass(frozen=True)
class BehaviorProfile:
    agent_id: str
    normal_patterns: tuple[str, ...] = ()
    anomaly_threshold: float = 0.7
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AnomalyScore:
    agent_id: str
    score: float
    contributing_events: tuple[BehaviorEvent, ...] = ()
    recommendation: AnomalyAction = AnomalyAction.LOG


@dataclass(frozen=True)
class BehavioralConfig:
    baseline_window: int = 3600
    anomaly_threshold: float = 0.7
    check_interval: int = 300


class BehaviorBaseline:
    """Statistical baseline of normal behavior per agent.

    Tracks event frequency per type, hourly distribution, and action type diversity.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._event_counts: dict[str, int] = {}
        self._hour_distribution: dict[int, int] = {}
        self._total_events = 0
        self._output_sizes: list[int] = []

    def record_event(self, event: BehaviorEvent) -> None:
        self._event_counts[event.event_type] = self._event_counts.get(event.event_type, 0) + 1
        hour = event.timestamp.hour
        self._hour_distribution[hour] = self._hour_distribution.get(hour, 0) + 1
        self._total_events += 1

    @property
    def known_event_types(self) -> set[str]:
        return set(self._event_counts.keys())

    @property
    def total_events(self) -> int:
        return self._total_events

    @property
    def dominant_hours(self) -> set[int]:
        """Return hours with above-average activity."""
        if not self._hour_distribution:
            return set()
        mean = statistics.mean(self._hour_distribution.values()) if self._hour_distribution else 0
        return {h for h, count in self._hour_distribution.items() if count > mean}

    def get_event_rate(self, event_type: str) -> float:
        return self._event_counts.get(event_type, 0) / max(self._total_events, 1)


class BehavioralMonitor:
    """Layer 3: Runtime behavior anomaly detection.

    Observes agent actions, builds behavioral baselines, and detects
    anomalous patterns indicating potential safety violations.
    """

    def __init__(self, config: BehavioralConfig | None = None) -> None:
        self._config = config or BehavioralConfig()
        self._events: dict[str, list[BehaviorEvent]] = {}
        self._baselines: dict[str, BehaviorBaseline] = {}
        self._next_event_id = 0

    @property
    def config(self) -> BehavioralConfig:
        return self._config

    def observe_event(
        self, agent_id: str, event_type: str, details: str = "", severity: float = 0.5
    ) -> BehaviorEvent:
        """Record a behavior event for an agent and update baselines."""
        event_id = f"evt-{agent_id}-{self._next_event_id}"
        self._next_event_id += 1

        event = BehaviorEvent(
            event_id=event_id,
            agent_id=agent_id,
            event_type=event_type,
            details=details,
            severity=severity,
        )

        if agent_id not in self._events:
            self._events[agent_id] = []
        self._events[agent_id].append(event)

        if agent_id not in self._baselines:
            self._baselines[agent_id] = BehaviorBaseline(agent_id)
        self._baselines[agent_id].record_event(event)

        return event

    def get_events(self, agent_id: str) -> tuple[BehaviorEvent, ...]:
        return tuple(self._events.get(agent_id, []))

    def detect_anomalies(self, agent_id: str) -> tuple[AnomalyScore, ...]:
        """Detect anomalies by comparing recent events to the agent's baseline."""
        scores: list[AnomalyScore] = []

        baseline = self._baselines.get(agent_id)
        if baseline is None or baseline.total_events < 2:
            return ()

        events = self._events.get(agent_id, [])
        if not events:
            return ()

        recent = events[-5:] if len(events) >= 5 else events

        # Anomaly: unusual hour activity
        unusual_hour_score = self._check_unusual_hour(agent_id, recent, baseline)
        if unusual_hour_score is not None:
            scores.append(unusual_hour_score)

        # Anomaly: excessive rate
        rate_score = self._check_excessive_rate(agent_id, recent, baseline)
        if rate_score is not None:
            scores.append(rate_score)

        # Anomaly: new action types
        new_action_score = self._check_new_action_types(agent_id, recent, baseline)
        if new_action_score is not None:
            scores.append(new_action_score)

        # Anomaly: access pattern deviation
        pattern_score = self._check_access_pattern_deviation(agent_id, recent, baseline)
        if pattern_score is not None:
            scores.append(pattern_score)

        return tuple(scores)

    def _check_unusual_hour(
        self,
        agent_id: str,
        recent: list[BehaviorEvent],
        baseline: BehaviorBaseline,
    ) -> AnomalyScore | None:
        """Detect activity during hours the agent is not typically active."""
        dominant = baseline.dominant_hours
        if not dominant:
            return None

        unusual_count = sum(1 for e in recent if e.timestamp.hour not in dominant)
        if unusual_count == 0:
            return None

        ratio = unusual_count / len(recent)
        if ratio < 0.5:
            return None

        return AnomalyScore(
            agent_id=agent_id,
            score=ratio * 0.8,
            contributing_events=tuple(e for e in recent if e.timestamp.hour not in dominant),
            recommendation=AnomalyAction.NOTIFY if ratio > 0.8 else AnomalyAction.LOG,
        )

    def _check_excessive_rate(
        self,
        agent_id: str,
        recent: list[BehaviorEvent],
        baseline: BehaviorBaseline,
    ) -> AnomalyScore | None:
        """Detect an unusually high rate of events in a short time window."""
        if len(recent) < 3:
            return None

        baseline_rate = baseline.total_events / max(self._config.baseline_window, 1)
        recent_window = 60.0
        recent_rate = len(recent) / recent_window

        if recent_rate <= baseline_rate * 3:
            return None

        ratio = recent_rate / max(baseline_rate, 0.001)

        return AnomalyScore(
            agent_id=agent_id,
            score=min(ratio / 10, 0.95),
            contributing_events=tuple(recent),
            recommendation=(
                AnomalyAction.THROTTLE
                if ratio > 20
                else AnomalyAction.NOTIFY if ratio > 10 else AnomalyAction.LOG
            ),
        )

    def _check_new_action_types(
        self,
        agent_id: str,
        recent: list[BehaviorEvent],
        baseline: BehaviorBaseline,
    ) -> AnomalyScore | None:
        """Detect event types the agent has rarely or never performed before."""
        known = baseline.known_event_types
        if not known:
            return None

        new_types: set[str] = set()
        for event in recent:
            if event.event_type not in known and event.event_type not in new_types:
                new_types.add(event.event_type)

        if not new_types:
            return None

        new_events = [e for e in recent if e.event_type in new_types]
        return AnomalyScore(
            agent_id=agent_id,
            score=min(len(new_types) * 0.25, 0.9),
            contributing_events=tuple(new_events),
            recommendation=AnomalyAction.NOTIFY if len(new_types) >= 2 else AnomalyAction.LOG,
        )

    def _check_access_pattern_deviation(
        self,
        agent_id: str,
        recent: list[BehaviorEvent],
        baseline: BehaviorBaseline,
    ) -> AnomalyScore | None:
        """Detect deviations from learned access patterns."""
        if baseline.total_events < 5:
            return None

        recent_types = {e.event_type for e in recent}
        expected = baseline.known_event_types

        if recent_types == expected:
            return None

        deviation_ratio = len(recent_types - expected) / max(len(recent_types), 1)
        if deviation_ratio < 0.3:
            return None

        return AnomalyScore(
            agent_id=agent_id,
            score=deviation_ratio * 0.7,
            contributing_events=tuple(e for e in recent if e.event_type not in expected),
            recommendation=(
                AnomalyAction.ESCALATE if deviation_ratio > 0.7 else AnomalyAction.NOTIFY
            ),
        )
