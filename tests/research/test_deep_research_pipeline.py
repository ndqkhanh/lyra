"""
Unit tests for the DeepResearchPipeline and QuestManager modules.
Mocks FindingsMemory, AutoResearchLoop, CascadeMemory, and all provider callbacks.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timezone

import pytest

from lyra.research.findings_memory import (
    DEFAULT_VALUATION_WEIGHTS,
    FindingsMemory,
    FindingRecord,
    FindingStage,
    ValuationScores,
)
from lyra.research.deep_research_pipeline import (
    DeepResearchPipeline,
    QuestConfig,
    QuestManager,
    ReviewerDimension,
    ReviewerScore,
)


# =============================================================================
# ReviewerScore
# =============================================================================

class TestReviewerScore:
    def test_creation(self) -> None:
        rs = ReviewerScore(
            hypothesis="Test hypothesis",
            utility=0.8,
            quality=0.7,
            efficiency=0.9,
            reasoning="Solid approach",
            reviewer_id="reviewer-1",
        )
        assert rs.hypothesis == "Test hypothesis"
        assert rs.utility == 0.8
        assert rs.quality == 0.7
        assert rs.efficiency == 0.9

    def test_to_valuation(self) -> None:
        rs = ReviewerScore(
            hypothesis="Test", utility=0.6, quality=0.5, efficiency=0.4,
        )
        v = rs.to_valuation()
        assert v.utility == 0.6
        assert v.quality == 0.5
        assert v.efficiency == 0.4


# =============================================================================
# ReviewerDimension
# =============================================================================

class TestReviewerDimension:
    def test_values(self) -> None:
        assert ReviewerDimension.UTILITY.value == "utility"
        assert ReviewerDimension.QUALITY.value == "quality"
        assert ReviewerDimension.EFFICIENCY.value == "efficiency"


# =============================================================================
# QuestConfig
# =============================================================================

class TestQuestConfig:
    def test_defaults(self) -> None:
        qc = QuestConfig()
        assert qc.quest_id == ""
        assert qc.max_iterations == 20
        assert qc.ucb_exploration == 1.0

    def test_to_dict(self) -> None:
        qc = QuestConfig(
            quest_id="q-001", goal="Test goal",
            baseline_repo="/repo", worktree_path="/repo/.claude/worktrees/q-001",
        )
        d = qc.to_dict()
        assert d["quest_id"] == "q-001"
        assert d["goal"] == "Test goal"
        assert d["baseline_repo"] == "/repo"

    def test_from_dict(self) -> None:
        d = {
            "quest_id": "q-002",
            "goal": "Another goal",
            "baseline_repo": "/repo2",
            "worktree_path": "/wt",
            "max_iterations": 10,
            "ucb_exploration": 0.5,
            "metadata": {"key": "val"},
        }
        qc = QuestConfig.from_dict(d)
        assert qc.quest_id == "q-002"
        assert qc.goal == "Another goal"
        assert qc.max_iterations == 10
        assert qc.ucb_exploration == 0.5
        assert qc.metadata["key"] == "val"

    def test_from_dict_empty(self) -> None:
        qc = QuestConfig.from_dict({})
        assert qc.quest_id == ""
        assert qc.max_iterations == 20


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_findings() -> FindingsMemory:
    fm = MagicMock(spec=FindingsMemory)
    # Some internal code accesses ._records directly as a fallback
    fm._records = {}
    return fm


@pytest.fixture
def mock_auto_loop() -> MagicMock:
    loop = MagicMock()
    loop.ledger = MagicMock()
    loop.ledger.best_record.return_value = None
    return loop


def make_reviewer(utility=0.8, quality=0.7, efficiency=0.6, hypothesis="reviewer_hyp"):
    """Create a reviewer callable that returns fixed ReviewerScore."""
    def reviewer(hyp: str, ctx: dict) -> ReviewerScore:
        return ReviewerScore(
            hypothesis=hypothesis or hyp,
            utility=utility,
            quality=quality,
            efficiency=efficiency,
            reasoning="auto test",
        )
    return reviewer


def make_coding_agent(result: dict | None = None) -> MagicMock:
    agent = MagicMock()
    agent.return_value = result or {
        "implementation_ref": "ref-1",
        "experiment_logs": [],
    }
    return agent


# =============================================================================
# DeepResearchPipeline
# =============================================================================

MINIMAL_RECORD = FindingRecord(
    finding_id="f-1",
    quest_id="q-001",
    hypothesis="Test hypothesis",
    stage=FindingStage.IDEA,
    valuation=ValuationScores(utility=0.8, quality=0.7, efficiency=0.6),
    experiment_logs=[],
    analysis="",
)


class TestDeepResearchPipelineInit:
    def test_default_creation(self, mock_findings) -> None:
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        assert pipe.findings_memory is mock_findings
        assert pipe._auto_loop is None
        assert pipe._llm_reviewer is None
        assert pipe._coding_agent is None
        assert pipe._ablation_budget == 5
        assert pipe._valuation_weights is not None

    def test_custom_valuation_weights(self, mock_findings) -> None:
        weights = {"utility": 0.5, "quality": 0.3, "efficiency": 0.2}
        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            valuation_weights=weights,
        )
        assert pipe._valuation_weights == weights


class TestDeepResearchPipelineRun:
    def test_run_with_hypotheses(self, mock_findings, mock_auto_loop) -> None:
        mock_findings.add_record.return_value = "f-1"
        mock_findings.get_record.return_value = MINIMAL_RECORD
        mock_findings.update_record.return_value = MINIMAL_RECORD
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage = MagicMock()

        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            auto_loop=mock_auto_loop,
        )
        results = pipe.run(
            quest_id="q-001",
            goal="Test run",
            hypotheses=["H1", "H2"],
        )
        assert isinstance(results, list)

    def test_run_without_hypotheses_uses_existing(self, mock_findings, mock_auto_loop) -> None:
        mock_findings.get_records_by_quest.return_value = []
        mock_findings.add_record.return_value = "f-1"
        mock_findings.get_record.return_value = MINIMAL_RECORD
        mock_findings.update_record.return_value = MINIMAL_RECORD
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage = MagicMock()

        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            auto_loop=mock_auto_loop,
        )
        results = pipe.run(quest_id="q-001", goal="Test")
        assert isinstance(results, list)


class TestDeepResearchPipelineStage1:
    def test_stage1_bootstrap_no_existing(self, mock_findings) -> None:
        mock_findings.get_records_by_quest.return_value = []
        mock_findings.add_record.return_value = "f-1"
        mock_findings.get_record.return_value = MINIMAL_RECORD
        mock_findings.update_record.return_value = MINIMAL_RECORD

        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage1(quest_id="q-001")
        # Should bootstrap with one default hypothesis
        assert len(results) >= 1

    def test_stage1_with_hypotheses(self, mock_findings) -> None:
        mock_findings.add_record.return_value = "f-1"
        mock_findings.get_record.return_value = MINIMAL_RECORD
        mock_findings.update_record.return_value = MINIMAL_RECORD

        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage1(quest_id="q-001", hypotheses=["H1", "H2"])
        assert len(results) == 2

    def test_stage1_with_reviewer(self, mock_findings) -> None:
        record = FindingRecord(
            finding_id="f-1", quest_id="q-001",
            hypothesis="Existing hyp",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(0.8, 0.7, 0.6),
            experiment_logs=[], analysis="",
        )
        mock_findings.get_records_by_quest.return_value = [record]
        mock_findings.ucb_acquisition.return_value = [record]
        mock_findings.add_record.return_value = "f-2"
        mock_findings.get_record.side_effect = [
            FindingRecord(
                finding_id="f-2", quest_id="q-001",
                hypothesis="New hyp",
                stage=FindingStage.IDEA,
                valuation=ValuationScores(0.5, 0.5, 0.5),
                experiment_logs=[], analysis="",
            ),
        ]
        mock_findings.update_record.return_value = record

        reviewer = make_reviewer(hypothesis="Reviewer generated hyp")
        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            llm_reviewer=reviewer,
        )
        results = pipe.run_stage1(quest_id="q-001")
        assert len(results) >= 1

    def test_stage1_reviewer_failure(self, mock_findings) -> None:
        record = FindingRecord(
            finding_id="f-1", quest_id="q-001",
            hypothesis="Existing hyp",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(0.8, 0.7, 0.6),
            experiment_logs=[], analysis="",
        )
        mock_findings.get_records_by_quest.return_value = [record]
        mock_findings.ucb_acquisition.return_value = [record]
        mock_findings.add_record.return_value = "f-2"
        mock_findings.get_record.return_value = FindingRecord(
            finding_id="f-2", quest_id="q-001",
            hypothesis="Fallback hyp",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(0.5, 0.5, 0.5),
            experiment_logs=[], analysis="",
        )
        mock_findings.update_record.return_value = record

        def failing_reviewer(hyp, ctx):
            raise RuntimeError("LLM down")
        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            llm_reviewer=failing_reviewer,
        )
        results = pipe.run_stage1(quest_id="q-001")
        # Should still work, just no reviewer-generated hypothesis
        assert isinstance(results, list)

    def test_stage1_empty_hypotheses_skipped(self, mock_findings) -> None:
        mock_findings.add_record.return_value = "f-1"
        mock_findings.get_record.return_value = MINIMAL_RECORD
        mock_findings.update_record.return_value = MINIMAL_RECORD

        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage1(quest_id="q-001", hypotheses=["", "  ", "valid"])
        assert len(results) == 1  # only "valid" recorded


class TestDeepResearchPipelineStage2:
    def test_stage2_empty_ideas(self, mock_findings) -> None:
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage2([])
        assert results == []

    def test_stage2_ucb_returns_none(self, mock_findings) -> None:
        mock_findings.ucb_acquisition.return_value = []
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage2([MINIMAL_RECORD])
        assert results == []

    def test_stage2_with_coding_agent(self, mock_findings) -> None:
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage = MagicMock()
        mock_findings.update_record.return_value = MINIMAL_RECORD
        mock_findings.get_record.return_value = MINIMAL_RECORD

        agent = make_coding_agent({"implementation_ref": "abc", "experiment_logs": []})
        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            coding_agent=agent,
        )
        results = pipe.run_stage2([MINIMAL_RECORD])
        assert len(results) == 1

    def test_stage2_coding_agent_failure(self, mock_findings) -> None:
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage = MagicMock()
        mock_findings.update_record.return_value = MINIMAL_RECORD
        mock_findings.get_record.return_value = MINIMAL_RECORD

        def failing_agent(hyp, work_dir, quest_config):
            raise RuntimeError("Experiment crashed")
        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            coding_agent=failing_agent,
        )
        results = pipe.run_stage2([MINIMAL_RECORD])
        assert len(results) == 1

    def test_stage2_update_stage_failure(self, mock_findings) -> None:
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage.side_effect = ValueError("Cannot advance")
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage2([MINIMAL_RECORD])
        assert results == []

    def test_stage2_with_auto_loop(self, mock_findings, mock_auto_loop) -> None:
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage = MagicMock()
        mock_findings.update_record.return_value = MINIMAL_RECORD
        mock_findings.get_record.return_value = MINIMAL_RECORD

        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            auto_loop=mock_auto_loop,
        )
        results = pipe.run_stage2([MINIMAL_RECORD])
        assert len(results) == 1

    def test_stage2_with_auto_loop_builder(self, mock_findings, mock_auto_loop) -> None:
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage = MagicMock()
        mock_findings.update_record.return_value = MINIMAL_RECORD
        mock_findings.get_record.return_value = MINIMAL_RECORD

        builder = MagicMock(return_value=mock_auto_loop)
        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            auto_loop_builder=builder,
        )
        results = pipe.run_stage2([MINIMAL_RECORD])
        assert len(results) == 1

    def test_stage2_auto_loop_failure(self, mock_findings, mock_auto_loop) -> None:
        mock_findings.ucb_acquisition.return_value = [MINIMAL_RECORD]
        mock_findings.update_stage = MagicMock()
        mock_findings.update_record.return_value = MINIMAL_RECORD
        mock_findings.get_record.return_value = MINIMAL_RECORD

        mock_auto_loop.set_proposer = MagicMock()
        mock_auto_loop.on_iteration = MagicMock()
        mock_auto_loop.run.side_effect = RuntimeError("Loop failed")

        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            auto_loop=mock_auto_loop,
        )
        results = pipe.run_stage2([MINIMAL_RECORD])
        assert len(results) == 1


class TestDeepResearchPipelineStage3:
    def test_stage3_skip_non_implement(self, mock_findings) -> None:
        record = FindingRecord(
            finding_id="f-1", quest_id="q-001",
            hypothesis="Idea only",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(0.5, 0.5, 0.5),
            experiment_logs=[], analysis="",
        )
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage3([record])
        assert results == []

    def test_stage3_unsuccessful_stays(self, mock_findings) -> None:
        record = FindingRecord(
            finding_id="f-1", quest_id="q-001",
            hypothesis="Bad hyp",
            stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(0.5, 0.5, 0.5),
            experiment_logs=[{"delta": -0.5}, {"delta": -0.3}],
            analysis="",
        )
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        results = pipe.run_stage3([record])
        assert results == []

    def test_stage3_successful_advances(self, mock_findings) -> None:
        record = FindingRecord(
            finding_id="f-1", quest_id="q-001",
            hypothesis="Good hyp",
            stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(0.8, 0.8, 0.8),
            experiment_logs=[{"delta": 0.5}, {"delta": 0.3}],
            analysis="",
            metadata={},
        )
        mock_findings.update_stage = MagicMock()
        mock_findings.update_record.return_value = record
        mock_findings.get_record.return_value = record

        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            ablation_budget=2,
        )
        results = pipe.run_stage3([record])
        assert len(results) == 1

    def test_stage3_update_stage_failure(self, mock_findings) -> None:
        record = FindingRecord(
            finding_id="f-1", quest_id="q-001",
            hypothesis="Good hyp",
            stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(0.8, 0.8, 0.8),
            experiment_logs=[{"delta": 0.5}],
            analysis="",
            metadata={},
        )
        mock_findings.update_stage.side_effect = ValueError("Cannot advance")
        mock_findings.update_record.return_value = record

        pipe = DeepResearchPipeline(
            findings_memory=mock_findings,
            ablation_budget=1,
        )
        results = pipe.run_stage3([record])
        assert results == []

    def test_evaluate_success_no_logs(self) -> None:
        record = FindingRecord(
            hypothesis="Test", stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(),
            experiment_logs=[],
        )
        assert DeepResearchPipeline._evaluate_success(record) is True

    def test_evaluate_success_mixed_logs(self) -> None:
        record = FindingRecord(
            hypothesis="Test", stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(),
            experiment_logs=[{"delta": 0.1}, {"delta": -0.2}, {"delta": 0.3}],
        )
        assert DeepResearchPipeline._evaluate_success(record) is True

    def test_evaluate_success_mostly_negative(self) -> None:
        record = FindingRecord(
            hypothesis="Test", stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(),
            experiment_logs=[{"delta": -0.5}, {"delta": -0.3}],
        )
        assert DeepResearchPipeline._evaluate_success(record) is False

    def test_synthesize_analysis(self) -> None:
        record = FindingRecord(
            hypothesis="Test hyp",
            stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(utility=0.9, quality=0.8, efficiency=0.7),
            experiment_logs=[{"delta": 0.5}],
        )
        analysis = DeepResearchPipeline._synthesize_analysis(record, [])
        assert "Test hyp" in analysis
        assert "0.90" in analysis or "0.9" in analysis

    def test_auto_generate_paper_snippet(self) -> None:
        record = FindingRecord(
            hypothesis="Paper test",
            stage=FindingStage.PROGRESS,
            valuation=ValuationScores(0.7, 0.6, 0.5),
            implementation_ref="git:abc123",
        )
        snippet = DeepResearchPipeline._auto_generate_paper_snippet(record, "analysis text")
        assert "## Finding" in snippet
        assert "Paper test" in snippet
        assert "git:abc123" in snippet


class TestDeepResearchPipelineAccessors:
    def test_get_results(self, mock_findings) -> None:
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        assert pipe.get_results() == []

    def test_current_quest(self, mock_findings) -> None:
        pipe = DeepResearchPipeline(findings_memory=mock_findings)
        assert pipe.current_quest() is None


# =============================================================================
# QuestManager
# =============================================================================

class TestQuestManager:
    def test_init(self) -> None:
        qm = QuestManager()
        assert qm._worktree_root.name == "research"

    def test_init_with_cascade(self) -> None:
        cascade = MagicMock()
        qm = QuestManager(cascade=cascade)
        assert qm._cascade is cascade

    def test_create_quest(self) -> None:
        qm = QuestManager()
        qc = qm.create_quest(goal="Test goal", baseline_repo="/repo")
        assert qc.quest_id.startswith("q-")
        assert qc.goal == "Test goal"
        assert qc.baseline_repo == "/repo"
        assert qc.quest_id in qm._quests

    def test_create_quest_with_id(self) -> None:
        qm = QuestManager()
        qc = qm.create_quest(goal="Goal", baseline_repo="/repo", quest_id="q-fixed")
        assert qc.quest_id == "q-fixed"

    def test_create_quest_duplicate_raises(self) -> None:
        qm = QuestManager()
        qm.create_quest(goal="G1", baseline_repo="/r", quest_id="q-dup")
        with pytest.raises(ValueError, match="already exists"):
            qm.create_quest(goal="G2", baseline_repo="/r2", quest_id="q-dup")

    def test_quest_status(self) -> None:
        qm = QuestManager()
        qm.create_quest(goal="G1", baseline_repo="/r", quest_id="q-1")
        statuses = qm.quest_status()
        assert "q-1" in statuses
        assert statuses["q-1"]["goal"] == "G1"
        assert statuses["q-1"]["total_findings"] == 0

    def test_list_findings(self) -> None:
        qm = QuestManager()
        findings = qm.list_findings("nonexistent")
        assert findings == []

    def test_list_findings_by_stage(self) -> None:
        qm = QuestManager()
        findings = qm.list_findings("nonexistent", stage=FindingStage.IDEA)
        assert findings == []

    def test_get_quest(self) -> None:
        qm = QuestManager()
        qm.create_quest(goal="G", baseline_repo="/r", quest_id="q-1")
        qc = qm.get_quest("q-1")
        assert qc is not None
        assert qc.goal == "G"

    def test_get_quest_not_found(self) -> None:
        qm = QuestManager()
        assert qm.get_quest("nonexistent") is None

    def test_remove_quest(self) -> None:
        qm = QuestManager()
        qm.create_quest(goal="G", baseline_repo="/r", quest_id="q-rm")
        assert qm.remove_quest("q-rm") is True
        assert qm.get_quest("q-rm") is None

    def test_remove_quest_not_found(self) -> None:
        qm = QuestManager()
        assert qm.remove_quest("nonexistent") is False

    def test_list_quests(self) -> None:
        qm = QuestManager()
        qm.create_quest(goal="G1", baseline_repo="/r1", quest_id="q-1")
        qm.create_quest(goal="G2", baseline_repo="/r2", quest_id="q-2")
        quests = qm.list_quests()
        assert len(quests) == 2

    def test_to_dict(self) -> None:
        qm = QuestManager()
        qm.create_quest(goal="G", baseline_repo="/r", quest_id="q-1")
        d = qm.to_dict()
        assert "quests" in d
        assert "q-1" in d["quests"]

    def test_from_dict(self) -> None:
        qm = QuestManager()
        data = {
            "worktree_root": "/tmp/wt",
            "quests": {
                "q-1": {
                    "quest_id": "q-1",
                    "goal": "G",
                    "baseline_repo": "/r",
                    "worktree_path": "/wt/q-1",
                    "max_iterations": 20,
                    "ucb_exploration": 1.0,
                    "metadata": {},
                },
            },
        }
        qm.from_dict(data)
        assert qm.get_quest("q-1") is not None
        assert qm._worktree_root == Path("/tmp/wt")

    def test_from_dict_empty(self) -> None:
        qm = QuestManager()
        qm.from_dict({})
        assert qm._worktree_root.name == "research"
