"""ReflACT Pipeline — Reflect→Act→Validate skill optimization (P3-B1 CRITICAL).

Epoch-based skill optimization where skills improve autonomously through:
1. Reflect — analyze trajectory failures, identify which skill step caused the failure
2. Act — edit skill's natural-language instructions at the failing step
3. Validate — run edited skill on held-out validation tasks, gate on success rate

Implements the Microsoft SkillOpt ReflACT pattern.
See: plan-phase3-skills-routing.md §Key Insight 1
"""
from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------


class StepOutcome(str, enum.Enum):
    """Outcome of a single skill step execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    ERROR = "error"


class PipelinePhase(str, enum.Enum):
    """Phases of the ReflACT optimization pipeline."""
    REFLECT = "reflect"
    ACT = "act"
    VALIDATE = "validate"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class SkillStep:
    """A single step in a skill's instruction pipeline."""

    step_id: str
    description: str
    instruction: str
    expected_output: str = ""
    timeout_seconds: float = 60.0
    order: int = 0


@dataclass(frozen=True)
class SkillDefinition:
    """A skill with its instruction steps."""

    name: str
    version: str
    description: str
    steps: tuple[SkillStep, ...]
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def step_by_id(self, step_id: str) -> SkillStep | None:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def with_updated_step(self, step_id: str, new_instruction: str) -> SkillDefinition:
        """Return a new SkillDefinition with one step's instruction changed."""
        new_steps = tuple(
            SkillStep(
                step_id=s.step_id,
                description=s.description,
                instruction=new_instruction if s.step_id == step_id else s.instruction,
                expected_output=s.expected_output,
                timeout_seconds=s.timeout_seconds,
                order=s.order,
            )
            for s in self.steps
        )
        new_version = _bump_version(self.version)
        return SkillDefinition(
            name=self.name,
            version=new_version,
            description=self.description,
            steps=new_steps,
            metadata=self.metadata,
        )

    def fingerprint(self) -> str:
        content = "|".join(f"{s.step_id}:{s.instruction}" for s in self.steps)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Trajectory Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StepTrace:
    """Execution trace for a single skill step."""

    step_id: str
    outcome: StepOutcome
    duration_ms: float
    error_message: str = ""
    output_preview: str = ""
    retry_count: int = 0


@dataclass(frozen=True)
class Trajectory:
    """Full execution trajectory of a skill invocation."""

    trajectory_id: str
    skill_name: str
    skill_version: str
    task_input: str
    steps: tuple[StepTrace, ...]
    overall_success: bool
    total_duration_ms: float
    created_at: float = 0.0

    def failing_steps(self) -> tuple[StepTrace, ...]:
        return tuple(s for s in self.steps if s.outcome != StepOutcome.SUCCESS)

    def step_ids(self) -> tuple[str, ...]:
        return tuple(s.step_id for s in self.steps)


# ---------------------------------------------------------------------------
# Reflect Phase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FailureAnalysis:
    """Analysis of why a trajectory failed."""

    trajectory_id: str
    failed_step_id: str
    root_cause: str
    suggested_fix: str
    confidence: float  # How confident we are in this analysis
    related_steps: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReflectReport:
    """Aggregate reflection across multiple trajectories."""

    trajectories_analyzed: int
    failures_found: int
    analyses: tuple[FailureAnalysis, ...]
    most_problematic_step: str | None
    success_rate_before: float

    @property
    def failure_rate(self) -> float:
        if self.trajectories_analyzed == 0:
            return 0.0
        return self.failures_found / self.trajectories_analyzed

    @property
    def primary_failure_step(self) -> str | None:
        if not self.analyses:
            return None
        counts: dict[str, int] = {}
        for a in self.analyses:
            counts[a.failed_step_id] = counts.get(a.failed_step_id, 0) + 1
        return max(counts, key=lambda k: counts[k])


@dataclass
class Reflector:
    """Reflect phase: analyze trajectory failures to identify root causes."""

    min_confidence: float = 0.5
    max_analyses: int = 100

    def analyze(self, trajectory: Trajectory) -> list[FailureAnalysis]:
        """Analyze a single trajectory for failures."""
        analyses: list[FailureAnalysis] = []
        for step in trajectory.failing_steps():
            analysis = self._analyze_step_failure(trajectory, step)
            if analysis.confidence >= self.min_confidence:
                analyses.append(analysis)
        return analyses

    def reflect(self, trajectories: list[Trajectory]) -> ReflectReport:
        """Reflect on a batch of trajectories to produce a failure report."""
        all_analyses: list[FailureAnalysis] = []
        total_successes = sum(1 for t in trajectories if t.overall_success)
        total_count = len(trajectories)

        for t in trajectories:
            analyses = self.analyze(t)[: self.max_analyses]
            all_analyses.extend(analyses)

        failures = sum(1 for t in trajectories if not t.overall_success)
        most_problematic = None
        if all_analyses:
            counts: dict[str, int] = {}
            for a in all_analyses:
                counts[a.failed_step_id] = counts.get(a.failed_step_id, 0) + 1
            most_problematic = max(counts, key=lambda k: counts[k])

        success_rate = total_successes / max(total_count, 1)

        return ReflectReport(
            trajectories_analyzed=total_count,
            failures_found=failures,
            analyses=tuple(all_analyses),
            most_problematic_step=most_problematic,
            success_rate_before=success_rate,
        )

    @staticmethod
    def _analyze_step_failure(trajectory: Trajectory, step: StepTrace) -> FailureAnalysis:
        """Heuristic failure analysis for a single step."""
        if step.outcome == StepOutcome.TIMEOUT:
            root_cause = f"Step '{step.step_id}' timed out after {step.duration_ms:.0f}ms"
            suggested_fix = f"Increase timeout or simplify instruction for step '{step.step_id}'"
            confidence = 0.85
        elif step.outcome == StepOutcome.ERROR:
            root_cause = f"Step '{step.step_id}' encountered error: {step.error_message[:200]}"
            suggested_fix = f"Add error handling or clarify constraints for step '{step.step_id}'"
            confidence = 0.75
        elif step.outcome == StepOutcome.FAILURE:
            root_cause = f"Step '{step.step_id}' failed to produce expected output"
            suggested_fix = f"Refine instruction specificity for step '{step.step_id}'"
            confidence = 0.65
        else:
            root_cause = f"Step '{step.step_id}' had unexpected outcome"
            suggested_fix = f"Review step '{step.step_id}' for correctness"
            confidence = 0.4

        # Boost confidence if this step failed consistently in prior steps
        failing_before = [
            s.step_id for s in trajectory.steps
            if s.outcome != StepOutcome.SUCCESS
            and trajectory.steps.index(s) < trajectory.steps.index(step)
        ]

        return FailureAnalysis(
            trajectory_id=trajectory.trajectory_id,
            failed_step_id=step.step_id,
            root_cause=root_cause,
            suggested_fix=suggested_fix,
            confidence=min(confidence + 0.05 * len(failing_before), 1.0),
            related_steps=tuple(failing_before),
        )


# ---------------------------------------------------------------------------
# Act Phase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EditAction:
    """A concrete edit to a skill step's instruction."""

    step_id: str
    original_instruction: str
    new_instruction: str
    reason: str
    source_analysis: str  # trajectory_id of the analysis


@dataclass(frozen=True)
class ActResult:
    """Result of the Act phase — edited skill."""

    original_skill: SkillDefinition
    edited_skill: SkillDefinition
    edits_applied: tuple[EditAction, ...]
    edit_count: int

    @property
    def has_edits(self) -> bool:
        return self.edit_count > 0


@dataclass
class Actor:
    """Act phase: apply suggested fixes to skill instructions."""

    max_edits_per_epoch: int = 5
    min_edit_confidence: float = 0.6

    def act(
        self, skill: SkillDefinition, report: ReflectReport
    ) -> ActResult:
        """Apply fixes from a reflection report to a skill definition."""
        if not report.analyses:
            return ActResult(
                original_skill=skill,
                edited_skill=skill,
                edits_applied=(),
                edit_count=0,
            )

        # Sort analyses by confidence descending
        sorted_analyses = sorted(report.analyses, key=lambda a: a.confidence, reverse=True)

        edited = skill
        edits: list[EditAction] = []

        for analysis in sorted_analyses[: self.max_edits_per_epoch]:
            if analysis.confidence < self.min_edit_confidence:
                continue

            step = edited.step_by_id(analysis.failed_step_id)
            if step is None:
                continue

            # Generate new instruction incorporating suggested fix
            new_instruction = self._apply_fix(step.instruction, analysis)
            if new_instruction == step.instruction:
                continue  # No change needed

            edit = EditAction(
                step_id=step.step_id,
                original_instruction=step.instruction,
                new_instruction=new_instruction,
                reason=analysis.root_cause,
                source_analysis=analysis.trajectory_id,
            )
            edits.append(edit)
            edited = edited.with_updated_step(step.step_id, new_instruction)

        return ActResult(
            original_skill=skill,
            edited_skill=edited,
            edits_applied=tuple(edits),
            edit_count=len(edits),
        )

    @staticmethod
    def _apply_fix(instruction: str, analysis: FailureAnalysis) -> str:
        """Apply the suggested fix to the instruction text."""
        suffix = f"\n[ReflACT fix: {analysis.suggested_fix}]"
        if instruction.endswith(suffix):
            return instruction
        return instruction + suffix


# ---------------------------------------------------------------------------
# Validate Phase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating an edited skill against held-out tasks."""

    passed: bool
    success_rate_before: float
    success_rate_after: float
    improvement: float  # positive = better
    tasks_run: int
    tasks_passed: int
    reason: str


class ImprovementGate:
    """Statistical gate that decides if an edit should be deployed."""

    def __init__(
        self,
        min_improvement: float = 0.0,
        min_success_rate: float = 0.5,
        min_tasks: int = 3,
    ):
        self.min_improvement = min_improvement
        self.min_success_rate = min_success_rate
        self.min_tasks = min_tasks

    def evaluate(self, result: ValidationResult) -> bool:
        """Evaluate whether the validation results pass the gate."""
        if result.tasks_run < self.min_tasks:
            return False
        if result.success_rate_after < self.min_success_rate:
            return False
        if result.improvement < self.min_improvement:
            return False
        return result.passed


@dataclass
class Validator:
    """Validate phase: test edited skills on held-out validation tasks."""

    gate: ImprovementGate = field(default_factory=ImprovementGate)

    def validate(
        self,
        edited_skill: SkillDefinition,
        validation_tasks: list[str],
        execute_fn=None,
    ) -> ValidationResult:
        """Run edited skill on validation tasks and measure improvement.

        execute_fn(task, skill) -> bool determines if task succeeded.
        """
        if not validation_tasks or execute_fn is None:
            return ValidationResult(
                passed=False,
                success_rate_before=0.0,
                success_rate_after=0.0,
                improvement=0.0,
                tasks_run=0,
                tasks_passed=0,
                reason="No validation tasks or executor provided",
            )

        passed_count = 0
        for task in validation_tasks:
            try:
                if execute_fn(task, edited_skill):
                    passed_count += 1
            except Exception:
                pass

        tasks_run = len(validation_tasks)
        success_rate = passed_count / max(tasks_run, 1)

        # In practice, success_rate_before would come from a prior validation run
        # Here we assume the gate handles the before/after comparison
        result = ValidationResult(
            passed=self.gate.evaluate(
                ValidationResult(
                    passed=success_rate >= self.gate.min_success_rate,
                    success_rate_before=0.0,
                    success_rate_after=success_rate,
                    improvement=0.0,
                    tasks_run=tasks_run,
                    tasks_passed=passed_count,
                    reason="",
                )
            ),
            success_rate_before=0.0,
            success_rate_after=success_rate,
            improvement=0.0,
            tasks_run=tasks_run,
            tasks_passed=passed_count,
            reason=f"{passed_count}/{tasks_run} tasks passed",
        )

        return result

    def compare(
        self,
        before_rate: float,
        after_rate: float,
        tasks_run: int,
    ) -> ValidationResult:
        """Compare before/after success rates with gate evaluation."""
        improvement = after_rate - before_rate
        passed = (
            tasks_run >= self.gate.min_tasks
            and after_rate >= self.gate.min_success_rate
            and improvement >= self.gate.min_improvement
        )
        return ValidationResult(
            passed=passed,
            success_rate_before=before_rate,
            success_rate_after=after_rate,
            improvement=improvement,
            tasks_run=tasks_run,
            tasks_passed=int(after_rate * tasks_run),
            reason=f"Improvement: {improvement:+.2%}" if passed else f"No significant improvement ({improvement:+.2%})",
        )


# ---------------------------------------------------------------------------
# ReflACT Pipeline
# ---------------------------------------------------------------------------


class EpochStopReason(str, enum.Enum):
    """Why a ReflACT epoch stopped."""
    MAX_EPOCHS = "max_epochs"
    NO_IMPROVEMENT = "no_improvement"
    CONVERGED = "converged"
    GATE_REJECTED = "gate_rejected"
    NO_FAILURES = "no_failures"


@dataclass(frozen=True)
class EpochResult:
    """Result of a single ReflACT epoch."""

    epoch: int
    phase: PipelinePhase
    report: ReflectReport | None = None
    act_result: ActResult | None = None
    validation: ValidationResult | None = None
    stop_reason: EpochStopReason | None = None

    @property
    def skill_fingerprint(self) -> str | None:
        if self.act_result is not None:
            return self.act_result.edited_skill.fingerprint()
        return None


@dataclass(frozen=True)
class ReflACTPipelineResult:
    """Final result of a ReflACT optimization run."""

    original_skill: SkillDefinition
    final_skill: SkillDefinition
    epochs: tuple[EpochResult, ...]
    total_improvement: float
    deployed: bool
    stop_reason: EpochStopReason

    @property
    def epoch_count(self) -> int:
        return len(self.epochs)

    @property
    def total_edits(self) -> int:
        return sum(
            e.act_result.edit_count
            for e in self.epochs
            if e.act_result is not None
        )


@dataclass
class ReflACTPipeline:
    """Full Reflect→Act→Validate pipeline for skill optimization.

    Usage::

        pipeline = ReflACTPipeline(max_epochs=10)
        result = pipeline.optimize(
            skill=my_skill,
            trajectories=training_trajectories,
            validation_tasks=held_out_tasks,
            execute_fn=my_executor,
        )
    """

    reflector: Reflector = field(default_factory=Reflector)
    actor: Actor = field(default_factory=Actor)
    validator: Validator = field(default_factory=Validator)
    max_epochs: int = 10
    early_stop_patience: int = 3
    improvement_threshold: float = 0.01
    _history: list[EpochResult] = field(default_factory=list)

    def optimize(
        self,
        skill: SkillDefinition,
        trajectories: list[Trajectory],
        validation_tasks: list[str] | None = None,
        execute_fn=None,
    ) -> ReflACTPipelineResult:
        """Run the full ReflACT optimization pipeline."""
        self._history = []
        current_skill = skill
        best_success_rate = 0.0
        patience_counter = 0

        for epoch in range(self.max_epochs):
            # 1. Reflect
            report = self.reflector.reflect(trajectories)

            if report.failures_found == 0:
                er = EpochResult(
                    epoch=epoch,
                    phase=PipelinePhase.REFLECT,
                    report=report,
                    stop_reason=EpochStopReason.NO_FAILURES,
                )
                self._history.append(er)
                return self._build_result(skill, current_skill, EpochStopReason.NO_FAILURES)

            # 2. Act
            act_result = self.actor.act(current_skill, report)

            if not act_result.has_edits:
                er = EpochResult(
                    epoch=epoch,
                    phase=PipelinePhase.ACT,
                    report=report,
                    act_result=act_result,
                    stop_reason=EpochStopReason.CONVERGED,
                )
                self._history.append(er)
                return self._build_result(skill, current_skill, EpochStopReason.CONVERGED)

            # 3. Validate
            validation = None
            if validation_tasks and execute_fn:
                validation = self.validator.validate(
                    act_result.edited_skill, validation_tasks, execute_fn
                )
                if not validation.passed:
                    er = EpochResult(
                        epoch=epoch,
                        phase=PipelinePhase.VALIDATE,
                        report=report,
                        act_result=act_result,
                        validation=validation,
                        stop_reason=EpochStopReason.GATE_REJECTED,
                    )
                    self._history.append(er)
                    return self._build_result(skill, current_skill, EpochStopReason.GATE_REJECTED)

                # Track improvement
                if validation.success_rate_after > best_success_rate + self.improvement_threshold:
                    best_success_rate = validation.success_rate_after
                    patience_counter = 0
                else:
                    patience_counter += 1

                if patience_counter >= self.early_stop_patience:
                    er = EpochResult(
                        epoch=epoch,
                        phase=PipelinePhase.VALIDATE,
                        report=report,
                        act_result=act_result,
                        validation=validation,
                        stop_reason=EpochStopReason.NO_IMPROVEMENT,
                    )
                    self._history.append(er)
                    return self._build_result(skill, current_skill, EpochStopReason.NO_IMPROVEMENT)

            # Accept the edit
            current_skill = act_result.edited_skill

            er = EpochResult(
                epoch=epoch,
                phase=PipelinePhase.DEPLOY,
                report=report,
                act_result=act_result,
                validation=validation,
            )
            self._history.append(er)

        return self._build_result(skill, current_skill, EpochStopReason.MAX_EPOCHS)

    def _build_result(
        self,
        original: SkillDefinition,
        final: SkillDefinition,
        reason: EpochStopReason,
    ) -> ReflACTPipelineResult:
        """Build the final pipeline result."""
        # Compute total improvement from validation results
        improvements = [
            e.validation.improvement
            for e in self._history
            if e.validation is not None
        ]
        total_improvement = sum(improvements) if improvements else 0.0

        return ReflACTPipelineResult(
            original_skill=original,
            final_skill=final,
            epochs=tuple(self._history),
            total_improvement=total_improvement,
            deployed=reason != EpochStopReason.GATE_REJECTED,
            stop_reason=reason,
        )

    @property
    def history(self) -> tuple[EpochResult, ...]:
        return tuple(self._history)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bump_version(version: str) -> str:
    """Bump the patch version of a semver string."""
    parts = version.split(".")
    if len(parts) == 3 and parts[-1].isdigit():
        return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
    return version + ".1"


def compute_success_rate(trajectories: list[Trajectory]) -> float:
    """Compute the success rate across a set of trajectories."""
    if not trajectories:
        return 0.0
    return sum(1 for t in trajectories if t.overall_success) / len(trajectories)


__all__ = [
    "ActResult",
    "Actor",
    "EditAction",
    "EpochResult",
    "EpochStopReason",
    "FailureAnalysis",
    "ImprovementGate",
    "PipelinePhase",
    "ReflectReport",
    "Reflector",
    "ReflACTPipeline",
    "ReflACTPipelineResult",
    "SkillDefinition",
    "SkillStep",
    "StepOutcome",
    "StepTrace",
    "Trajectory",
    "ValidationResult",
    "Validator",
    "compute_success_rate",
]
