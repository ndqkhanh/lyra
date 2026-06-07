"""Tests for DeepScientist-fused auto-research pipeline (P7)."""

import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.research.findings_memory import (
    DEFAULT_UCB_EXPLORATION,
    FindingRecord,
    FindingsMemory,
    FindingStage,
    ValuationScores,
)
from lyra.research.deep_research_pipeline import (
    DeepResearchPipeline,
    QuestConfig,
    QuestManager,
    ReviewerScore,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def empty_memory() -> FindingsMemory:
    """An empty FindingsMemory for testing."""
    return FindingsMemory()


@pytest.fixture
def populated_memory() -> FindingsMemory:
    """A FindingsMemory pre-loaded with sample records."""
    fm = FindingsMemory()
    fm.add_record(FindingRecord(
        quest_id="q-001",
        hypothesis="Attention sparsity reduces inference cost by 2x",
        stage=FindingStage.IDEA,
        valuation=ValuationScores(utility=0.8, quality=0.6, efficiency=0.9),
    ))
    fm.add_record(FindingRecord(
        quest_id="q-001",
        hypothesis="Mixture of experts reduces memory bandwidth",
        stage=FindingStage.IMPLEMENT,
        valuation=ValuationScores(utility=0.7, quality=0.8, efficiency=0.5),
    ))
    fm.add_record(FindingRecord(
        quest_id="q-001",
        hypothesis="KV cache quantization degrades quality above 4-bit",
        stage=FindingStage.PROGRESS,
        valuation=ValuationScores(utility=0.9, quality=0.85, efficiency=0.7),
        implementation_ref="abc123",
        experiment_logs=[
            {"iteration": 1, "delta": 0.12, "status": "KEPT"},
        ],
    ))
    fm.add_record(FindingRecord(
        quest_id="q-002",
        hypothesis="Flash attention reduces memory usage",
        stage=FindingStage.IDEA,
        valuation=ValuationScores(utility=0.6, quality=0.5, efficiency=0.8),
    ))
    return fm


@pytest.fixture
def reviewer_mock() -> MagicMock:
    """A mock LLM reviewer that returns deterministic scores."""
    def review(hypothesis: str, context: dict) -> ReviewerScore:
        return ReviewerScore(
            hypothesis=f"Refined: {hypothesis}",
            utility=0.75,
            quality=0.65,
            efficiency=0.85,
            reasoning="Promising direction based on literature.",
        )
    return MagicMock(side_effect=review)


# =============================================================================
# Test: ValuationScores
# =============================================================================


class TestValuationScores:
    """Test the DeepScientist V = (v_u, v_q, v_e) data structure."""

    def test_default_values(self):
        v = ValuationScores()
        assert v.utility == 0.5
        assert v.quality == 0.5
        assert v.efficiency == 0.5

    def test_clamping(self):
        v = ValuationScores(utility=1.5, quality=-0.1, efficiency=0.5)
        assert v.utility == 1.0
        assert v.quality == 0.0
        assert v.efficiency == 0.5

    def test_combined_default_weights(self):
        v = ValuationScores(utility=1.0, quality=1.0, efficiency=1.0)
        assert v.combined() == 1.0  # All weights sum to 1.0

    def test_combined_custom_weights(self):
        v = ValuationScores(utility=0.5, quality=0.5, efficiency=0.5)
        # With equal weights = each gives 0.5*(1/3) contribution
        result = v.combined({"utility": 0.33, "quality": 0.33, "efficiency": 0.34})
        assert result == pytest.approx(0.5, abs=0.01)

    def test_to_dict_roundtrip(self):
        v = ValuationScores(utility=0.8, quality=0.6, efficiency=0.9)
        d = v.to_dict()
        v2 = ValuationScores.from_dict(d)
        assert v2.utility == v.utility
        assert v2.quality == v.quality
        assert v2.efficiency == v.efficiency


# =============================================================================
# Test: FindingRecord
# =============================================================================


class TestFindingRecord:
    """Test the FindingRecord data structure."""

    def test_default_stage_is_idea(self):
        r = FindingRecord()
        assert r.stage == FindingStage.IDEA

    def test_to_dict_roundtrip(self):
        r = FindingRecord(
            finding_id="f-001",
            quest_id="q-001",
            hypothesis="Test hypothesis",
            stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(utility=0.7, quality=0.8, efficiency=0.6),
            implementation_ref="abc123",
            experiment_logs=[{"delta": 0.5}],
            analysis="Good results",
        )
        d = r.to_dict()
        r2 = FindingRecord.from_dict(d)
        assert r2.finding_id == r.finding_id
        assert r2.quest_id == r.quest_id
        assert r2.hypothesis == r.hypothesis
        assert r2.stage == FindingStage.IMPLEMENT
        assert r2.valuation.utility == 0.7
        assert r2.implementation_ref == "abc123"
        assert r2.experiment_logs == [{"delta": 0.5}]
        assert r2.analysis == "Good results"


# =============================================================================
# Test: FindingsMemory - CRUD
# =============================================================================


class TestFindingsMemoryCRUD:
    """Test basic CRUD operations on FindingsMemory."""

    def test_empty_memory(self, empty_memory):
        assert empty_memory.total_records() == 0
        assert empty_memory.get_records_by_quest("q-none") == []

    def test_add_record_assigns_id(self, empty_memory):
        rec = FindingRecord(
            quest_id="q-001",
            hypothesis="Test",
            stage=FindingStage.IDEA,
        )
        fid = empty_memory.add_record(rec)
        assert fid != ""
        stored = empty_memory.get_record(fid)
        assert stored is not None
        assert stored.hypothesis == "Test"

    def test_add_record_generates_timestamps(self, empty_memory):
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-001",
            hypothesis="Test",
        ))
        stored = empty_memory.get_record(fid)
        assert stored is not None
        assert stored.created_at != ""
        assert stored.updated_at != ""

    def test_update_stage_advances(self, empty_memory):
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-001",
            hypothesis="Test",
            stage=FindingStage.IDEA,
        ))
        empty_memory.update_stage(fid, FindingStage.IMPLEMENT)
        stored = empty_memory.get_record(fid)
        assert stored is not None
        assert stored.stage == FindingStage.IMPLEMENT

    def test_update_stage_raises_on_invalid(self, empty_memory):
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-001",
            hypothesis="Test",
            stage=FindingStage.IDEA,
        ))
        with pytest.raises(ValueError):
            empty_memory.update_stage(fid, FindingStage.IDEA)  # Same stage

    def test_update_stage_raises_on_regression(self, empty_memory):
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-001",
            hypothesis="Test",
            stage=FindingStage.PROGRESS,
        ))
        with pytest.raises(ValueError):
            empty_memory.update_stage(fid, FindingStage.IDEA)

    def test_update_stage_raises_on_missing(self, empty_memory):
        with pytest.raises(KeyError):
            empty_memory.update_stage("does-not-exist", FindingStage.IMPLEMENT)

    def test_update_record_immutable(self, empty_memory):
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-001",
            hypothesis="Original",
        ))
        original = empty_memory.get_record(fid)
        empty_memory.update_record(fid, hypothesis="Updated")
        updated = empty_memory.get_record(fid)
        assert original is not updated  # Different objects
        assert updated.hypothesis == "Updated"

    def test_update_record_raises_on_missing(self, empty_memory):
        with pytest.raises(KeyError):
            empty_memory.update_record("does-not-exist", hypothesis="x")

    def test_get_records_by_quest(self, populated_memory):
        records = populated_memory.get_records_by_quest("q-001")
        assert len(records) == 3  # Three q-001 records
        assert all(r.quest_id == "q-001" for r in records)

    def test_get_records_by_stage(self, populated_memory):
        ideas = populated_memory.get_records_by_stage(FindingStage.IDEA)
        assert len(ideas) == 2  # q-001 + q-002 ideas
        assert all(r.stage == FindingStage.IDEA for r in ideas)

    def test_clear(self, populated_memory):
        assert populated_memory.total_records() > 0
        populated_memory.clear()
        assert populated_memory.total_records() == 0


# =============================================================================
# Test: FindingsMemory - UCB Acquisition
# =============================================================================


class TestFindingsMemoryUCB:
    """Test UCB acquisition in FindingsMemory."""

    def test_ucb_on_empty_memory(self, empty_memory):
        result = empty_memory.ucb_acquisition()
        assert result == []

    def test_ucb_returns_most_promising(self, populated_memory):
        result = populated_memory.ucb_acquisition(top_k=1)
        assert len(result) >= 1
        # The highest-valued record is q-001/KV cache (combined=0.85*0.4+0.85*0.35+0.7*0.25=0.7975)
        assert result[0].hypothesis == "KV cache quantization degrades quality above 4-bit"

    def test_ucb_top_k(self, populated_memory):
        result = populated_memory.ucb_acquisition(top_k=2)
        assert len(result) == 2

    def test_ucb_quest_filter(self, populated_memory):
        result = populated_memory.ucb_acquisition(top_k=5, quest_id="q-002")
        assert len(result) == 1
        assert result[0].quest_id == "q-002"

    def test_ucb_exploration_parameter(self, populated_memory):
        """High exploration should give different results than low exploration."""
        low_explore = populated_memory.ucb_acquisition(c=0.0, top_k=3)
        high_explore = populated_memory.ucb_acquisition(c=10.0, top_k=3)
        # With high exploration, previously-unseen hypotheses get infinite bonus
        # All records have at least n_h > 0, so scores differ
        assert len(low_explore) == 3
        assert len(high_explore) == 3


# =============================================================================
# Test: FindingsMemory - Hybrid Search
# =============================================================================


class TestFindingsMemorySearch:
    """Test hybrid keyword + embedding search via RRF."""

    def test_search_empty(self, empty_memory):
        assert empty_memory.search("test") == []

    def test_search_returns_relevant(self, populated_memory):
        results = populated_memory.search("attention sparsity")
        assert len(results) >= 1
        assert any("sparsity" in r.hypothesis.lower() for r in results)

    def test_search_respects_top_k(self, populated_memory):
        results = populated_memory.search("test", top_k=2)
        assert len(results) <= 2

    def test_search_returns_results_sorted(self, populated_memory):
        results = populated_memory.search("inference")
        if len(results) >= 2:
            # First result should be more relevant
            assert any("inference" in r.hypothesis.lower() for r in results)


# =============================================================================
# Test: FindingsMemory - Cross-Quest Knowledge Sharing
# =============================================================================


class TestFindingsMemoryCrossQuest:
    """Test cross-quest knowledge sharing."""

    def test_cross_quest_share_returns_findings(self, populated_memory):
        shared = populated_memory.cross_quest_share("q-001", "q-002", top_k=2)
        assert len(shared) >= 1
        for rec in shared:
            assert "shared_to" in rec.metadata
            assert rec.metadata["shared_to"] == "q-002"

    def test_cross_quest_empty_source(self, empty_memory):
        shared = empty_memory.cross_quest_share("q-empty", "q-002")
        assert shared == []


# =============================================================================
# Test: FindingsMemory - Persistence
# =============================================================================


class TestFindingsMemoryPersistence:
    """Test FindingsMemory serialization roundtrip."""

    def test_to_dict_from_dict_roundtrip(self, populated_memory):
        d = populated_memory.to_dict()
        fm2 = FindingsMemory.from_dict(d)
        assert fm2.total_records() == populated_memory.total_records()
        # Check a specific record
        src_first = populated_memory.get_records_by_quest("q-001")
        dst_first = fm2.get_records_by_quest("q-001")
        assert len(src_first) == len(dst_first)
        for src, dst in zip(src_first, dst_first):
            assert src.hypothesis == dst.hypothesis
            assert src.valuation.utility == dst.valuation.utility
            assert src.stage == dst.stage

    def test_from_dict_empty(self):
        fm = FindingsMemory.from_dict({"records": {}})
        assert fm.total_records() == 0


# =============================================================================
# Test: DeepResearchPipeline - Stage 1 (Strategize)
# =============================================================================


class TestDeepResearchPipelineStage1:
    """Test Stage 1 (Strategize) of the DeepResearchPipeline."""

    def test_run_stage1_generates_hypotheses(self, empty_memory, reviewer_mock):
        pipeline = DeepResearchPipeline(
            findings_memory=empty_memory,
            llm_reviewer=reviewer_mock,
        )
        quest_id = "q-test"
        result = pipeline.run_stage1(
            quest_id=quest_id,
            hypotheses=["Test hypothesis 1"],
        )
        assert len(result) == 1
        record = result[0]
        assert record.quest_id == quest_id
        assert record.stage == FindingStage.IDEA
        # Reviewer should have updated the valuation
        assert record.valuation.utility == 0.75
        assert record.valuation.quality == 0.65

    def test_run_stage1_without_hypotheses_generates_bootstrap(self, empty_memory):
        pipeline = DeepResearchPipeline(
            findings_memory=empty_memory,
        )
        result = pipeline.run_stage1(quest_id="q-bootstrap")
        assert len(result) >= 1  # Bootstrap hypothesis generated
        record = result[0]
        assert record.quest_id == "q-bootstrap"

    def test_run_stage1_without_reviewer_uses_default_scores(self, empty_memory):
        pipeline = DeepResearchPipeline(findings_memory=empty_memory)
        result = pipeline.run_stage1(
            quest_id="q-test",
            hypotheses=["Default scored hypothesis"],
        )
        assert len(result) == 1
        # Default scores = all 0.5
        assert result[0].valuation.utility == 0.5
        assert result[0].valuation.quality == 0.5
        assert result[0].valuation.efficiency == 0.5


# =============================================================================
# Test: DeepResearchPipeline - Stage 2 (Implement)
# =============================================================================


class TestDeepResearchPipelineStage2:
    """Test Stage 2 (Implement) of the DeepResearchPipeline."""

    def test_stage2_no_ideas_returns_empty(self, empty_memory):
        pipeline = DeepResearchPipeline(findings_memory=empty_memory)
        result = pipeline.run_stage2([])
        assert result == []

    def test_stage2_selects_via_ucb_and_logs(self, empty_memory):
        pipeline = DeepResearchPipeline(
            findings_memory=empty_memory,
            coding_agent=MagicMock(return_value={
                "implementation_ref": "abc123",
                "experiment_logs": [{"delta": 0.1}],
            }),
        )
        # Add a scored idea
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-test",
            hypothesis="Test hypothesis for implementation",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(utility=0.8, quality=0.7, efficiency=0.6),
        ))
        idea = empty_memory.get_record(fid)
        assert idea is not None

        result = pipeline.run_stage2([idea])
        assert len(result) >= 1
        record = result[0]
        assert record.stage == FindingStage.IMPLEMENT
        assert record.implementation_ref == "abc123"
        assert len(record.experiment_logs) == 1

    def test_stage2_coding_agent_failure_still_logged(self, empty_memory):
        pipeline = DeepResearchPipeline(
            findings_memory=empty_memory,
            coding_agent=MagicMock(side_effect=RuntimeError("Agent crashed")),
        )
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-test",
            hypothesis="Hypothesis that fails",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(utility=0.8, quality=0.7, efficiency=0.6),
        ))
        idea = empty_memory.get_record(fid)
        assert idea is not None

        result = pipeline.run_stage2([idea])
        assert len(result) >= 1
        record = result[0]
        assert record.stage == FindingStage.IMPLEMENT
        # Error should be logged in experiment_logs
        assert any("error" in str(log).lower() for log in record.experiment_logs)


# =============================================================================
# Test: DeepResearchPipeline - Stage 3 (Analyze)
# =============================================================================


class TestDeepResearchPipelineStage3:
    """Test Stage 3 (Analyze) of the DeepResearchPipeline."""

    def test_stage3_empty(self, empty_memory):
        pipeline = DeepResearchPipeline(findings_memory=empty_memory)
        result = pipeline.run_stage3([])
        assert result == []

    def test_stage3_advances_successful(self, empty_memory):
        pipeline = DeepResearchPipeline(
            findings_memory=empty_memory,
            ablation_budget=2,
        )
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-test",
            hypothesis="Successful finding",
            stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(utility=0.8, quality=0.7, efficiency=0.6),
            experiment_logs=[{"delta": 0.5}],
        ))
        impl_record = empty_memory.get_record(fid)
        assert impl_record is not None

        result = pipeline.run_stage3([impl_record])
        assert len(result) == 1
        assert result[0].stage == FindingStage.PROGRESS
        assert "paper_snippet" in result[0].metadata

    def test_stage3_skips_non_implement(self, empty_memory):
        pipeline = DeepResearchPipeline(findings_memory=empty_memory)
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-test",
            hypothesis="Idea only",
            stage=FindingStage.IDEA,
        ))
        idea = empty_memory.get_record(fid)
        assert idea is not None

        result = pipeline.run_stage3([idea])
        assert result == []

    def test_stage3_adds_ablation_logs(self, empty_memory):
        pipeline = DeepResearchPipeline(
            findings_memory=empty_memory,
            ablation_budget=3,
        )
        fid = empty_memory.add_record(FindingRecord(
            quest_id="q-test",
            hypothesis="To be ablated",
            stage=FindingStage.IMPLEMENT,
            valuation=ValuationScores(utility=0.7, quality=0.7, efficiency=0.7),
            experiment_logs=[{"delta": 0.1, "stage": "main"}],
        ))
        impl_record = empty_memory.get_record(fid)
        assert impl_record is not None

        result = pipeline.run_stage3([impl_record])
        assert len(result) == 1
        ablated = result[0]
        ablation_logs = [log for log in ablated.experiment_logs if log.get("stage") == "ablation"]
        assert len(ablation_logs) == 3

    def test_evaluate_success(self):
        record = FindingRecord(
            experiment_logs=[{"delta": 0.5}, {"delta": -0.1}, {"delta": 0.3}],
            stage=FindingStage.IMPLEMENT,
        )
        assert DeepResearchPipeline._evaluate_success(record) is True

    def test_evaluate_success_empty_logs(self):
        record = FindingRecord(stage=FindingStage.IMPLEMENT)
        assert DeepResearchPipeline._evaluate_success(record) is True


# =============================================================================
# Test: DeepResearchPipeline - Full Pipeline
# =============================================================================


class TestDeepResearchPipelineFull:
    """Test the full 3-stage pipeline execution."""

    def test_full_pipeline_with_mocks(self, empty_memory, reviewer_mock):
        coding_agent = MagicMock(return_value={
            "implementation_ref": "abc123",
            "experiment_logs": [{"delta": 0.15, "stage": "main"}],
        })
        pipeline = DeepResearchPipeline(
            findings_memory=empty_memory,
            llm_reviewer=reviewer_mock,
            coding_agent=coding_agent,
            ablation_budget=2,
        )
        result = pipeline.run(
            quest_id="q-full",
            goal="Test full pipeline",
            baseline_repo="/tmp/test",
            hypotheses=["Full pipeline hypothesis"],
        )
        assert len(result) >= 1
        assert all(r.stage == FindingStage.PROGRESS for r in result)


# =============================================================================
# Test: QuestManager
# =============================================================================


class TestQuestManager:
    """Test the QuestManager lifecycle."""

    def test_create_quest(self):
        qm = QuestManager()
        quest = qm.create_quest(
            goal="Test goal",
            baseline_repo="/tmp/repo",
        )
        assert quest.quest_id != ""
        assert quest.goal == "Test goal"
        assert quest.baseline_repo == "/tmp/repo"
        assert quest.worktree_path != ""
        assert qm.get_quest(quest.quest_id) is quest

    def test_create_quest_duplicate_raises(self):
        qm = QuestManager()
        qm.create_quest(goal="G1", baseline_repo="/tmp", quest_id="q-test")
        with pytest.raises(ValueError):
            qm.create_quest(goal="G2", baseline_repo="/tmp", quest_id="q-test")

    def test_quest_status(self):
        qm = QuestManager()
        quest = qm.create_quest(goal="Status test", baseline_repo="/tmp")
        self._add_idea(qm, quest.quest_id)
        status = qm.quest_status()
        assert quest.quest_id in status
        assert status[quest.quest_id]["total_findings"] == 1

    def test_quest_status_empty(self):
        qm = QuestManager()
        assert qm.quest_status() == {}

    def test_list_findings(self):
        qm = QuestManager()
        quest = qm.create_quest(goal="Findings test", baseline_repo="/tmp")
        self._add_idea(qm, quest.quest_id)
        self._add_idea(qm, quest.quest_id)
        findings = qm.list_findings(quest.quest_id)
        assert len(findings) == 2

    def test_list_findings_filter_by_stage(self):
        qm = QuestManager()
        quest = qm.create_quest(goal="Stage filter", baseline_repo="/tmp")
        self._add_progress(qm, quest.quest_id)
        ideas = qm.list_findings(quest.quest_id, stage=FindingStage.IDEA)
        progress = qm.list_findings(quest.quest_id, stage=FindingStage.PROGRESS)
        assert len(ideas) == 0
        assert len(progress) == 1

    def test_list_findings_unknown_quest(self):
        qm = QuestManager()
        assert qm.list_findings("q-nonexistent") == []

    def test_remove_quest(self, tmp_path):
        qm = QuestManager()
        qm.create_quest(goal="Remove me", baseline_repo=str(tmp_path))
        # Find the quest
        quest_id = list(qm._quests.keys())[0]
        assert qm.remove_quest(quest_id) is True
        assert qm.get_quest(quest_id) is None

    def test_remove_quest_unknown(self):
        qm = QuestManager()
        assert qm.remove_quest("does-not-exist") is False

    def test_list_quests(self):
        qm = QuestManager()
        qm.create_quest(goal="G1", baseline_repo="/tmp")
        qm.create_quest(goal="G2", baseline_repo="/tmp")
        quests = qm.list_quests()
        assert len(quests) == 2

    def test_list_quests_empty(self):
        qm = QuestManager()
        assert qm.list_quests() == []

    def test_to_dict_roundtrip(self):
        qm = QuestManager()
        qm.create_quest(goal="Serialization test", baseline_repo="/tmp")
        d = qm.to_dict()
        qm2 = QuestManager()
        qm2.from_dict(d)
        # Deserialized quest manager should have the same quests
        assert len(qm2._quests) == 1
        qid = list(qm._quests.keys())[0]
        assert qm2.get_quest(qid) is not None

    def test_get_quest_none(self):
        qm = QuestManager()
        assert qm.get_quest("does-not-exist") is None

    def test_cascade_integration(self):
        """Quest creation should cascade to memory if available."""
        mock_cascade = MagicMock()
        qm = QuestManager(cascade=mock_cascade)
        qm.create_quest(goal="Cascade test", baseline_repo="/tmp")
        assert mock_cascade.store.called

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _add_idea(qm: QuestManager, quest_id: str) -> str:
        return qm.findings_memory.add_record(FindingRecord(
            quest_id=quest_id,
            hypothesis=f"Idea for {quest_id}",
            stage=FindingStage.IDEA,
        ))

    @staticmethod
    def _add_progress(qm: QuestManager, quest_id: str) -> str:
        return qm.findings_memory.add_record(FindingRecord(
            quest_id=quest_id,
            hypothesis=f"Progress for {quest_id}",
            stage=FindingStage.PROGRESS,
            valuation=ValuationScores(utility=0.9, quality=0.8, efficiency=0.7),
        ))


# =============================================================================
# Test: Cross-Quest in QuestManager context
# =============================================================================


class TestCrossQuestSharing:
    """Test cross-quest knowledge sharing integrated with QuestManager."""

    def test_share_between_quests(self):
        qm = QuestManager()
        q1 = qm.create_quest(goal="Source quest", baseline_repo="/tmp", quest_id="q-src")
        q2 = qm.create_quest(goal="Target quest", baseline_repo="/tmp", quest_id="q-dst")

        # Add a progress finding to source
        qm.findings_memory.add_record(FindingRecord(
            quest_id="q-src",
            hypothesis="Important discovery from source",
            stage=FindingStage.PROGRESS,
            valuation=ValuationScores(utility=0.9, quality=0.85, efficiency=0.8),
        ))

        # Share to target
        shared = qm.findings_memory.cross_quest_share("q-src", "q-dst", top_k=1)
        assert len(shared) >= 1
        assert shared[0].metadata.get("shared_to") == "q-dst"
        assert shared[0].metadata.get("shared_from") == "q-src"
