"""SkillExtractor — scan a trajectory corpus for repeating successful patterns.

The extractor groups trajectories by `task_signature` and looks for action
sequences that recur frequently across successful runs. Each recurring
sequence becomes a :class:`SkillCandidate` whose ``occurrence_count`` is the
number of source trajectories and ``success_rate`` is the fraction that
completed successfully.

Implementation is intentionally simple — pattern *templating* (mapping
action sequences to a generic skill) is a deeper task that production wires
through an LLM-side judge. The extractor here finds *exact action-sequence
repeats* among successful trajectories; LLM-driven generalization plugs in
via the ``name_generator`` callable.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from ..forensic import Trajectory, TrajectoryOutcome
from .types import SkillCandidate


_NameGenerator = Callable[[str, tuple[str, ...]], str]


def _default_name_generator(task_signature: str, action_template: tuple[str, ...]) -> str:
    """Default name: ``<task_signature>_<n_actions>step``."""
    return f"{task_signature}_{len(action_template)}step"


@dataclass
class SkillExtractor:
    """Extract :class:`SkillCandidate`s from a trajectory corpus.

    Pattern detection: action-sequence repeats grouped by task signature.
    A repeat must:
        - Appear in ≥ ``min_occurrences`` distinct trajectories.
        - Have a success rate ≥ ``min_success_rate`` across those trajectories.
        - Match the action template exactly (no fuzzy matching at this layer).

    >>> from harness_core.forensic import Trajectory, TrajectoryOutcome
    >>> from harness_core.orchestration import AgentDecision
    >>> def make(tid, task, actions, outcome):
    ...     decisions = tuple(AgentDecision(action=a, fingerprint=f"{tid}-{i}")
    ...                       for i, a in enumerate(actions))
    ...     return Trajectory(trajectory_id=tid, task_signature=task,
    ...                       decisions=decisions, outcome=outcome)
    >>> trajs = [
    ...     make("t1", "refactor", ["read", "edit", "test"], TrajectoryOutcome.SUCCESS),
    ...     make("t2", "refactor", ["read", "edit", "test"], TrajectoryOutcome.SUCCESS),
    ...     make("t3", "refactor", ["read", "edit", "test"], TrajectoryOutcome.SUCCESS),
    ... ]
    >>> extractor = SkillExtractor(min_occurrences=2)
    >>> candidates = extractor.extract(trajs)
    >>> len(candidates)
    1
    >>> candidates[0].action_template
    ('read', 'edit', 'test')
    """

    min_occurrences: int = 2
    min_success_rate: float = 0.7
    name_generator: _NameGenerator = field(default=_default_name_generator)

    def __post_init__(self) -> None:
        if self.min_occurrences < 2:
            raise ValueError(
                f"min_occurrences must be >= 2 to be a 'pattern', got {self.min_occurrences}"
            )
        if not 0.0 <= self.min_success_rate <= 1.0:
            raise ValueError(
                f"min_success_rate must be in [0, 1], got {self.min_success_rate}"
            )

    def extract(self, trajectories: Iterable[Trajectory]) -> list[SkillCandidate]:
        """Find recurring action templates among successful trajectories."""
        traj_list = list(trajectories)
        if not traj_list:
            return []

        # Group by (task_signature, action_template).
        # Each group: (count, success_count, source_trajectory_ids).
        groups: dict[tuple[str, tuple[str, ...]], list[Trajectory]] = {}
        for t in traj_list:
            template = t.action_sequence()
            if not template:
                continue  # empty trajectories don't form patterns
            key = (t.task_signature, template)
            groups.setdefault(key, []).append(t)

        candidates: list[SkillCandidate] = []
        for (task_sig, template), members in groups.items():
            if len(members) < self.min_occurrences:
                continue
            successful = [
                t for t in members if t.outcome == TrajectoryOutcome.SUCCESS
            ]
            success_rate = len(successful) / len(members)
            if success_rate < self.min_success_rate:
                continue
            name = self.name_generator(task_sig, template)
            candidates.append(SkillCandidate.create(
                name=name,
                task_signature_pattern=task_sig,
                action_template=template,
                source_trajectories=tuple(t.trajectory_id for t in members),
                occurrence_count=len(members),
                success_rate=success_rate,
            ))

        # Most-frequent first; tie-break by higher success rate.
        candidates.sort(
            key=lambda c: (-c.occurrence_count, -c.success_rate, c.name),
        )
        return candidates


__all__ = ["SkillExtractor"]
