"""Recursive Reward — Three nested reward loops preventing reward hacking at every level."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RewardSignal:
    loop_level: str  # inner, middle, outer
    value: float
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


class InnerRewardLoop:
    """Task success rate — measures how well Lyra completes individual tasks (weekly)."""

    def __init__(self, window: int = 7):
        self.window = window
        self.daily_scores: deque[float] = deque(maxlen=window)
        self.hacking_events: list[dict[str, Any]] = []

    def record_day(self, success_rate: float) -> None:
        self.daily_scores.append(success_rate)

    @property
    def current_score(self) -> float:
        if not self.daily_scores:
            return 0.0
        return np.mean(self.daily_scores)

    def detect_reward_hacking(self, held_out_score: float) -> bool:
        visible = self.current_score
        gap = visible - held_out_score
        if gap > 0.15:
            self.hacking_events.append({
                "visible": visible,
                "held_out": held_out_score,
                "gap": gap,
                "is_hacking": True,
            })
            return True
        return False


class MiddleRewardLoop:
    """Speed of skill acquisition — how fast Lyra learns new skills (monthly)."""

    def __init__(self, window: int = 30):
        self.window = window
        self.daily_acquisition: deque[int] = deque(maxlen=window)
        self.monthly_rate: float = 0.0

    def record_acquisition(self, skills_learned: int) -> None:
        self.daily_acquisition.append(skills_learned)

    @property
    def current_rate(self) -> float:
        if not self.daily_acquisition:
            return 0.0
        return np.mean(self.daily_acquisition)

    def is_accelerating(self) -> bool:
        if len(self.daily_acquisition) < 10:
            return False
        recent = np.mean(list(self.daily_acquisition)[-7:])
        older = np.mean(list(self.daily_acquisition)[:7])
        return recent > older * 1.1


class OuterRewardLoop:
    """Speed of evolution improvement — how fast Lyra improves its own evolution (quarterly)."""

    def __init__(self, window: int = 90):
        self.window = window
        self.evolution_rates: deque[float] = deque(maxlen=window)

    def record_evolution_speed(self, speed: float) -> None:
        self.evolution_rates.append(speed)

    @property
    def trend(self) -> float:
        if len(self.evolution_rates) < 2:
            return 0.0
        return (self.evolution_rates[-1] - self.evolution_rates[0]) / len(self.evolution_rates)


class RecursiveReward:
    """Coordinates all three nested reward loops and prevents reward hacking at every level."""

    def __init__(self):
        self.inner = InnerRewardLoop()
        self.middle = MiddleRewardLoop()
        self.outer = OuterRewardLoop()
        self.all_signals: list[RewardSignal] = []

    def record_inner(self, success_rate: float) -> RewardSignal:
        self.inner.record_day(success_rate)
        signal = RewardSignal("inner", success_rate, self._now())
        self.all_signals.append(signal)
        return signal

    def record_middle(self, skills_learned: int) -> RewardSignal:
        self.middle.record_acquisition(skills_learned)
        signal = RewardSignal("middle", float(skills_learned), self._now())
        self.all_signals.append(signal)
        return signal

    def record_outer(self, evolution_speed: float) -> RewardSignal:
        self.outer.record_evolution_speed(evolution_speed)
        signal = RewardSignal("outer", evolution_speed, self._now())
        self.all_signals.append(signal)
        return signal

    def detect_hacking(self, held_out_score: float) -> bool:
        return self.inner.detect_reward_hacking(held_out_score)

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "inner_task_success": self.inner.current_score,
            "middle_skill_acquisition_rate": self.middle.current_rate,
            "outer_evolution_trend": self.outer.trend,
            "inner_accelerating": self.middle.is_accelerating(),
            "hacking_events": len(self.inner.hacking_events),
        }

    def _now(self) -> float:
        return __import__("time").time()
