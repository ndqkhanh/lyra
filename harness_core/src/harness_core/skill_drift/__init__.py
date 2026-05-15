"""harness_core.skill_drift — detect performance regressions in promoted skills.

A skill that was promoted by :mod:`harness_core.skill_auto` had a high
held-out eval score *at the time of promotion*. That snapshot can drift:
the skill's underlying assumptions go stale, the corpus shifts, or new
edge cases surface. Without continuous monitoring, drift hides until
catastrophe.

The package wires three pieces:

    - :class:`SkillInvocation` — one record per skill use (succeeded +
      optional graded ``score``).
    - :class:`DriftPolicy` — thresholds (``info`` / ``warning`` /
      ``critical``) over the gap between baseline rate and recent rate.
    - :class:`SkillDriftMonitor` — accumulator + checker. ``record(...)``
      collects invocations; ``check(skill_id)`` emits a :class:`DriftAlert`
      when the recent-window success rate has fallen below baseline by
      more than the policy's ``info_drift``.

Used by Argus (curator drift detection per [docs/197]), Lyra V3.9 (skill-
drift monitor before promotion to procedural memory), Polaris (long-
running research-skill regressions), Orion-Code (per-repo skill drift).
"""
from __future__ import annotations

from .monitor import SkillDriftMonitor
from .types import DriftAlert, DriftPolicy, SkillInvocation

__all__ = [
    "DriftAlert",
    "DriftPolicy",
    "SkillDriftMonitor",
    "SkillInvocation",
]
