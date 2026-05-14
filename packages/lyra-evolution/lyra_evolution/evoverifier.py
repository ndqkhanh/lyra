"""EvoSkills co-evolutionary verification — Phase K of the Lyra skill-curation plan.

Implements an informationally isolated verifier that evaluates skill candidates
independently of the training signal, preventing reward hacking.

Grounded in:
- arXiv:2604.01687 — EvoSkills: Co-evolutionary Skill Verification
- Key finding: +17.6pp over human curation when verifier is isolated from curator
- Isolation breaks the curator's ability to game its own evaluation metric
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol


__all__ = [
    "VerificationOutcome",
    "VerificationReport",
    "VerificationTask",
    "SkillRunner",
    "IsolatedVerifier",
    "CoEvolutionGate",
]


class VerificationOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class VerificationReport:
    """Result of one isolated verification run."""

    skill_id: str
    outcome: VerificationOutcome
    score: float            # fraction of tasks passed [0, 1]
    rationale: str
    tasks_run: int = 0
    tasks_passed: int = 0


@dataclass
class VerificationTask:
    """One task used to probe a skill candidate."""

    task_id: str
    description: str
    expected_outcome: str
    context_tag: str = ""


class SkillRunner(Protocol):
    """Executes a skill against a verification task; returns True on success."""

    def run(self, skill_content: str, task: VerificationTask) -> bool: ...


@dataclass
class IsolatedVerifier:
    """Informationally isolated verifier for skill candidates.

    The verifier holds its own separate task pool and never receives
    curator reward signals, preventing the curator from gaming the metric.

    Usage::

        verifier = IsolatedVerifier(pass_threshold=0.70)
        verifier.register_task(VerificationTask("t1", "parse JSON", "success", "web"))
        report = verifier.verify("my-skill", skill_content, runner)
    """

    pass_threshold: float = 0.70
    _task_pool: list[VerificationTask] = field(default_factory=list)
    _verification_history: list[VerificationReport] = field(default_factory=list)

    def register_task(self, task: VerificationTask) -> None:
        self._task_pool.append(task)

    def verify(
        self,
        skill_id: str,
        skill_content: str,
        runner: SkillRunner,
        context_filter: Optional[str] = None,
    ) -> VerificationReport:
        """Run all registered tasks (optionally filtered by context_tag)."""
        tasks = self._task_pool
        if context_filter is not None:
            tasks = [t for t in tasks if t.context_tag == context_filter]

        if not tasks:
            report = VerificationReport(
                skill_id=skill_id,
                outcome=VerificationOutcome.INCONCLUSIVE,
                score=0.0,
                rationale="no verification tasks registered",
            )
            self._verification_history.append(report)
            return report

        passed = sum(1 for t in tasks if runner.run(skill_content, t))
        score = passed / len(tasks)
        outcome = (
            VerificationOutcome.PASS
            if score >= self.pass_threshold
            else VerificationOutcome.FAIL
        )
        report = VerificationReport(
            skill_id=skill_id,
            outcome=outcome,
            score=score,
            rationale=f"{passed}/{len(tasks)} tasks passed (threshold={self.pass_threshold})",
            tasks_run=len(tasks),
            tasks_passed=passed,
        )
        self._verification_history.append(report)
        return report

    @property
    def history(self) -> list[VerificationReport]:
        return list(self._verification_history)

    def pass_rate(self) -> float:
        if not self._verification_history:
            return 0.0
        passed = sum(
            1 for r in self._verification_history
            if r.outcome == VerificationOutcome.PASS
        )
        return passed / len(self._verification_history)


class CoEvolutionGate:
    """Gate that admits skills to the library only after isolated verification.

    The curator proposes; the isolated verifier decides.
    This co-evolutionary arrangement breaks the curator's ability to optimize
    its own evaluation signal — the verifier is a separate agent with its own
    task pool that the curator cannot inspect or influence.

    Usage::

        gate = CoEvolutionGate(verifier, runner)
        report = gate.evaluate("skill-id", content)
        if report.outcome == VerificationOutcome.PASS:
            library.add("skill-id", content)
    """

    def __init__(
        self,
        verifier: IsolatedVerifier,
        runner: SkillRunner,
    ) -> None:
        self._verifier = verifier
        self._runner = runner
        self._admitted: dict[str, VerificationReport] = {}
        self._rejected: dict[str, VerificationReport] = {}

    def evaluate(
        self,
        skill_id: str,
        skill_content: str,
        context_filter: Optional[str] = None,
    ) -> VerificationReport:
        """Evaluate a skill candidate; record admission or rejection."""
        report = self._verifier.verify(
            skill_id, skill_content, self._runner, context_filter
        )
        if report.outcome == VerificationOutcome.PASS:
            self._admitted[skill_id] = report
        else:
            self._rejected[skill_id] = report
        return report

    @property
    def admitted_ids(self) -> list[str]:
        return list(self._admitted.keys())

    @property
    def rejected_ids(self) -> list[str]:
        return list(self._rejected.keys())

    def admission_rate(self) -> float:
        total = len(self._admitted) + len(self._rejected)
        return len(self._admitted) / total if total > 0 else 0.0
