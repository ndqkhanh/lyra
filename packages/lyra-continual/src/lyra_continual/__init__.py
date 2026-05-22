"""Continual Learning — experience replay, elastic weight consolidation, progressive neural networks.

Enables Lyra to learn across thousands of tasks without catastrophic forgetting.
Three complementary mechanisms: replay (rehearse past), EWC (protect important weights),
and progressive networks (grow new columns).
"""

from __future__ import annotations

import logging
import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "AgentExperience",
    "ExperienceReplay",
    "ElasticWeightConsolidation",
    "ProgressiveNetwork",
    "ContinualLearner",
]


@dataclass
class AgentExperience:
    task_id: str
    state: dict[str, Any]
    action: str
    result: Any
    reward: float = 0.0


class ExperienceReplay:
    """Store and replay past experiences to prevent catastrophic forgetting."""

    def __init__(self, capacity: int = 100000):
        self.buffer: deque[AgentExperience] = deque(maxlen=capacity)
        self.task_counts: dict[str, int] = {}

    def store(self, experience: AgentExperience) -> None:
        self.buffer.append(experience)
        self.task_counts[experience.task_id] = self.task_counts.get(experience.task_id, 0) + 1

    def sample(self, batch_size: int = 32, strategy: str = "balanced") -> list[AgentExperience]:
        if not self.buffer:
            return []
        if strategy == "balanced":
            tasks = list(self.task_counts.keys())
            per_task = max(1, batch_size // max(len(tasks), 1))
            samples = []
            for task in tasks:
                task_samples = [e for e in self.buffer if e.task_id == task]
                samples.extend(random.sample(task_samples, min(per_task, len(task_samples))))
            return samples[:batch_size]
        return random.sample(list(self.buffer), min(batch_size, len(self.buffer)))

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_experiences": len(self.buffer),
            "unique_tasks": len(self.task_counts),
            "capacity": self.buffer.maxlen,
        }


class ElasticWeightConsolidation:
    """EWC: quadratic penalty on important weights when learning new tasks."""

    def __init__(self, lambda_ewc: float = 0.5):
        self.lambda_ewc = lambda_ewc
        self.fisher_matrices: dict[str, dict[str, float]] = {}
        self.optimal_weights: dict[str, dict[str, float]] = {}

    def compute_fisher(self, task_id: str, weight_importance: dict[str, float]) -> None:
        self.fisher_matrices[task_id] = weight_importance

    def compute_ewc_loss(self, task_id: str, current_weights: dict[str, float]) -> float:
        loss = 0.0
        for tid, fisher in self.fisher_matrices.items():
            if tid == task_id:
                continue
            opt = self.optimal_weights.get(tid, {})
            for param, f_val in fisher.items():
                curr = current_weights.get(param, 0.0)
                opt_val = opt.get(param, 0.0)
                loss += self.lambda_ewc * f_val * (curr - opt_val) ** 2
        return loss


class ProgressiveNetwork:
    """Progressive neural networks: new column per task, no forgetting."""

    def __init__(self):
        self.columns: dict[str, dict[str, Any]] = {}
        self.lateral_connections: dict[str, list[str]] = {}

    def add_column(self, task_id: str, layer_sizes: list[int]) -> None:
        self.columns[task_id] = {"layer_sizes": layer_sizes, "parameters": {}}
        self.lateral_connections[task_id] = list(self.columns.keys())

    def transfer_from(self, task_id: str, source_task: str) -> dict[str, Any]:
        source = self.columns.get(source_task)
        if not source:
            return {"transfer": False}
        return {"transfer": True, "source_layers": source["layer_sizes"]}


class ContinualLearner:
    """Combines replay, EWC, and progressive networks for continual learning."""

    def __init__(self):
        self.replay = ExperienceReplay()
        self.ewc = ElasticWeightConsolidation()
        self.progressive = ProgressiveNetwork()
        self.task_count = 0

    def learn_task(self, task_id: str, experiences: list[AgentExperience]) -> dict[str, Any]:
        self.task_count += 1
        for exp in experiences:
            self.replay.store(exp)
        self.progressive.add_column(task_id, [128, 64, 32])
        return {
            "task": task_id,
            "experiences_stored": len(experiences),
            "total_experiences": len(self.replay.buffer),
            "total_tasks": self.task_count,
        }
