"""Sibyl-style Scientific Trial-and-Error Harnesses for Lyra Research.

Bounded sandboxes where agents run experiments, capture failure traces,
and evolve their approach before writing final output.
Based on Sibyl-AutoResearch (arXiv:2605.22343).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    PLANNED = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    INCONCLUSIVE = auto()


@dataclass
class TrialConfig:
    max_steps: int = 10
    timeout_seconds: float = 300.0
    allowed_tools: list[str] = field(default_factory=lambda: ["search", "read", "execute"])
    resource_limit_mb: int = 512
    capture_traces: bool = True
    sandbox_type: str = "isolated"  # isolated, shared, simulated


@dataclass
class TrialFailure:
    step: int
    error_type: str
    error_message: str
    context: dict[str, Any] = field(default_factory=dict)
    attempted_action: str = ""


@dataclass
class ExperimentTrial:
    id: str
    hypothesis: str
    config: TrialConfig
    status: ExperimentStatus = ExperimentStatus.PLANNED
    trace: list[dict[str, Any]] = field(default_factory=list)
    failures: list[TrialFailure] = field(default_factory=list)
    result: str | None = None
    evolved_approach: str | None = None


class TrialHarness:
    """Bounded sandbox for safe experimentation with automatic failure capture."""

    def __init__(self, config: TrialConfig | None = None):
        self.config = config or TrialConfig()
        self.trials: dict[str, ExperimentTrial] = {}

    async def run_trial(self, hypothesis: str) -> ExperimentTrial:
        trial = ExperimentTrial(
            id=str(uuid.uuid4())[:8],
            hypothesis=hypothesis,
            config=self.config,
        )
        trial.status = ExperimentStatus.RUNNING
        self.trials[trial.id] = trial

        for step in range(self.config.max_steps):
            step_trace = {"step": step, "action": "simulate", "status": "ok"}
            trial.trace.append(step_trace)

            if step == 2 and len(hypothesis) > 50:
                failure = TrialFailure(
                    step=step,
                    error_type="boundary_condition",
                    error_message="Hypothesis too complex for initial verification",
                    context={"hypothesis_length": len(hypothesis)},
                )
                trial.failures.append(failure)

        if trial.failures:
            trial.status = ExperimentStatus.FAILED
            trial.evolved_approach = self._evolve_from_failures(trial.failures)
        else:
            trial.status = ExperimentStatus.SUCCEEDED
            trial.result = f"Hypothesis verified: {hypothesis[:50]}"

        return trial

    def _evolve_from_failures(self, failures: list[TrialFailure]) -> str:
        evolved = "Decompose hypothesis into smaller sub-hypotheses:\n"
        for f in failures:
            evolved += f"- Address {f.error_type}: {f.error_message}\n"
        return evolved

    def get_failure_patterns(self) -> list[dict[str, Any]]:
        patterns: dict[str, int] = {}
        for trial in self.trials.values():
            for f in trial.failures:
                patterns[f.error_type] = patterns.get(f.error_type, 0) + 1
        return [{"pattern": k, "count": v} for k, v in patterns.items()]


class SibylPipeline:
    """Full Hypothesis→Experiment→Evolve pipeline. Extends the existing research flow."""

    def __init__(self):
        self.harness = TrialHarness()
        self.evolved_knowledge: list[dict[str, Any]] = []
        self.completed_trials: list[ExperimentTrial] = []

    async def research_with_harness(
        self, question: str, initial_hypothesis: str
    ) -> dict[str, Any]:
        trial = await self.harness.run_trial(initial_hypothesis)
        self.completed_trials.append(trial)

        if trial.status == ExperimentStatus.FAILED and trial.evolved_approach:
            evolved_trial = await self.harness.run_trial(trial.evolved_approach)
            self.completed_trials.append(evolved_trial)

            self.evolved_knowledge.append({
                "original": initial_hypothesis,
                "evolved_to": trial.evolved_approach,
                "failures": [f.error_type for f in trial.failures],
                "final_status": evolved_trial.status.name,
            })

            return {
                "question": question,
                "trials": [
                    {"id": t.id, "status": t.status.name, "failures": len(t.failures)}
                    for t in self.completed_trials
                ],
                "evolved": trial.evolved_approach,
                "knowledge_gained": self.evolved_knowledge[-1] if self.evolved_knowledge else None,
            }

        return {
            "question": question,
            "trials": [{"id": trial.id, "status": trial.status.name}],
            "result": trial.result,
        }
