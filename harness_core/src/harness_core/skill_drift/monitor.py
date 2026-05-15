"""SkillDriftMonitor — record skill invocations + compare baseline vs recent.

The monitor is a typed accumulator. Each :meth:`record` call appends a
:class:`SkillInvocation`. :meth:`check` compares the *baseline* (the
first ``min_baseline_invocations`` for that skill) to the *recent window*
(the last ``recent_window`` invocations). When the recent rate has
dropped by at least the policy's ``info_drift``, it returns a
:class:`DriftAlert` whose severity is determined by which threshold the
drop crossed.

Composes with :mod:`harness_core.skill_auto` (which produces the skills
in question), :mod:`harness_core.eval_runner` (graded ``score``-based
checks), and :mod:`harness_core.provenance` (every alert may be
witnessed).
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from ..provenance import WitnessLattice
from .types import DriftAlert, DriftPolicy, SkillInvocation


@dataclass
class SkillDriftMonitor:
    """Track invocations + raise alerts when recent performance degrades.

    >>> mon = SkillDriftMonitor()
    >>> for _ in range(20):
    ...     _ = mon.record(skill_id="x", succeeded=True)
    >>> for _ in range(10):
    ...     _ = mon.record(skill_id="x", succeeded=False)
    >>> alert = mon.check("x")
    >>> alert is not None and alert.severity == "critical"
    True
    """

    policy: DriftPolicy = field(default_factory=DriftPolicy)
    lattice: Optional[WitnessLattice] = None
    _invocations: dict[str, list[SkillInvocation]] = field(
        default_factory=lambda: defaultdict(list),
    )
    _alerts: list[DriftAlert] = field(default_factory=list)

    # --- Recording -------------------------------------------------------

    def record(
        self,
        *,
        skill_id: str,
        succeeded: bool,
        score: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> SkillInvocation:
        """Append one invocation.

        ``score`` is used when the skill produces a graded outcome (e.g., an
        eval rubric in [0, 1]); when ``score`` is omitted it defaults to
        1.0 on success and 0.0 on failure, so the monitor can be driven by
        boolean success alone.
        """
        if score is None:
            score = 1.0 if succeeded else 0.0
        inv = SkillInvocation.create(
            skill_id=skill_id,
            succeeded=succeeded,
            score=score,
            metadata=metadata,
        )
        self._invocations[skill_id].append(inv)
        return inv

    # --- Inspection ------------------------------------------------------

    def invocations_for(self, skill_id: str) -> list[SkillInvocation]:
        return list(self._invocations.get(skill_id, ()))

    def known_skills(self) -> list[str]:
        return sorted(self._invocations)

    def baseline_rate(self, skill_id: str) -> Optional[float]:
        """Mean ``score`` over the first ``min_baseline_invocations``.

        Returns None when there is not enough history yet.
        """
        history = self._invocations.get(skill_id, [])
        n = self.policy.min_baseline_invocations
        if len(history) < n:
            return None
        baseline = history[:n]
        return sum(i.score for i in baseline) / len(baseline)

    def recent_rate(self, skill_id: str) -> Optional[float]:
        """Mean ``score`` over the last ``recent_window``.

        Returns None when there are fewer invocations than the recent window.
        """
        history = self._invocations.get(skill_id, [])
        w = self.policy.recent_window
        if len(history) < w:
            return None
        recent = history[-w:]
        return sum(i.score for i in recent) / len(recent)

    # --- Alerting --------------------------------------------------------

    def check(self, skill_id: str) -> Optional[DriftAlert]:
        """Compute drift for one skill; emit an alert if above ``info_drift``.

        Returns None when there isn't enough history, or when the recent
        rate is at or above the baseline.
        """
        baseline = self.baseline_rate(skill_id)
        recent = self.recent_rate(skill_id)
        if baseline is None or recent is None:
            return None
        drift = baseline - recent
        if drift <= self.policy.info_drift:
            return None

        if drift > self.policy.critical_drift:
            severity = "critical"
        elif drift > self.policy.warning_drift:
            severity = "warning"
        else:
            severity = "info"

        alert = DriftAlert(
            skill_id=skill_id,
            baseline_rate=baseline,
            recent_rate=recent,
            drift=drift,
            n_baseline=self.policy.min_baseline_invocations,
            n_recent=self.policy.recent_window,
            severity=severity,
            note=(
                f"recent rate {recent:.3f} dropped {drift:.3f} below "
                f"baseline {baseline:.3f}"
            ),
            detected_at=time.time(),
        )
        self._alerts.append(alert)
        self._record_witness(alert)
        return alert

    def check_all(self) -> list[DriftAlert]:
        """Run :meth:`check` on every known skill; return non-None alerts."""
        out: list[DriftAlert] = []
        for skill_id in self.known_skills():
            alert = self.check(skill_id)
            if alert is not None:
                out.append(alert)
        return out

    def alerts(self) -> list[DriftAlert]:
        """Every alert ever emitted by this monitor."""
        return list(self._alerts)

    # --- Stats -----------------------------------------------------------

    def stats(self) -> dict:
        """Counts by skill: total invocations, success rate, alert count."""
        out: dict = {}
        per_skill_alerts = defaultdict(int)
        for a in self._alerts:
            per_skill_alerts[a.skill_id] += 1
        for skill_id, history in self._invocations.items():
            n = len(history)
            success_rate = sum(i.score for i in history) / n if n else 0.0
            out[skill_id] = {
                "n_invocations": n,
                "success_rate": success_rate,
                "n_alerts": per_skill_alerts[skill_id],
            }
        return out

    # --- Internals -------------------------------------------------------

    def _record_witness(self, alert: DriftAlert) -> None:
        if self.lattice is None:
            return
        self.lattice.record_decision(
            agent_id="skill-drift-monitor",
            action="drift_alert",
            fingerprint=alert.skill_id,
        )


__all__ = ["SkillDriftMonitor"]
