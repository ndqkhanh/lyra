"""Stats command — agent performance and usage statistics display.

Collects and displays aggregated statistics about agent activity,
token usage, task completion rates, and session metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class SessionStats:
    session_id: str
    tasks_completed: int
    tasks_failed: int
    tokens_used: int
    tools_called: int
    duration_sec: float
    model_switches: int
    mode_transitions: int

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 100.0
        return round(self.tasks_completed / total * 100, 1)

    @property
    def tokens_per_minute(self) -> float:
        minutes = self.duration_sec / 60.0
        if minutes == 0:
            return 0.0
        return round(self.tokens_used / minutes, 1)


@dataclass(frozen=True)
class AggregateStats:
    total_sessions: int
    total_tasks: int
    total_tokens: int
    total_duration_sec: float
    overall_success_rate: float
    avg_tokens_per_task: float
    peak_parallel_tasks: int
    generated_at: float


class StatsCollector:
    """Collects and aggregates agent performance statistics.

    Tracks per-session metrics and computes aggregate statistics
    across all sessions for trend analysis and reporting.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionStats] = {}
        self._current: dict[str, dict] = {}

    def start_session(self, session_id: str) -> None:
        self._current[session_id] = {
            "start_time": time.time(),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tokens_used": 0,
            "tools_called": 0,
            "model_switches": 0,
            "mode_transitions": 0,
        }

    def record_task(self, session_id: str, success: bool) -> None:
        if session_id not in self._current:
            self.start_session(session_id)
        key = "tasks_completed" if success else "tasks_failed"
        self._current[session_id][key] += 1

    def record_tokens(self, session_id: str, count: int) -> None:
        if session_id not in self._current:
            self.start_session(session_id)
        self._current[session_id]["tokens_used"] += count

    def record_tool_call(self, session_id: str) -> None:
        if session_id not in self._current:
            self.start_session(session_id)
        self._current[session_id]["tools_called"] += 1

    def record_model_switch(self, session_id: str) -> None:
        if session_id not in self._current:
            self.start_session(session_id)
        self._current[session_id]["model_switches"] += 1

    def record_mode_transition(self, session_id: str) -> None:
        if session_id not in self._current:
            self.start_session(session_id)
        self._current[session_id]["mode_transitions"] += 1

    def end_session(self, session_id: str) -> SessionStats | None:
        current = self._current.pop(session_id, None)
        if current is None:
            return None

        stats = SessionStats(
            session_id=session_id,
            tasks_completed=current["tasks_completed"],
            tasks_failed=current["tasks_failed"],
            tokens_used=current["tokens_used"],
            tools_called=current["tools_called"],
            duration_sec=round(time.time() - current["start_time"], 1),
            model_switches=current["model_switches"],
            mode_transitions=current["mode_transitions"],
        )
        self._sessions[session_id] = stats
        return stats

    def aggregate(self) -> AggregateStats:
        sessions = list(self._sessions.values())
        if not sessions:
            return AggregateStats(0, 0, 0, 0.0, 100.0, 0.0, 0, time.time())

        return AggregateStats(
            total_sessions=len(sessions),
            total_tasks=sum(s.tasks_completed + s.tasks_failed for s in sessions),
            total_tokens=sum(s.tokens_used for s in sessions),
            total_duration_sec=round(sum(s.duration_sec for s in sessions), 1),
            overall_success_rate=round(
                sum(s.tasks_completed for s in sessions)
                / max(sum(s.tasks_completed + s.tasks_failed for s in sessions), 1)
                * 100,
                1,
            ),
            avg_tokens_per_task=round(
                sum(s.tokens_used for s in sessions)
                / max(sum(s.tasks_completed + s.tasks_failed for s in sessions), 1),
                1,
            ),
            peak_parallel_tasks=0,
            generated_at=time.time(),
        )

    def get_session(self, session_id: str) -> SessionStats | None:
        return self._sessions.get(session_id)

    def stats(self) -> dict:
        agg = self.aggregate()
        return {
            "total_sessions": agg.total_sessions,
            "total_tasks": agg.total_tasks,
            "total_tokens": agg.total_tokens,
            "overall_success_rate": agg.overall_success_rate,
            "active_sessions": len(self._current),
        }
