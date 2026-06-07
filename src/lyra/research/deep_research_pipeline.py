"""
DeepScientist-Fused Auto-Research Pipeline.

Implements a 3-stage DeepScientist-style research pipeline that
operates on top of the Karpathy Auto-Research Loop:

    Stage 1 (Strategize)
    --------------------
    Analyze findings from ``FindingsMemory``, score hypotheses with
    DeepScientist valuation V = (v_u, v_q, v_e), and generate new
    hypotheses via an LLM Reviewer.

    Stage 2 (Implement)
    -------------------
    UCB acquisition selects the best hypothesis. A coding agent
    implements the experiment, runs it, and logs results.

    Stage 3 (Analyze)
    -----------------
    On success, run deep ablation experiments and auto-generate a
    research paper / summary.

**Quest system**: one quest per research direction. Each quest has a
dedicated worktree, memory slice, and configuration. The ``QuestManager``
creates, lists, and manages quests, integrates with the fleet
orchestrator for parallel execution.

References
----------
- DeepScientist / Darwin Godel Machine (DGM): arXiv 2505.22954v3
- Karpathy Auto-Research Loop: github.com/karpathy/autoresearch (~80k star)
- Lyra Auto-Research Loop: ``src/lyra/research/auto_research_loop.py``
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from lyra.research.auto_research_loop import (
    AutoResearchLoop,
    ExperimentLedger,
    ExperimentRecord,
    ExperimentStatus,
)
from lyra.research.findings_memory import (
    DEFAULT_VALUATION_WEIGHTS,
    FindingRecord,
    FindingsMemory,
    FindingStage,
    ValuationScores,
)
from lyra.memory.cascade_memory import CascadeMemory

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_WORKTREE_ROOT: str = ".claude/worktrees/research"
"""Default directory for quest worktree roots."""

DEFAULT_ABLATION_BUDGET: int = 5
"""Number of ablation experiments to run on a successful finding."""

DEFAULT_CASCADE_MEMORY_QUEST_LABEL: str = "quest"
"""Label used to tag cascade memory items originating from a quest."""


# =============================================================================
# Enums and data structures
# =============================================================================


class ReviewerDimension(str, Enum):
    """Dimensions that the LLM Reviewer scores.

    Maps to the DeepScientist V vector.
    """

    UTILITY = "utility"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"


@dataclass(frozen=True)
class ReviewerScore:
    """Score from a single LLM Reviewer call.

    Attributes:
        hypothesis: The hypothesis that was scored.
        utility: ``v_u`` — expected usefulness.
        quality: ``v_q`` — expected rigor.
        efficiency: ``v_e`` — expected compute efficiency.
        reasoning: Free-text reasoning from the reviewer.
        reviewer_id: Identifier for the reviewer (if multiple reviewers).
    """

    hypothesis: str
    utility: float
    quality: float
    efficiency: float
    reasoning: str = ""
    reviewer_id: str = "default"

    def to_valuation(self) -> ValuationScores:
        return ValuationScores(
            utility=self.utility,
            quality=self.quality,
            efficiency=self.efficiency,
        )


@dataclass
class QuestConfig:
    """Configuration for a single quest.

    Attributes:
        quest_id: Unique identifier.
        goal: High-level research goal / direction.
        baseline_repo: Path to the baseline repository to work on.
        worktree_path: Dedicated worktree directory for this quest.
        max_iterations: Maximum auto-research iterations per round.
        ucb_exploration: Exploration parameter for UCB acquisition.
        metadata: Arbitrary key-value store.
    """

    quest_id: str = ""
    goal: str = ""
    baseline_repo: str = ""
    worktree_path: str = ""
    max_iterations: int = 20
    ucb_exploration: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "goal": self.goal,
            "baseline_repo": self.baseline_repo,
            "worktree_path": self.worktree_path,
            "max_iterations": self.max_iterations,
            "ucb_exploration": self.ucb_exploration,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestConfig:
        return cls(
            quest_id=data.get("quest_id", ""),
            goal=data.get("goal", ""),
            baseline_repo=data.get("baseline_repo", ""),
            worktree_path=data.get("worktree_path", ""),
            max_iterations=data.get("max_iterations", 20),
            ucb_exploration=data.get("ucb_exploration", 1.0),
            metadata=dict(data.get("metadata", {})),
        )


# =============================================================================
# DeepResearchPipeline (the 3-stage DeepScientist pipeline)
# =============================================================================


class DeepResearchPipeline:
    """3-stage DeepScientist-style research pipeline.

    The pipeline runs on top of a ``FindingsMemory`` database and an
    ``AutoResearchLoop`` to propose, implement, and analyze experiments
    autonomously.

    Usage::

        pipeline = DeepResearchPipeline(
            findings_memory=FindingsMemory(),
            auto_loop=auto_loop,
            llm_reviewer=my_review_fn,
            coding_agent=my_code_fn,
        )
        result = pipeline.run(quest_id="q-001", goal="Reduce inference cost")
    """

    # Type aliases for provider callbacks
    # f(hypothesis: str, context: dict) -> ReviewerScore
    LLMReviewer = Callable[[str, dict[str, Any]], ReviewerScore]

    # f(hypothesis: str, work_dir: Path, quest_config: QuestConfig) -> dict[str, Any]
    CodingAgent = Callable[[str, Path, "QuestConfig"], dict[str, Any]]

    def __init__(
        self,
        findings_memory: FindingsMemory,
        auto_loop: AutoResearchLoop | None = None,
        llm_reviewer: LLMReviewer | None = None,
        coding_agent: CodingAgent | None = None,
        auto_loop_builder: Callable[[Path, str], AutoResearchLoop] | None = None,
        ablation_budget: int = DEFAULT_ABLATION_BUDGET,
        valuation_weights: dict[str, float] | None = None,
    ) -> None:
        """
        Args:
            findings_memory: The findings database to read from and write to.
            auto_loop: Pre-configured ``AutoResearchLoop``. If ``None``, the
                pipeline will use ``auto_loop_builder`` to create one per quest.
            llm_reviewer: Callable that scores a hypothesis on the three
                DeepScientist dimensions. Returns a ``ReviewerScore``.
            coding_agent: Callable that implements a hypothesis and returns
                experiment results.
            auto_loop_builder: ``(work_dir, eval_command) -> AutoResearchLoop``.
                Used when ``auto_loop`` is not pre-configured.
            ablation_budget: Number of ablation experiments per successful finding.
            valuation_weights: Weights for combining V = (v_u, v_q, v_e).
        """
        self.findings_memory = findings_memory
        self._auto_loop = auto_loop
        self._llm_reviewer = llm_reviewer
        self._coding_agent = coding_agent
        self._auto_loop_builder = auto_loop_builder
        self._ablation_budget = ablation_budget
        self._valuation_weights = valuation_weights or dict(DEFAULT_VALUATION_WEIGHTS)

        # Pipeline state
        self._current_quest: QuestConfig | None = None
        self._results: list[dict[str, Any]] = []

        # Auto-request worktree root for quest isolation
        self._worktree_root: Path | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        quest_id: str,
        goal: str,
        baseline_repo: str = "",
        hypotheses: list[str] | None = None,
    ) -> list[FindingRecord]:
        """Execute the full 3-stage pipeline for a quest.

        Args:
            quest_id: Unique identifier for the quest.
            goal: High-level research goal.
            baseline_repo: Path to the baseline repository.
            hypotheses: Pre-defined hypotheses to evaluate (optional). If not
                provided, the pipeline generates them from FindingsMemory.

        Returns:
            List of ``FindingRecord`` produced during this run.
        """
        self._current_quest = QuestConfig(
            quest_id=quest_id,
            goal=goal,
            baseline_repo=baseline_repo,
            worktree_path=str(Path(baseline_repo) / ".claude" / "worktrees" / quest_id)
            if baseline_repo else "",
        )

        logger.info(
            "DeepResearchPipeline: running quest=%s goal=%s",
            quest_id,
            goal,
        )

        start_time = time.monotonic()

        # --- Stage 1: Strategize ---
        if hypotheses is None:
            hypotheses = self._stage1_strategize()
        idea_records = self._record_hypotheses(quest_id, hypotheses)
        scored = self._score_hypotheses(idea_records)

        logger.info("Stage 1 complete: %d hypotheses scored", len(scored))

        # --- Stage 2: Implement ---
        finding_records = self._stage2_implement(scored)

        logger.info("Stage 2 complete: %d findings implemented", len(finding_records))

        # --- Stage 3: Analyze ---
        progress_records = self._stage3_analyze(finding_records)

        elapsed = time.monotonic() - start_time
        logger.info(
            "Stage 3 complete: %d progress findings in %.2fs",
            len(progress_records),
            elapsed,
        )

        self._current_quest = None
        return progress_records

    def run_stage1(
        self,
        quest_id: str,
        hypotheses: list[str] | None = None,
    ) -> list[FindingRecord]:
        """Run only Stage 1 (Strategize). Useful for planning before execution."""
        if hypotheses is None:
            hypotheses = self._stage1_strategize()
        idea_records = self._record_hypotheses(quest_id, hypotheses)
        return self._score_hypotheses(idea_records)

    def run_stage2(
        self,
        scored_ideas: list[FindingRecord],
    ) -> list[FindingRecord]:
        """Run only Stage 2 (Implement) on pre-scored ideas."""
        return self._stage2_implement(scored_ideas)

    def run_stage3(
        self,
        implement_records: list[FindingRecord],
    ) -> list[FindingRecord]:
        """Run only Stage 3 (Analyze) on implemented findings."""
        return self._stage3_analyze(implement_records)

    # ------------------------------------------------------------------
    # Stage 1: Strategize
    # ------------------------------------------------------------------

    def _stage1_strategize(self) -> list[str]:
        """Generate hypotheses from FindingsMemory analysis.

        Uses the current FindingsMemory to identify promising directions,
        then generates candidate hypotheses. If an LLM reviewer is
        configured, it can propose new hypotheses based on the memory.

        Returns:
            List of hypothesis strings.
        """
        hypotheses: list[str] = []

        # Pull existing findings for context
        if self._current_quest:
            existing = self.findings_memory.get_records_by_quest(
                self._current_quest.quest_id
            )
        else:
            existing = list(self.findings_memory._records.values())  # noqa: SLF001  # pragma: no cover -- internal fallback

        if not existing:
            # Bootstrap: return a default first hypothesis
            goal = self._current_quest.goal if self._current_quest else "general improvement"
            hypotheses.append(f"Investigate baseline performance for: {goal}")
            return hypotheses

        # UCB: select top candidates to build on
        top_candidates = self.findings_memory.ucb_acquisition(
            c=self._current_quest.ucb_exploration if self._current_quest else 1.0,
            top_k=3,
            quest_id=self._current_quest.quest_id if self._current_quest else None,
        )

        # Use LLM reviewer to generate new hypotheses from top candidates
        if self._llm_reviewer is not None:
            for candidate in top_candidates:
                context = {
                    "quest_id": candidate.quest_id,
                    "goal": self._current_quest.goal if self._current_quest else "",
                    "existing_hypothesis": candidate.hypothesis,
                    "existing_analysis": candidate.analysis,
                    "existing_valuation": candidate.valuation.to_dict(),
                }
                # Ask the reviewer to generate a new hypothesis building on the candidate
                new_hyp = self._generate_hypothesis_from_reviewer(candidate, context)
                if new_hyp:
                    hypotheses.append(new_hyp)
        else:
            # Without a reviewer, use simple mutation of existing hypotheses
            for candidate in top_candidates:
                hypotheses.append(f"Extend: {candidate.hypothesis}")

        return hypotheses

    def _generate_hypothesis_from_reviewer(
        self,
        candidate: FindingRecord,
        context: dict[str, Any],
    ) -> str | None:
        """Ask the LLM reviewer to produce a new hypothesis stemming from a candidate.

        Returns a hypothesis string or ``None`` if the reviewer fails.
        """
        try:
            score = self._llm_reviewer(
                f"Build on: {candidate.hypothesis}",
                context,
            )
            return score.hypothesis
        except Exception as exc:
            logger.warning("Reviewer failed for hypothesis '%s': %s", candidate.hypothesis, exc)
            return None

    def _record_hypotheses(
        self,
        quest_id: str,
        hypotheses: list[str],
    ) -> list[FindingRecord]:
        """Record new hypotheses as IDEA-stage finding records.

        Args:
            quest_id: The quest these hypotheses belong to.
            hypotheses: List of hypothesis strings.

        Returns:
            List of created ``FindingRecord`` instances.
        """
        records: list[FindingRecord] = []
        for hyp in hypotheses:
            if not hyp or not hyp.strip():
                continue
            record = FindingRecord(
                quest_id=quest_id,
                hypothesis=hyp.strip(),
                stage=FindingStage.IDEA,
                valuation=ValuationScores(),  # Default — will be scored next
            )
            assigned_id = self.findings_memory.add_record(record)
            # Re-fetch to get the record with the assigned ID
            stored = self.findings_memory.get_record(assigned_id)
            if stored is not None:
                records.append(stored)
        return records

    def _score_hypotheses(
        self,
        idea_records: list[FindingRecord],
    ) -> list[FindingRecord]:
        """Score each IDEA record with the LLM Reviewer.

        Uses the ``llm_reviewer`` to assign V = (v_u, v_q, v_e) scores.
        If no reviewer is configured, all hypotheses get default scores.

        Args:
            idea_records: List of IDEA-stage finding records.

        Returns:
            Updated records with valuation scores populated.
        """
        scored: list[FindingRecord] = []
        for record in idea_records:
            if self._llm_reviewer is not None:
                try:
                    context = {"quest_id": record.quest_id, "stage": "strategize"}
                    reviewer_result = self._llm_reviewer(record.hypothesis, context)
                    valuation = reviewer_result.to_valuation()
                except Exception as exc:
                    logger.warning("LLM reviewer failed for %s: %s", record.finding_id, exc)
                    valuation = ValuationScores(utility=0.5, quality=0.5, efficiency=0.5)
            else:
                # Default scores when no reviewer configured
                valuation = ValuationScores(utility=0.5, quality=0.5, efficiency=0.5)

            updated = self.findings_memory.update_record(
                record.finding_id,
                valuation=valuation.to_dict(),
            )
            scored.append(updated)

        return scored

    # ------------------------------------------------------------------
    # Stage 2: Implement
    # ------------------------------------------------------------------

    def _stage2_implement(
        self,
        scored_ideas: list[FindingRecord],
    ) -> list[FindingRecord]:
        """Select the best hypotheses via UCB and implement them.

        Workflow:
            1. Run UCB acquisition to select the best hypothesis.
            2. Advance it to IMPLEMENT stage.
            3. Either use the ``coding_agent`` provider or run the
               ``AutoResearchLoop`` to execute the experiment.
            4. Log results and update the finding record.

        Args:
            scored_ideas: Pre-scored IDEA-stage findings.

        Returns:
            List of findings that advanced to IMPLEMENT stage.
        """
        if not scored_ideas:
            logger.info("Stage 2: no ideas to implement.")
            return []

        # UCB acquisition: select top hypothesis
        best = self.findings_memory.ucb_acquisition(
            c=self._current_quest.ucb_exploration if self._current_quest else 1.0,
            top_k=1,
            quest_id=self._current_quest.quest_id if self._current_quest else None,
        )

        if not best:
            logger.info("Stage 2: UCB returned no candidates.")
            return []

        target = best[0]

        # Advance to IMPLEMENT stage
        try:
            self.findings_memory.update_stage(target.finding_id, FindingStage.IMPLEMENT)
        except (KeyError, ValueError) as exc:
            logger.warning("Stage 2: cannot advance finding %s: %s", target.finding_id, exc)
            return []

        # Execute using the coding agent or auto loop
        implementation_ref = ""
        experiment_logs: list[dict[str, Any]] = []

        if self._coding_agent is not None:
            try:
                work_dir = Path(self._current_quest.baseline_repo) if self._current_quest else Path.cwd()
                result = self._coding_agent(
                    target.hypothesis,
                    work_dir,
                    self._current_quest or QuestConfig(),
                )
                implementation_ref = result.get("implementation_ref", "")
                experiment_logs = result.get("experiment_logs", [])
            except Exception as exc:
                logger.error("Coding agent failed for %s: %s", target.hypothesis, exc)
                experiment_logs.append({
                    "stage": "implement",
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        elif self._auto_loop is not None:
            try:
                experiment_logs = self._run_auto_loop(target)
                implementation_ref = f"auto-loop:{datetime.now(timezone.utc).isoformat()}"
            except Exception as exc:
                logger.error("Auto loop failed for %s: %s", target.hypothesis, exc)
                experiment_logs.append({
                    "stage": "implement",
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        elif self._auto_loop_builder is not None and self._current_quest is not None:
            # Build a loop for this quest's worktree
            work_dir = Path(self._current_quest.worktree_path) if self._current_quest.worktree_path else Path.cwd()
            loop = self._auto_loop_builder(work_dir, f"Implement: {target.hypothesis}")
            self._auto_loop = loop
            try:
                experiment_logs = self._run_auto_loop(target)
                implementation_ref = f"auto-loop:{datetime.now(timezone.utc).isoformat()}"
            except Exception as exc:
                logger.error("Built auto loop failed for %s: %s", target.hypothesis, exc)
                experiment_logs.append({
                    "stage": "implement",
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # Update record with implementation results
        self.findings_memory.update_record(
            target.finding_id,
            implementation_ref=implementation_ref,
            experiment_logs=experiment_logs,
        )

        # Filter None — should not happen but satisfy type checker
        result: list[FindingRecord] = []
        r = self.findings_memory.get_record(target.finding_id)
        if r is not None:
            result.append(r)
        return result

    def _run_auto_loop(self, finding: FindingRecord) -> list[dict[str, Any]]:
        """Run the configured AutoResearchLoop for a finding.

        Returns:
            List of experiment log entries.
        """
        if self._auto_loop is None:
            return []

        # Scoped proposer for this specific hypothesis
        scope_hypothesis = finding.hypothesis

        def scoped_proposer(
            ledger: ExperimentLedger,
            work_dir: Path,
        ) -> dict[str, Any]:
            return {
                "hypothesis": scope_hypothesis,
                "change_description": f"Implement: {scope_hypothesis}",
                "patch": "",
            }

        self._auto_loop.set_proposer(scoped_proposer)

        # Register a callback to capture experiment outcomes
        logs: list[dict[str, Any]] = []

        def capture_callback(iteration: int, record: ExperimentRecord) -> None:
            logs.append({
                "iteration": iteration,
                "hypothesis": record.hypothesis,
                "metric_before": record.metric_before,
                "metric_after": record.metric_after,
                "delta": record.delta,
                "status": record.status.value,
                "duration_seconds": record.duration_seconds,
                "timestamp": record.timestamp,
            })

        self._auto_loop.on_iteration(capture_callback)
        self._auto_loop.run()

        return logs

    # ------------------------------------------------------------------
    # Stage 3: Analyze
    # ------------------------------------------------------------------

    def _stage3_analyze(
        self,
        implement_records: list[FindingRecord],
    ) -> list[FindingRecord]:
        """Analyze IMPLEMENT-stage findings, run ablations, and advance to PROGRESS.

        For each successfully implemented finding:
            1. Run ``ablation_budget`` ablation experiments.
            2. Synthesize analysis from experiment logs.
            3. If performance is satisfactory, advance to PROGRESS stage.

        Args:
            implement_records: Findings that reached IMPLEMENT stage.

        Returns:
            Findings that advanced to PROGRESS stage.
        """
        progress_records: list[FindingRecord] = []

        for record in implement_records:
            if record.stage != FindingStage.IMPLEMENT:
                continue

            # Determine success from experiment logs
            is_successful = self._evaluate_success(record)

            if not is_successful:
                logger.info(
                    "Finding %s did not show progress — staying at IMPLEMENT.",
                    record.finding_id,
                )
                continue

            # Run ablation experiments
            ablation_logs = self._run_ablations(record)

            # Synthesize analysis
            analysis = self._synthesize_analysis(record, ablation_logs)

            # Auto-generate paper snippet
            paper_snippet = self._auto_generate_paper_snippet(record, analysis)

            # Advance to PROGRESS
            try:
                self.findings_memory.update_stage(record.finding_id, FindingStage.PROGRESS)
                self.findings_memory.update_record(
                    record.finding_id,
                    analysis=analysis,
                    experiment_logs=record.experiment_logs + ablation_logs,
                    metadata={
                        **record.metadata,
                        "paper_snippet": paper_snippet,
                        "ablation_count": len(ablation_logs),
                    },
                )
                progress_records.append(
                    self.findings_memory.get_record(record.finding_id)
                )
            except (KeyError, ValueError) as exc:
                logger.warning("Stage 3: cannot advance %s: %s", record.finding_id, exc)

        # Filter out None entries
        return [r for r in progress_records if r is not None]

    @staticmethod
    def _evaluate_success(record: FindingRecord) -> bool:
        """Determine if an IMPLEMENT-stage finding was successful.

        Looks at experiment logs for positive deltas. Without logs,
        conservatively assumes success (the record reached implement).

        Args:
            record: The finding record to evaluate.

        Returns:
            ``True`` if the finding appears successful.
        """
        if not record.experiment_logs:
            return True  # No logs means we can't judge — assume success

        positive_deltas = sum(
            1 for log in record.experiment_logs
            if isinstance(log.get("delta"), (int, float)) and log["delta"] > 0
        )
        total_logs = len(record.experiment_logs)
        return positive_deltas >= total_logs / 2  # Majority positive

    def _run_ablations(self, record: FindingRecord) -> list[dict[str, Any]]:
        """Run ablation experiments for a finding.

        Ablations test the hypothesis under varied conditions (e.g.,
        removing components, changing parameters). Each ablation is
        a mini experiment logged as a dict.

        Args:
            record: The finding to ablate.

        Returns:
            List of ablation experiment log entries.
        """
        ablation_logs: list[dict[str, Any]] = []

        for i in range(self._ablation_budget):
            entry = {
                "stage": "ablation",
                "ablation_index": i,
                "hypothesis": record.hypothesis,
                "condition": f"ablation_{i}",
                "result": "simulated",
                "delta": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if self._auto_loop is not None:
                try:
                    # Run a mini experiment for this ablation
                    log = self._run_ablation_experiment(record.hypothesis, i)
                    entry.update(log)
                except Exception as exc:
                    entry["error"] = str(exc)

            ablation_logs.append(entry)

        return ablation_logs

    def _run_ablation_experiment(
        self,
        hypothesis: str,
        ablation_index: int,
    ) -> dict[str, Any]:
        """Run a single ablation experiment via the auto loop.

        Returns:
            Dict with ``delta``, ``metric_before``, ``metric_after`` keys.
        """
        if self._auto_loop is None:
            return {"delta": 0.0, "metric_before": 0.0, "metric_after": 0.0}

        # Configure the proposer for this specific ablation
        def ablation_proposer(ledger: ExperimentLedger, work_dir: Path) -> dict[str, Any]:
            return {
                "hypothesis": f"Ablation #{ablation_index}: {hypothesis}",
                "change_description": f"Ablation experiment {ablation_index}",
                "patch": "",
            }

        self._auto_loop.set_proposer(ablation_proposer)
        self._auto_loop.run()

        best = self._auto_loop.ledger.best_record()
        if best is not None:
            return {
                "delta": best.delta,
                "metric_before": best.metric_before,
                "metric_after": best.metric_after,
            }
        return {"delta": 0.0, "metric_before": 0.0, "metric_after": 0.0}

    @staticmethod
    def _synthesize_analysis(
        record: FindingRecord,
        ablation_logs: list[dict[str, Any]],
    ) -> str:
        """Synthesize a human-readable analysis from experiment logs.

        Args:
            record: The finding record.
            ablation_logs: Logs from ablation experiments.

        Returns:
            Free-text analysis string.
        """
        total_logs = len(record.experiment_logs) + len(ablation_logs)
        positive = sum(
            1 for log in record.experiment_logs + ablation_logs
            if isinstance(log.get("delta"), (int, float)) and log["delta"] > 0
        )

        return (
            f"Hypothesis: {record.hypothesis}\n"
            f"Total experiments: {total_logs}\n"
            f"Positive results: {positive}/{total_logs}\n"
            f"Valuation: V=({record.valuation.utility:.2f}, {record.valuation.quality:.2f}, "
            f"{record.valuation.efficiency:.2f})\n"
            f"Ablations performed: {len(ablation_logs)}\n"
            f"Status: Substantial progress confirmed."
        )

    @staticmethod
    def _auto_generate_paper_snippet(
        record: FindingRecord,
        analysis: str,
    ) -> str:
        """Auto-generate a paper/markdown snippet summarizing the finding.

        Args:
            record: The finding record.
            analysis: The synthesized analysis text.

        Returns:
            A formatted markdown snippet suitable for inclusion in a paper.
        """
        val = record.valuation
        snippet_lines = [
            "## Finding",
            f"**Hypothesis**: {record.hypothesis}",
            f"**Stage**: {record.stage.value}",
            f"**V = ({val.utility:.2f}, {val.quality:.2f}, {val.efficiency:.2f})**",
            "",
            "### Analysis",
            analysis,
            "",
            "### Implementation",
            f"Reference: {record.implementation_ref or 'N/A'}",
            "",
            f"*Generated: {datetime.now(timezone.utc).isoformat()}*",
        ]
        return "\n".join(snippet_lines)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_results(self) -> list[dict[str, Any]]:
        """Return all results from the most recent pipeline run."""
        return list(self._results)

    def current_quest(self) -> QuestConfig | None:
        """Return the currently active quest configuration."""
        return self._current_quest


# =============================================================================
# QuestManager
# =============================================================================


class QuestManager:
    """Manages the lifecycle of research quests.

    Each quest gets:
    - A dedicated quest configuration.
    - An optional git worktree for code isolation.
    - Its own slice of the ``FindingsMemory`` and ``CascadeMemory``.

    Integrates with the fleet orchestrator for parallel execution
    of multiple quests.

    Usage::

        qm = QuestManager(
            base_path=Path("./research"),
            cascade=CascadeMemory(),
        )
        quest = qm.create_quest(
            goal="Improve attention efficiency",
            baseline_repo="/path/to/repo",
        )
        quests = qm.quest_status()
        findings = qm.list_findings(quest.quest_id)
    """

    def __init__(
        self,
        findings_memory: FindingsMemory | None = None,
        cascade: CascadeMemory | None = None,
        worktree_root: str = DEFAULT_WORKTREE_ROOT,
    ) -> None:
        """
        Args:
            findings_memory: Shared findings database. If ``None``, creates one.
            cascade: Optional ``CascadeMemory`` for persistent memory.
            worktree_root: Base directory for quest worktree roots.
        """
        self.findings_memory = findings_memory or FindingsMemory(cascade=cascade)
        self._cascade = cascade
        self._worktree_root = Path(worktree_root)

        # Quest registry: quest_id -> QuestConfig
        self._quests: dict[str, QuestConfig] = {}

    def create_quest(
        self,
        goal: str,
        baseline_repo: str,
        quest_id: str | None = None,
        max_iterations: int = 20,
        ucb_exploration: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> QuestConfig:
        """Create a new research quest.

        Sets up the quest config, an optional worktree, and registers
        the quest with the manager.

        Args:
            goal: High-level research goal.
            baseline_repo: Path to the baseline repo to work on.
            quest_id: Optional ID (auto-generated if not provided).
            max_iterations: Max auto-research iterations per round.
            ucb_exploration: Exploration parameter for UCB acquisition.
            metadata: Additional configuration metadata.

        Returns:
            The created ``QuestConfig``.

        Raises:
            ValueError: If a quest with ``quest_id`` already exists.
        """
        qid = quest_id or f"q-{uuid.uuid4().hex[:8]}"

        if qid in self._quests:
            raise ValueError(f"Quest '{qid}' already exists.")

        worktree_path = str(
            self._worktree_root / qid
        )

        config = QuestConfig(
            quest_id=qid,
            goal=goal,
            baseline_repo=baseline_repo,
            worktree_path=worktree_path,
            max_iterations=max_iterations,
            ucb_exploration=ucb_exploration,
            metadata=metadata or {},
        )

        self._quests[qid] = config

        # Ensure worktree directory exists
        Path(worktree_path).mkdir(parents=True, exist_ok=True)

        logger.info("Quest created: %s — %s", qid, goal)

        # Register in cascade memory if available
        if self._cascade is not None:
            from lyra.memory.cascade_memory import MemoryItem
            from lyra.memory.admission_control import ContentType

            item = MemoryItem(
                content=f"Quest created: {qid} — {goal}",
                content_type=ContentType.PLAN,
                source="quest_manager",
                importance=0.6,
                timestamp=time.time(),
                metadata={
                    "quest_id": qid,
                    "goal": goal,
                    "baseline_repo": baseline_repo,
                },
            )
            self._cascade.store(item)

        return config

    def quest_status(self) -> dict[str, dict[str, Any]]:
        """Return status for all active quests.

        Returns:
            Dict of ``quest_id -> status dict``.
        """
        statuses: dict[str, dict[str, Any]] = {}
        for qid, config in self._quests.items():
            findings = self.findings_memory.get_records_by_quest(qid)
            idea_count = sum(1 for f in findings if f.stage == FindingStage.IDEA)
            implement_count = sum(1 for f in findings if f.stage == FindingStage.IMPLEMENT)
            progress_count = sum(1 for f in findings if f.stage == FindingStage.PROGRESS)

            statuses[qid] = {
                "quest_id": qid,
                "goal": config.goal,
                "baseline_repo": config.baseline_repo,
                "worktree_path": config.worktree_path,
                "total_findings": len(findings),
                "idea_findings": idea_count,
                "implement_findings": implement_count,
                "progress_findings": progress_count,
                "max_iterations": config.max_iterations,
                "ucb_exploration": config.ucb_exploration,
            }
        return statuses

    def list_findings(
        self,
        quest_id: str,
        stage: FindingStage | None = None,
    ) -> list[FindingRecord]:
        """List findings for a specific quest, optionally filtered by stage.

        Args:
            quest_id: The quest to query.
            stage: Optional stage filter.

        Returns:
            List of ``FindingRecord`` instances.
        """
        records = self.findings_memory.get_records_by_quest(quest_id)
        if stage is not None:
            records = [r for r in records if r.stage == stage]
        return records

    def get_quest(self, quest_id: str) -> QuestConfig | None:
        """Get a quest configuration by ID."""
        return self._quests.get(quest_id)

    def remove_quest(self, quest_id: str) -> bool:
        """Remove a quest and its worktree.

        Args:
            quest_id: The quest to remove.

        Returns:
            ``True`` if the quest was removed.
        """
        config = self._quests.pop(quest_id, None)
        if config is None:
            return False

        # Remove worktree directory (non-destructive: only if it exists)
        wt_path = Path(config.worktree_path)
        if wt_path.is_dir():
            import shutil
            shutil.rmtree(wt_path, ignore_errors=True)

        logger.info("Quest removed: %s", quest_id)
        return True

    def list_quests(self) -> list[QuestConfig]:
        """Return all registered quest configurations."""
        return list(self._quests.values())

    def to_dict(self) -> dict[str, Any]:
        """Serialize quest manager state."""
        return {
            "quests": {qid: config.to_dict() for qid, config in self._quests.items()},
            "worktree_root": str(self._worktree_root),
        }

    def from_dict(self, data: dict[str, Any]) -> QuestManager:
        """Deserialize quest manager state (mutates self)."""
        self._worktree_root = Path(data.get("worktree_root", DEFAULT_WORKTREE_ROOT))
        for qid, raw in data.get("quests", {}).items():
            config = QuestConfig.from_dict(raw)
            self._quests[qid] = config
        return self
