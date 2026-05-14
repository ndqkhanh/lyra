"""SkillOS curator — Phase I of the Lyra skill-curation plan.

Trainable curator that learns INSERT / UPDATE / DELETE decisions from
task outcomes, outperforming both human curation and direct use of a
much larger uncurated model.

Key finding from arXiv:2605.06614:
- A trained 8B Curator outperforms using Gemini-2.5-Pro directly
- +9.8% improvement, 6% fewer interaction steps
- Trained curator transfers across executor models and task domains

This module provides the structural layer: action types, composite
reward computation, and the curator protocol. The RL training loop
that updates the curator weights lives in the experiment harness.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol


__all__ = [
    "CurationAction",
    "CurationDecision",
    "CurationReward",
    "CurationRewardConfig",
    "SkillOSCurator",
    "TaskGroup",
]


class CurationAction(str, Enum):
    """Lifecycle operations available to the SkillOS curator."""
    INSERT = "insert"       # add new skill to repo
    UPDATE = "update"       # revise existing skill content
    DELETE = "delete"       # remove stale/harmful skill
    NOOP = "noop"           # no change needed


@dataclass
class CurationDecision:
    """One curation action with rationale."""

    action: CurationAction
    skill_id: str
    content: str = ""           # new/updated skill content (empty for DELETE/NOOP)
    rationale: str = ""
    confidence: float = 1.0


@dataclass(frozen=True)
class CurationRewardConfig:
    """Weights for the composite curation reward signal."""

    task_outcome_weight: float = 0.50       # downstream task success rate
    operation_validity_weight: float = 0.20  # fraction of valid curator ops
    content_quality_weight: float = 0.20    # external judge score [0,1]
    compression_weight: float = 0.10        # penalty for storing raw trajectories


@dataclass
class CurationReward:
    """Composite reward computed after one curation episode."""

    task_outcome: float = 0.0           # [0, 1]
    operation_validity: float = 0.0     # [0, 1]
    content_quality: float = 0.0        # [0, 1]
    compression_ratio: float = 0.0      # higher = more compressed = better

    def total(self, config: Optional[CurationRewardConfig] = None) -> float:
        cfg = config or CurationRewardConfig()
        return (
            cfg.task_outcome_weight * self.task_outcome
            + cfg.operation_validity_weight * self.operation_validity
            + cfg.content_quality_weight * self.content_quality
            + cfg.compression_weight * min(self.compression_ratio, 1.0)
        )


@dataclass
class TaskGroup:
    """Group of related tasks used for dense training signal.

    Earlier tasks update the SkillRepo; later tasks evaluate updates.
    This resolves the sparse reward problem for complex curation ops.
    """

    group_id: str
    training_tasks: list[str] = field(default_factory=list)   # update SkillRepo
    evaluation_tasks: list[str] = field(default_factory=list)  # measure effect


class SkillExecutor(Protocol):
    """Runs tasks against the current skill repo; returns success rate."""
    def evaluate(self, tasks: list[str], skill_ids: list[str]) -> float: ...


class SkillOSCurator:
    """Curator that tracks decisions and reward signals for RL training.

    Usage::

        curator = SkillOSCurator()
        decision = CurationDecision(CurationAction.INSERT, "new-skill", content="...")
        curator.submit(decision)
        # ... run executor ...
        reward = CurationReward(task_outcome=0.8, operation_validity=1.0,
                                content_quality=0.7, compression_ratio=0.6)
        curator.record_reward(decision, reward)
        print(curator.mean_reward())
    """

    def __init__(self, config: Optional[CurationRewardConfig] = None) -> None:
        self._config = config or CurationRewardConfig()
        self._decisions: list[CurationDecision] = []
        self._rewards: list[tuple[CurationDecision, CurationReward]] = []
        self._skill_repo: dict[str, str] = {}   # skill_id → content

    # ---------------------------------------------------------------- #
    # Curation operations                                                #
    # ---------------------------------------------------------------- #

    def submit(self, decision: CurationDecision) -> bool:
        """Apply a curation decision to the in-memory skill repo."""
        self._decisions.append(decision)
        if decision.action == CurationAction.INSERT:
            if decision.skill_id in self._skill_repo:
                return False   # collision
            self._skill_repo[decision.skill_id] = decision.content
        elif decision.action == CurationAction.UPDATE:
            if decision.skill_id not in self._skill_repo:
                return False   # unknown skill
            self._skill_repo[decision.skill_id] = decision.content
        elif decision.action == CurationAction.DELETE:
            self._skill_repo.pop(decision.skill_id, None)
        return True

    def record_reward(
        self, decision: CurationDecision, reward: CurationReward
    ) -> None:
        self._rewards.append((decision, reward))

    # ---------------------------------------------------------------- #
    # Metrics                                                            #
    # ---------------------------------------------------------------- #

    def mean_reward(self) -> float:
        if not self._rewards:
            return 0.0
        return sum(r.total(self._config) for _, r in self._rewards) / len(self._rewards)

    def action_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {a.value: 0 for a in CurationAction}
        for d in self._decisions:
            dist[d.action.value] += 1
        return dist

    @property
    def skill_count(self) -> int:
        return len(self._skill_repo)

    def list_skills(self) -> list[str]:
        return list(self._skill_repo.keys())

    def get_skill(self, skill_id: str) -> Optional[str]:
        return self._skill_repo.get(skill_id)
