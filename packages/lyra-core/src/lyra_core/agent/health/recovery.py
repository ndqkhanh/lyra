"""Recovery playbooks for known failure modes."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class PlaybookStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class PlaybookStep:
    order: int
    action: str
    description: str = ""
    verify_after: bool = True
    timeout_seconds: float = 30.0
    rollback_action: str = ""


@dataclass(frozen=True)
class RecoveryResult:
    playbook_id: str
    status: PlaybookStatus
    steps_completed: int
    total_steps: int
    error_message: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_success(self) -> bool:
        return self.status == PlaybookStatus.COMPLETED

    @property
    def progress_pct(self) -> float:
        if self.total_steps == 0:
            return 100.0
        return (self.steps_completed / self.total_steps) * 100.0


@dataclass(frozen=True)
class RecoveryPlaybook:
    id: str
    name: str
    anomaly_type: str
    signal_source: str
    steps: tuple[PlaybookStep, ...]
    description: str = ""
    max_retries: int = 2
    cooldown_seconds: float = 60.0

    @property
    def step_count(self) -> int:
        return len(self.steps)


@dataclass
class PlaybookRegistry:
    """Registry of recovery playbooks keyed by (anomaly_type, signal_source).

    Usage::

        registry = PlaybookRegistry()
        registry.register(RecoveryPlaybook(
            id="pb1", name="Error Rate Spike Recovery",
            anomaly_type="spike", signal_source="error_rate",
            steps=(PlaybookStep(order=1, action="throttle_requests"),),
        ))
        playbook = registry.find("spike", "error_rate")
    """

    _playbooks: dict[str, RecoveryPlaybook] = field(default_factory=dict)
    _history: list[RecoveryResult] = field(default_factory=list)
    _last_run: dict[str, float] = field(default_factory=dict)

    def register(self, playbook: RecoveryPlaybook) -> None:
        key = self._make_key(playbook.anomaly_type, playbook.signal_source)
        if key in self._playbooks:
            existing = self._playbooks[key]
            self._playbooks[key] = RecoveryPlaybook(
                id=playbook.id,
                name=playbook.name,
                anomaly_type=playbook.anomaly_type,
                signal_source=playbook.signal_source,
                steps=existing.steps + playbook.steps,
                description=playbook.description or existing.description,
                max_retries=playbook.max_retries,
                cooldown_seconds=playbook.cooldown_seconds,
            )
        else:
            self._playbooks[key] = playbook

    def find(self, anomaly_type: str, signal_source: str) -> RecoveryPlaybook | None:
        return self._playbooks.get(self._make_key(anomaly_type, signal_source))

    def can_run(self, playbook_id: str) -> bool:
        last = self._last_run.get(playbook_id)
        if last is None:
            return True
        playbook = self._get_by_id(playbook_id)
        if playbook is None:
            return True
        return (time.time() - last) >= playbook.cooldown_seconds

    def record_result(self, result: RecoveryResult) -> None:
        self._history.append(result)
        self._last_run[result.playbook_id] = result.timestamp

    def get_history(self, playbook_id: str | None = None) -> list[RecoveryResult]:
        if playbook_id is None:
            return list(self._history)
        return [r for r in self._history if r.playbook_id == playbook_id]

    def list_playbooks(self) -> list[RecoveryPlaybook]:
        return list(self._playbooks.values())

    def _get_by_id(self, playbook_id: str) -> RecoveryPlaybook | None:
        for pb in self._playbooks.values():
            if pb.id == playbook_id:
                return pb
        return None

    @staticmethod
    def _make_key(anomaly_type: str, signal_source: str) -> str:
        return f"{anomaly_type}:{signal_source}"

    @property
    def playbook_count(self) -> int:
        return len(self._playbooks)

    @property
    def history_count(self) -> int:
        return len(self._history)

    def clear(self) -> None:
        self._playbooks.clear()
        self._history.clear()
        self._last_run.clear()
