"""Agent Experimentation Platform — A/B testing for agents.

Greenfield opportunity. This is where MLOps was in 2019 —
everyone needs it but nobody has built the standard.
Lyra owns this category.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "ExperimentStatus",
    "AgentConfig",
    "Metric",
    "AgentExperiment",
    "ExperimentRegistry",
]


class ExperimentStatus(Enum):
    DRAFT = auto()
    RUNNING = auto()
    COMPLETED = auto()
    PAUSED = auto()


@dataclass
class AgentConfig:
    id: str
    name: str
    model: str = ""
    temperature: float = 0.7
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)


@dataclass
class Metric:
    name: str
    higher_is_better: bool = True


@dataclass
class AgentExperiment:
    id: str
    name: str
    control_config: AgentConfig
    variant_config: AgentConfig
    traffic_split: float = 0.1
    metrics: list[Metric] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    control_results: list[float] = field(default_factory=list)
    variant_results: list[float] = field(default_factory=list)


class ExperimentRegistry:
    """Manages the lifecycle of agent experiments."""

    def __init__(self):
        self.experiments: dict[str, AgentExperiment] = {}
        self._counter = 0

    def create_experiment(
        self,
        name: str,
        control: AgentConfig,
        variant: AgentConfig,
        traffic_split: float = 0.1,
        metrics: list[Metric] | None = None,
    ) -> AgentExperiment:
        self._counter += 1
        exp = AgentExperiment(
            id=f"exp_{self._counter}",
            name=name,
            control_config=control,
            variant_config=variant,
            traffic_split=traffic_split,
            metrics=metrics or [Metric("success_rate")],
            status=ExperimentStatus.DRAFT,
        )
        self.experiments[exp.id] = exp
        return exp

    def start(self, experiment_id: str) -> bool:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return False
        exp.status = ExperimentStatus.RUNNING
        return True

    def pause(self, experiment_id: str) -> bool:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return False
        exp.status = ExperimentStatus.PAUSED
        return True

    def _should_route_to_variant(self, exp: AgentExperiment) -> bool:
        return random.random() < exp.traffic_split

    def record_result(self, experiment_id: str, score: float, is_variant: bool) -> None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return
        if is_variant:
            exp.variant_results.append(score)
        else:
            exp.control_results.append(score)

    def get_results(self, experiment_id: str) -> dict[str, Any] | None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None

        control_mean = self._mean(exp.control_results)
        variant_mean = self._mean(exp.variant_results)

        return {
            "experiment_id": exp.id,
            "name": exp.name,
            "status": exp.status.name,
            "control": {
                "count": len(exp.control_results),
                "mean": control_mean,
            },
            "variant": {
                "count": len(exp.variant_results),
                "mean": variant_mean,
            },
            "improvement": (variant_mean - control_mean) if control_mean is not None else None,
            "winner": (
                "variant"
                if variant_mean and control_mean and variant_mean > control_mean
                else "control"
            ),
        }

    def promote_variant(self, experiment_id: str) -> AgentConfig | None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None
        results = self.get_results(experiment_id)
        if results and results.get("winner") == "variant":
            exp.status = ExperimentStatus.COMPLETED
            return exp.variant_config
        return exp.control_config

    def _mean(self, values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "total": len(self.experiments),
            "running": sum(
                1 for e in self.experiments.values() if e.status == ExperimentStatus.RUNNING
            ),
            "completed": sum(
                1 for e in self.experiments.values() if e.status == ExperimentStatus.COMPLETED
            ),
        }
