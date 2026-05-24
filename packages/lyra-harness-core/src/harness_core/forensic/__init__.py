"""harness_core.forensic — trajectory replay + comparison for sabotage detection.

Per [docs/220-orion-code-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/220-orion-code-multi-hop-collaborative-apply-plan.md) §4.9
(trajectory-replay forensic comparator), [docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md]
(../../../../../../research/harness-engineering/docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md) §3.5
(forensic record), and [docs/188-witness-provenance-memory-techniques-synthesis.md]
(../../../../../../research/harness-engineering/docs/188-witness-provenance-memory-techniques-synthesis.md).

A trajectory that looks unlike all past trajectories on the same task is a
sabotage-detection candidate. This module ships the comparator: similarity
metrics over (decision-fingerprint sets, action-type sequences, side-effect
signatures), grouped by task signature, with outlier detection.

Pure-function agents from :mod:`harness_core.orchestration` are the
prerequisite — non-deterministic trajectories cannot be replay-compared.
"""
from __future__ import annotations

from .replay_comparator import (
    ReplayComparator,
    Trajectory,
    TrajectoryOutcome,
    TrajectorySimilarity,
    action_jaccard,
    fingerprint_jaccard,
)

__all__ = [
    "ReplayComparator",
    "Trajectory",
    "TrajectoryOutcome",
    "TrajectorySimilarity",
    "action_jaccard",
    "fingerprint_jaccard",
]
