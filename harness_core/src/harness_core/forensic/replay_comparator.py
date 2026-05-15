"""Trajectory replay + similarity comparator for sabotage detection.

A trajectory is a sequence of (decision, side-effects, outcome) over a task.
Pure-function agents make trajectories *replayable*: replaying the same input
fingerprint reproduces the same decision. The comparator groups trajectories
by task signature and computes similarity; outliers (far from every past
trajectory on the same task) are sabotage-detection candidates.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from ..orchestration import AgentDecision, SideEffectRecord


class TrajectoryOutcome(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNCLEAR = "unclear"
    ROLLED_BACK = "rolled_back"  # user-initiated rollback


@dataclass(frozen=True)
class Trajectory:
    """One agent run: decisions + side-effects + outcome, keyed by task signature.

    ``task_signature`` is a coarse hash of the task (e.g. SWE-Bench instance id,
    incident-class id, research-question fingerprint). Comparator groups by
    signature; only trajectories on the same task are compared.
    """

    trajectory_id: str
    task_signature: str
    decisions: tuple[AgentDecision, ...] = ()
    side_effects: tuple[SideEffectRecord, ...] = ()
    outcome: TrajectoryOutcome = TrajectoryOutcome.UNCLEAR

    def action_sequence(self) -> tuple[str, ...]:
        """The sequence of decision actions ('tool_call', 'answer', etc.)."""
        return tuple(d.action for d in self.decisions)

    def fingerprint_set(self) -> frozenset[str]:
        """The set of decision fingerprints — coarser than the sequence."""
        return frozenset(d.fingerprint for d in self.decisions if d.fingerprint)

    def tool_signature_set(self) -> frozenset[str]:
        """The set of (tool_name, replayable-flag) pairs from side-effects."""
        return frozenset(
            f"{r.tool_name}:{r.is_replayable}" for r in self.side_effects
        )


@dataclass(frozen=True, order=True)
class TrajectorySimilarity:
    """Pairwise similarity record. Ordered descending by composite."""

    sort_key: float  # negation of composite for sort order
    composite: float
    pair_id: tuple[str, str]
    action_overlap: float = 0.0
    fingerprint_overlap: float = 0.0
    tool_overlap: float = 0.0
    reason: str = ""

    @classmethod
    def make(
        cls,
        *,
        pair_id: tuple[str, str],
        action_overlap: float,
        fingerprint_overlap: float,
        tool_overlap: float,
        reason: str = "",
    ) -> "TrajectorySimilarity":
        composite = (
            0.4 * action_overlap + 0.4 * fingerprint_overlap + 0.2 * tool_overlap
        )
        return cls(
            sort_key=-composite,
            composite=composite,
            pair_id=pair_id,
            action_overlap=action_overlap,
            fingerprint_overlap=fingerprint_overlap,
            tool_overlap=tool_overlap,
            reason=reason,
        )


def action_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    """Jaccard similarity on action *bigrams* — sensitive to ordering.

    Bigrams capture local sequence: the same actions in different orders score
    lower than the same actions in the same order. Uses set semantics on the
    bigram sequence so length differences don't dominate.
    """
    if not a and not b:
        return 1.0
    bigrams_a = _bigrams(a)
    bigrams_b = _bigrams(b)
    if not bigrams_a or not bigrams_b:
        # Fall back to unigram Jaccard for length-1 sequences.
        sa, sb = set(a), set(b)
        if not sa and not sb:
            return 1.0
        return len(sa & sb) / max(1, len(sa | sb))
    inter = len(bigrams_a & bigrams_b)
    union = len(bigrams_a | bigrams_b)
    return inter / union if union else 0.0


def _bigrams(seq: Sequence[str]) -> frozenset[tuple[str, str]]:
    return frozenset((seq[i], seq[i + 1]) for i in range(len(seq) - 1))


def fingerprint_jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Plain Jaccard on decision-fingerprint sets."""
    if not a and not b:
        return 1.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


@dataclass
class ReplayComparator:
    """Group trajectories by task; surface outliers + similarity rankings.

    >>> from harness_core.orchestration import AgentDecision
    >>> traj = Trajectory(
    ...   trajectory_id="t1", task_signature="task-A",
    ...   decisions=(AgentDecision(action="tool_call", fingerprint="fp1"),),
    ... )
    >>> comp = ReplayComparator(corpus=[traj])
    >>> sims = comp.compare(traj)
    >>> sims[0].pair_id == ("t1", "t1")
    True
    """

    corpus: list[Trajectory] = field(default_factory=list)

    def add(self, trajectory: Trajectory) -> None:
        self.corpus.append(trajectory)

    def for_task(self, task_signature: str) -> list[Trajectory]:
        """Return all corpus trajectories on the given task."""
        return [t for t in self.corpus if t.task_signature == task_signature]

    def compare(
        self,
        current: Trajectory,
        *,
        k: int = 5,
    ) -> list[TrajectorySimilarity]:
        """Find the k most similar past trajectories on the same task."""
        peers = self.for_task(current.task_signature)
        sims: list[TrajectorySimilarity] = []
        for peer in peers:
            sim = TrajectorySimilarity.make(
                pair_id=(current.trajectory_id, peer.trajectory_id),
                action_overlap=action_jaccard(
                    current.action_sequence(), peer.action_sequence()
                ),
                fingerprint_overlap=fingerprint_jaccard(
                    current.fingerprint_set(), peer.fingerprint_set()
                ),
                tool_overlap=fingerprint_jaccard(
                    current.tool_signature_set(), peer.tool_signature_set()
                ),
                reason=f"task={current.task_signature}",
            )
            sims.append(sim)
        sims.sort()  # by sort_key = -composite → descending composite
        return sims[:k]

    def is_outlier(
        self,
        current: Trajectory,
        *,
        threshold: float = 0.3,
        require_n_peers: int = 1,
    ) -> bool:
        """True if no past peer trajectory has composite >= threshold.

        Returns False (not an outlier) if there are fewer than ``require_n_peers``
        comparable trajectories on the same task — outlier detection requires a
        baseline.
        """
        sims = self.compare(current, k=10)
        if len(sims) < require_n_peers:
            return False  # insufficient baseline → don't accuse
        return all(s.composite < threshold for s in sims)

    def stats(self) -> dict[str, int]:
        return {
            "trajectories": len(self.corpus),
            "tasks": len({t.task_signature for t in self.corpus}),
            "outcomes_success": sum(
                1 for t in self.corpus if t.outcome == TrajectoryOutcome.SUCCESS
            ),
            "outcomes_failure": sum(
                1 for t in self.corpus if t.outcome == TrajectoryOutcome.FAILURE
            ),
            "outcomes_rolled_back": sum(
                1 for t in self.corpus if t.outcome == TrajectoryOutcome.ROLLED_BACK
            ),
        }


__all__ = [
    "ReplayComparator",
    "Trajectory",
    "TrajectoryOutcome",
    "TrajectorySimilarity",
    "action_jaccard",
    "fingerprint_jaccard",
]
