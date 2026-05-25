"""RL-trained Skill Curator (SkillOS pattern).

Proposes and evaluates skill patches using a configurable exploration
strategy modelled on reinforcement-learning dynamics.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class CuratorAction(Enum):
    """Actions the RL curator can take on a skill."""

    PROPOSE = "propose"
    MODIFY = "modify"
    DEPRECATE = "deprecate"
    PROMOTE = "promote"
    MERGE = "merge"


@dataclass(frozen=True)
class SkillPatch:
    """A proposed change to a skill."""

    patch_id: str
    skill_name: str
    changes: str
    confidence: float
    source: str


@dataclass(frozen=True)
class CuratorState:
    """Current state of the curation system."""

    current_skills: tuple[str, ...]
    performance_history: tuple[float, ...]
    exploration_rate: float


@dataclass(frozen=True)
class CuratorConfig:
    """Configuration for the curation cycle."""

    exploration_rate: float = 0.1
    learning_rate: float = 0.01
    min_confidence: float = 0.7
    max_patches_per_cycle: int = 10


class RLCurator:
    """RL-inspired skill curator that proposes and evaluates patches."""

    def __init__(self, config: CuratorConfig | None = None) -> None:
        self._config = config or CuratorConfig()

    @property
    def config(self) -> CuratorConfig:
        return self._config

    def propose_patch(self, state: CuratorState) -> SkillPatch:
        """Propose an improvement to a skill based on current state."""
        return propose_patch(state, self._config)

    def evaluate_patch(
        self, patch: SkillPatch, held_out_tasks: Sequence[str]
    ) -> float:
        """Evaluate a skill patch against held-out tasks, returning a reward."""
        return evaluate_patch(patch, held_out_tasks)

    def run_curation_cycle(self) -> list[SkillPatch]:
        """Run one curation cycle and return the proposed patches."""
        return run_curation_cycle(self._config)


def propose_patch(
    state: CuratorState, config: CuratorConfig | None = None
) -> SkillPatch:
    """Propose a skill patch given the current curator state.

    Uses exploration_rate from the config to decide whether to explore
    (random action) or exploit (improve the lowest-performing skill).

    Args:
        state: current curator state including skills and performance history.
        config: curator configuration; uses defaults if not provided.

    Returns:
        A SkillPatch representing the proposed change.

    Raises:
        ValueError: if performance_history is empty and no skills exist.
    """
    cfg = config or CuratorConfig()
    if not state.current_skills:
        raise ValueError("Cannot propose a patch: no skills in state.")

    if not state.performance_history:
        raise ValueError(
            "Cannot propose a patch: no performance history available."
        )

    explore = random.random() < cfg.exploration_rate

    if explore:
        skill_name = random.choice(list(state.current_skills))
        action = random.choice(list(CuratorAction))
        changes = f"{action.value} skill '{skill_name}' (exploration)"
        confidence = random.uniform(0.3, 0.9)
    else:
        min_idx = min(
            range(len(state.performance_history)),
            key=lambda i: state.performance_history[i],
        )
        skill_name = state.current_skills[
            min_idx % len(state.current_skills)
        ]
        action = CuratorAction.MODIFY
        changes = (
            f"Improve skill '{skill_name}' lowest performance "
            f"({state.performance_history[min_idx]:.3f})"
        )
        confidence = min(
            cfg.min_confidence + random.uniform(0.0, 0.2), 1.0
        )

    return SkillPatch(
        patch_id=_generate_patch_id(skill_name, action),
        skill_name=skill_name,
        changes=changes,
        confidence=round(confidence, 4),
        source="rl_curator",
    )


def evaluate_patch(
    patch: SkillPatch, held_out_tasks: Sequence[str]
) -> float:
    """Evaluate a skill patch against held-out tasks.

    Returns a reward signal between 0.0 and 1.0 derived from the patch
    confidence and a simulated task-pass rate.

    Args:
        patch: the skill patch to evaluate.
        held_out_tasks: tasks used to evaluate the patch.

    Returns:
        A float reward between 0.0 and 1.0.
    """
    if not held_out_tasks:
        return 0.0

    task_pass_rate = sum(
        1 for _ in held_out_tasks if random.random() < 0.7
    ) / len(held_out_tasks)

    reward = 0.6 * patch.confidence + 0.4 * task_pass_rate
    return round(min(reward, 1.0), 4)


def run_curation_cycle(config: CuratorConfig | None = None) -> list[SkillPatch]:
    """Run one curation cycle, generating patches for the configured skills.

    Creates a default state with no skills and no history. This produces
    an empty patch list because there is nothing to curate.

    Args:
        config: curation configuration; uses defaults if not provided.

    Returns:
        A list of SkillPatch objects proposed during this cycle.
    """
    cfg = config or CuratorConfig()
    state = CuratorState(
        current_skills=("skill_a", "skill_b", "skill_c"),
        performance_history=(0.85, 0.42, 0.73),
        exploration_rate=cfg.exploration_rate,
    )

    patches: list[SkillPatch] = []
    for _ in range(cfg.max_patches_per_cycle):
        try:
            patch = propose_patch(state, cfg)
            patches.append(patch)
        except ValueError:
            break

        if random.random() < cfg.exploration_rate:
            state = CuratorState(
                current_skills=state.current_skills,
                performance_history=state.performance_history,
                exploration_rate=state.exploration_rate,
            )

    return patches


def _generate_patch_id(skill_name: str, action: CuratorAction) -> str:
    """Generate a unique patch identifier."""
    suffix = random.randint(1000, 9999)
    return f"{skill_name}_{action.value}_{suffix}"
