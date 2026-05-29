"""Tests for the lyra-skill-curator package (80+ tests covering all modules)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from lyra_skill_curator.confidence_scorer import (
    ConfidenceScore,
    ConfidenceScorer,
    EvidenceItem,
    EvidenceType,
    decay_confidence,
    get_reliability_tier,
    score,
    update_score,
)
from lyra_skill_curator.exceptions import (
    CuratorError,
    EvaluationError,
    ExtractionError,
    MiningError,
    PromotionError,
    ScorerError,
    SyncError,
)
from lyra_skill_curator.instinct_extractor import (
    ExtractionConfig,
    Instinct,
    InstinctExtractor,
    InstinctType,
    extract_from_sessions,
    validate_instinct,
)
from lyra_skill_curator.marketplace_sync import (
    MarketplaceSync,
    RegistryEntry,
    SyncConfig,
    SyncResult,
    check_for_updates,
    pull_from_registry,
    push_to_registry,
    resolve_conflict,
)
from lyra_skill_curator.promotion_gate import (
    GateCheck,
    GateConfig,
    GateResult,
    PromotionGate,
    PromotionStatus,
    validate,
)
from lyra_skill_curator.quality_evaluator import (
    EvaluationConfig,
    QualityCriteria,
    QualityEvaluator,
    QualityScore,
    evaluate,
    rank_by_quality,
)
from lyra_skill_curator.rl_curator import (
    CuratorAction,
    CuratorConfig,
    CuratorState,
    RLCurator,
    SkillPatch,
    evaluate_patch,
    propose_patch,
    run_curation_cycle,
)
from lyra_skill_curator.skill_miner import (
    MiningConfig,
    SkillCandidate,
    SkillMiner,
    SkillMiningResult,
    SourceType,
    deduplicate,
    mine_from_registry,
    mine_from_repo,
    mine_from_traces,
)

# =========================================================================
# rl_curator tests
# =========================================================================


class TestRLCurator:
    def test_curator_action_enum_values(self) -> None:
        assert CuratorAction.PROPOSE.value == "propose"
        assert CuratorAction.MODIFY.value == "modify"
        assert CuratorAction.DEPRECATE.value == "deprecate"
        assert CuratorAction.PROMOTE.value == "promote"
        assert CuratorAction.MERGE.value == "merge"

    def test_skill_patch_frozen_dataclass(self) -> None:
        patch = SkillPatch(
            patch_id="p1",
            skill_name="test_skill",
            changes="refactor x",
            confidence=0.85,
            source="test",
        )
        assert patch.patch_id == "p1"
        assert patch.skill_name == "test_skill"
        assert patch.changes == "refactor x"
        assert patch.confidence == 0.85
        assert patch.source == "test"
        with pytest.raises(AttributeError):
            patch.confidence = 0.9  # type: ignore[misc]

    def test_curator_state_frozen_dataclass(self) -> None:
        state = CuratorState(
            current_skills=("a", "b"),
            performance_history=(0.9, 0.5),
            exploration_rate=0.1,
        )
        assert state.current_skills == ("a", "b")
        assert state.performance_history == (0.9, 0.5)
        assert state.exploration_rate == 0.1

    def test_curator_config_defaults(self) -> None:
        cfg = CuratorConfig()
        assert cfg.exploration_rate == 0.1
        assert cfg.learning_rate == 0.01
        assert cfg.min_confidence == 0.7
        assert cfg.max_patches_per_cycle == 10

    def test_rl_curator_default_config(self) -> None:
        curator = RLCurator()
        assert curator.config.exploration_rate == 0.1
        assert curator.config.learning_rate == 0.01

    def test_rl_curator_custom_config(self) -> None:
        cfg = CuratorConfig(exploration_rate=0.5, learning_rate=0.1)
        curator = RLCurator(config=cfg)
        assert curator.config.exploration_rate == 0.5
        assert curator.config.learning_rate == 0.1

    def test_propose_patch_with_valid_state(self) -> None:
        state = CuratorState(
            current_skills=("skill_a", "skill_b"),
            performance_history=(0.9, 0.3),
            exploration_rate=0.0,
        )
        cfg = CuratorConfig(min_confidence=0.7, exploration_rate=0.0)
        patch = propose_patch(state, cfg)
        assert isinstance(patch, SkillPatch)
        assert patch.confidence >= 0.7

    def test_propose_patch_explore_high_rate(self) -> None:
        state = CuratorState(
            current_skills=("skill_a", "skill_b"),
            performance_history=(0.9, 0.5),
            exploration_rate=1.0,
        )
        cfg = CuratorConfig(exploration_rate=1.0, min_confidence=0.3)
        patch = propose_patch(state, cfg)
        assert isinstance(patch, SkillPatch)

    def test_propose_patch_raises_on_empty_skills(self) -> None:
        state = CuratorState(
            current_skills=(),
            performance_history=(),
            exploration_rate=0.1,
        )
        with pytest.raises(ValueError, match="no skills in state"):
            propose_patch(state)

    def test_propose_patch_raises_on_empty_history(self) -> None:
        state = CuratorState(
            current_skills=("skill_a",),
            performance_history=(),
            exploration_rate=0.1,
        )
        with pytest.raises(
            ValueError, match="no performance history available"
        ):
            propose_patch(state)

    def test_propose_patch_uses_default_config(self) -> None:
        state = CuratorState(
            current_skills=("skill_a",),
            performance_history=(0.8,),
            exploration_rate=0.0,
        )
        patch = propose_patch(state)
        assert isinstance(patch, SkillPatch)

    def test_evaluate_patch_with_tasks(self) -> None:
        patch = SkillPatch(
            patch_id="p1",
            skill_name="test",
            changes="fix",
            confidence=0.9,
            source="test",
        )
        reward = evaluate_patch(patch, ("task1", "task2", "task3"))
        assert 0.0 <= reward <= 1.0

    def test_evaluate_patch_high_confidence(self) -> None:
        patch = SkillPatch(
            patch_id="p1",
            skill_name="test",
            changes="fix",
            confidence=1.0,
            source="test",
        )
        reward = evaluate_patch(patch, ("task1", "task2", "task3", "task4", "task5"))
        assert 0.0 <= reward <= 1.0

    def test_evaluate_patch_empty_tasks(self) -> None:
        patch = SkillPatch(
            patch_id="p1",
            skill_name="test",
            changes="fix",
            confidence=0.9,
            source="test",
        )
        reward = evaluate_patch(patch, ())
        assert reward == 0.0

    def test_evaluate_patch_confidence_capped(self) -> None:
        patch = SkillPatch(
            patch_id="p1",
            skill_name="test",
            changes="fix",
            confidence=0.5,
            source="test",
        )
        reward = evaluate_patch(patch, ("task1",))
        assert reward <= 1.0

    def test_run_curation_cycle_default(self) -> None:
        patches = run_curation_cycle()
        assert isinstance(patches, list)
        assert len(patches) > 0
        for p in patches:
            assert isinstance(p, SkillPatch)

    def test_run_curation_cycle_respects_max_patches(self) -> None:
        cfg = CuratorConfig(max_patches_per_cycle=3, exploration_rate=0.0)
        patches = run_curation_cycle(cfg)
        assert len(patches) <= 3

    def test_run_curation_cycle_empty_state(self) -> None:
        cfg = CuratorConfig(max_patches_per_cycle=5, exploration_rate=0.0)
        patches = run_curation_cycle(cfg)
        assert len(patches) > 0

    def test_rl_curator_propose_patch_method(self) -> None:
        curator = RLCurator()
        state = CuratorState(
            current_skills=("skill_x",),
            performance_history=(0.5,),
            exploration_rate=0.0,
        )
        patch = curator.propose_patch(state)
        assert isinstance(patch, SkillPatch)

    def test_rl_curator_evaluate_patch_method(self) -> None:
        curator = RLCurator()
        patch = SkillPatch(
            patch_id="p1",
            skill_name="test",
            changes="fix",
            confidence=0.8,
            source="test",
        )
        reward = curator.evaluate_patch(patch, ("task1",))
        assert 0.0 <= reward <= 1.0

    def test_rl_curator_run_curation_cycle_method(self) -> None:
        curator = RLCurator()
        patches = curator.run_curation_cycle()
        assert isinstance(patches, list)

    def test_generate_patch_id_format(self) -> None:
        from lyra_skill_curator.rl_curator import _generate_patch_id

        pid = _generate_patch_id("test_skill", CuratorAction.MERGE)
        assert pid.startswith("test_skill_merge_")
        suffix = pid.split("_")[-1]
        assert suffix.isdigit()

    def test_curator_config_custom_values(self) -> None:
        cfg = CuratorConfig(
            exploration_rate=0.9,
            learning_rate=0.5,
            min_confidence=0.2,
            max_patches_per_cycle=1,
        )
        assert cfg.exploration_rate == 0.9
        assert cfg.learning_rate == 0.5
        assert cfg.min_confidence == 0.2
        assert cfg.max_patches_per_cycle == 1

    def test_propose_patch_exploit_selects_lowest_performer(self) -> None:
        state = CuratorState(
            current_skills=("skill_a", "skill_b", "skill_c"),
            performance_history=(0.9, 0.3, 0.6),
            exploration_rate=0.0,
        )
        patch = propose_patch(state)
        assert "0.300" in patch.changes or "0.3" in patch.changes
        assert "skill_b" in patch.changes


# =========================================================================
# skill_miner tests
# =========================================================================


class TestSkillMiner:
    def test_source_type_enum(self) -> None:
        assert SourceType.GITHUB_REPO.value == "github_repo"
        assert SourceType.SESSION_TRACE.value == "session_trace"
        assert SourceType.COMMUNITY_REGISTRY.value == "community_registry"
        assert SourceType.PAPER.value == "paper"
        assert SourceType.DOCS.value == "docs"

    def test_skill_candidate_frozen(self) -> None:
        cand = SkillCandidate(
            name="test_skill",
            description="A test skill.",
            trigger_patterns=("pat1",),
            body="body content",
            source_url="https://example.com",
            source_type=SourceType.GITHUB_REPO,
        )
        assert cand.name == "test_skill"
        assert cand.description == "A test skill."
        assert cand.trigger_patterns == ("pat1",)
        assert cand.body == "body content"
        assert cand.source_url == "https://example.com"
        assert cand.source_type == SourceType.GITHUB_REPO

    def test_mining_config_defaults(self) -> None:
        cfg = MiningConfig()
        assert cfg.max_skills == 50
        assert cfg.min_stars == 10
        assert cfg.min_quality_score == 0.5

    def test_skill_miner_default_config(self) -> None:
        miner = SkillMiner()
        assert miner.config.max_skills == 50

    def test_skill_miner_custom_config(self) -> None:
        cfg = MiningConfig(max_skills=10)
        miner = SkillMiner(config=cfg)
        assert miner.config.max_skills == 10

    def test_mine_from_repo_valid_url(self) -> None:
        candidates = mine_from_repo("https://github.com/test/repo")
        assert len(candidates) > 0
        for c in candidates:
            assert c.source_type == SourceType.GITHUB_REPO
            assert c.source_url == "https://github.com/test/repo"

    def test_mine_from_repo_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Repository URL cannot be empty"):
            mine_from_repo("")

    def test_mine_from_repo_blank_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Repository URL cannot be empty"):
            mine_from_repo("   ")

    def test_mine_from_repo_respects_max_results(self) -> None:
        candidates = mine_from_repo(
            "https://github.com/test/repo", max_results=1
        )
        assert len(candidates) <= 1

    def test_mine_from_traces_valid(self) -> None:
        candidates = mine_from_traces(("session_1", "session_2"))
        assert len(candidates) == 2
        for c in candidates:
            assert c.source_type == SourceType.SESSION_TRACE

    def test_mine_from_traces_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Session list cannot be empty"):
            mine_from_traces(())

    def test_mine_from_registry_valid(self) -> None:
        candidates = mine_from_registry("https://registry.example.com")
        assert len(candidates) > 0
        for c in candidates:
            assert c.source_type == SourceType.COMMUNITY_REGISTRY

    def test_mine_from_registry_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Registry URL cannot be empty"):
            mine_from_registry("")

    def test_deduplicate_removes_duplicates(self) -> None:
        candidates = [
            SkillCandidate(
                name="dup_skill",
                description="short",
                trigger_patterns=("a",),
                body="body",
                source_url="url1",
                source_type=SourceType.GITHUB_REPO,
            ),
            SkillCandidate(
                name="dup_skill",
                description="longer description",
                trigger_patterns=("b",),
                body="body2",
                source_url="url2",
                source_type=SourceType.GITHUB_REPO,
            ),
        ]
        result = deduplicate(candidates)
        assert len(result) == 1
        assert result[0].description == "longer description"

    def test_deduplicate_no_duplicates(self) -> None:
        candidates = [
            SkillCandidate(
                name="skill_a",
                description="A",
                trigger_patterns=("a",),
                body="body_a",
                source_url="url_a",
                source_type=SourceType.GITHUB_REPO,
            ),
            SkillCandidate(
                name="skill_b",
                description="B",
                trigger_patterns=("b",),
                body="body_b",
                source_url="url_b",
                source_type=SourceType.GITHUB_REPO,
            ),
        ]
        result = deduplicate(candidates)
        assert len(result) == 2

    def test_deduplicate_empty_list(self) -> None:
        result = deduplicate([])
        assert result == []

    def test_skill_miner_mine_from_repo_method(self) -> None:
        miner = SkillMiner()
        candidates = miner.mine_from_repo("https://github.com/test/repo")
        assert len(candidates) > 0

    def test_skill_miner_mine_from_traces_method(self) -> None:
        miner = SkillMiner()
        candidates = miner.mine_from_traces(("s1", "s2"))
        assert len(candidates) == 2

    def test_skill_miner_mine_from_registry_method(self) -> None:
        miner = SkillMiner()
        candidates = miner.mine_from_registry(
            "https://registry.example.com"
        )
        assert len(candidates) > 0

    def test_skill_miner_deduplicate_method(self) -> None:
        miner = SkillMiner()
        candidates = [
            SkillCandidate(
                name="skill_x",
                description="test",
                trigger_patterns=("a",),
                body="body",
                source_url="url",
                source_type=SourceType.GITHUB_REPO,
            ),
        ]
        result = miner.deduplicate(candidates)
        assert len(result) == 1

    def test_skill_mining_result_dataclass(self) -> None:
        candidates = (
            SkillCandidate(
                name="test",
                description="test",
                trigger_patterns=(),
                body="body",
                source_url="url",
                source_type=SourceType.PAPER,
            ),
        )
        result = SkillMiningResult(
            candidates=candidates,
            total_candidates=1,
            total_sources_scanned=5,
            duplicates_removed=2,
        )
        assert result.total_candidates == 1
        assert result.total_sources_scanned == 5
        assert result.duplicates_removed == 2


# =========================================================================
# quality_evaluator tests
# =========================================================================


class TestQualityEvaluator:
    def test_quality_criteria_enum(self) -> None:
        assert QualityCriteria.CLARITY.value == "clarity"
        assert QualityCriteria.COMPLETENESS.value == "completeness"
        assert QualityCriteria.CORRECTNESS.value == "correctness"
        assert QualityCriteria.USEFULNESS.value == "usefulness"
        assert QualityCriteria.TESTABILITY.value == "testability"

    def test_quality_score_dataclass(self) -> None:
        qs = QualityScore(
            overall=0.8,
            clarity=0.7,
            completeness=0.6,
            correctness=0.9,
            usefulness=0.8,
            testability=0.5,
        )
        assert qs.overall == 0.8
        assert qs.clarity == 0.7
        assert qs.completeness == 0.6
        assert qs.correctness == 0.9
        assert qs.usefulness == 0.8
        assert qs.testability == 0.5

    def test_evaluation_config_defaults(self) -> None:
        cfg = EvaluationConfig()
        assert cfg.min_clarity == 0.5
        assert cfg.min_correctness == 0.5
        assert cfg.pass_threshold == 0.6

    def test_evaluate_well_formed_skill(self) -> None:
        class MockSkill:
            name = "ExcellentSkill"
            description = "This skill extracts, generates, and analyzes data."
            trigger_patterns = ("pattern1", "pattern2")
            body = "def execute(): return 42\nclass Handler: pass"

        score = evaluate(MockSkill())
        assert 0.0 <= score.overall <= 1.0
        assert score.clarity > 0.5
        assert score.completeness > 0.3

    def test_evaluate_minimal_skill(self) -> None:
        class MinimalSkill:
            name = "X"
            description = ""
            trigger_patterns = ()
            body = ""

        score = evaluate(MinimalSkill())
        assert 0.0 <= score.overall <= 1.0
        assert score.clarity >= 0.5
        assert score.usefulness >= 0.4

    def test_evaluate_skill_with_action_keywords(self) -> None:
        class ActionSkill:
            name = "GoodSkill"
            description = "This function will validate and convert data."
            trigger_patterns = ("p1",)
            body = "def validate(): pass"

        score = evaluate(ActionSkill())
        assert score.usefulness > 0.5

    def test_evaluate_skill_missing_attributes(self) -> None:
        class PartialSkill:
            pass

        score = evaluate(PartialSkill())
        assert 0.0 <= score.overall <= 1.0

    def test_evaluate_skill_none_attributes(self) -> None:
        class NoneSkill:
            name = None  # type: ignore[assignment]
            description = None  # type: ignore[assignment]
            trigger_patterns = None  # type: ignore[assignment]
            body = None  # type: ignore[assignment]

        score = evaluate(NoneSkill())
        assert 0.0 <= score.overall <= 1.0

    def test_batch_evaluate_empty(self) -> None:
        scores = QualityEvaluator().batch_evaluate([])
        assert scores == []

    def test_batch_evaluate_multiple(self) -> None:
        class SK:
            name = "S"
            description = "desc"
            trigger_patterns = ("p",)
            body = "body"

        scores = QualityEvaluator().batch_evaluate([SK(), SK()])
        assert len(scores) == 2
        assert all(isinstance(s, QualityScore) for s in scores)

    def test_rank_by_quality_empty(self) -> None:
        ranked = rank_by_quality([])
        assert ranked == []

    def test_rank_by_quality_orders_descending(self) -> None:
        class LowSkill:
            name = "L"
            description = ""
            trigger_patterns = ()
            body = ""

        class HighSkill:
            name = "HighQualitySkill"
            description = "This skill extracts information from documents."
            trigger_patterns = ("p1", "p2", "p3")
            body = "def execute(): return True\ndef validate(): pass"

        ranked = rank_by_quality([LowSkill(), HighSkill()])
        assert len(ranked) == 2
        assert ranked[0][1].overall >= ranked[1][1].overall

    def test_quality_evaluator_evaluate_method(self) -> None:
        evaluator = QualityEvaluator()

        class SK:
            name = "TestSkill"
            description = "A test skill description."
            trigger_patterns = ("p1",)
            body = "def run(): pass"

        score = evaluator.evaluate(SK())
        assert isinstance(score, QualityScore)

    def test_quality_evaluator_rank_by_quality_method(self) -> None:
        evaluator = QualityEvaluator()

        class SK:
            name = "TestSkill"
            description = "A test skill."
            trigger_patterns = ("pat",)
            body = "def fn(): pass"

        ranked = evaluator.rank_by_quality([SK(), SK()])
        assert len(ranked) == 2


# =========================================================================
# promotion_gate tests
# =========================================================================


class TestPromotionGate:
    def test_promotion_status_enum(self) -> None:
        assert PromotionStatus.PENDING_REVIEW.value == "pending_review"
        assert PromotionStatus.APPROVED.value == "approved"
        assert PromotionStatus.REJECTED.value == "rejected"
        assert PromotionStatus.NEEDS_REVISION.value == "needs_revision"

    def test_gate_check_frozen(self) -> None:
        check = GateCheck(
            check_name="test_check",
            passed=True,
            score=0.9,
            reviewer_agent="agent_1",
            notes="All good.",
        )
        assert check.passed is True
        assert check.score == 0.9

    def test_gate_result_frozen(self) -> None:
        checks = (
            GateCheck(
                check_name="c1",
                passed=True,
                score=0.8,
                reviewer_agent="a1",
                notes="ok",
            ),
        )
        result = GateResult(
            skill="test_skill",
            checks=checks,
            overall_pass=True,
            required_approvals=1,
        )
        assert result.overall_pass is True
        assert result.required_approvals == 1

    def test_gate_config_defaults(self) -> None:
        cfg = GateConfig()
        assert cfg.required_approvals == 2
        assert cfg.reviewer_count == 3
        assert cfg.min_consensus == 0.6

    def test_validate_passes_with_required_approvals(self) -> None:
        class MockSkill:
            name = "test_skill"

        result = validate(
            MockSkill(), ("reviewer1", "reviewer2", "reviewer3")
        )
        assert isinstance(result, GateResult)
        assert len(result.checks) > 0

    def test_validate_raises_on_empty_reviewers(self) -> None:
        class MockSkill:
            name = "test_skill"

        with pytest.raises(
            ValueError, match="At least one reviewer is required"
        ):
            validate(MockSkill(), ())

    def test_validate_respects_reviewer_count(self) -> None:
        class MockSkill:
            name = "test_skill"

        cfg = GateConfig(reviewer_count=1, required_approvals=0)
        result = validate(MockSkill(), ("r1", "r2", "r3"), cfg)
        assert len(result.checks) == 1

    def test_promotion_gate_default_config(self) -> None:
        gate = PromotionGate()
        assert gate.config.required_approvals == 2

    def test_promotion_gate_custom_config(self) -> None:
        cfg = GateConfig(required_approvals=3, reviewer_count=5)
        gate = PromotionGate(config=cfg)
        assert gate.config.required_approvals == 3
        assert gate.config.reviewer_count == 5

    def test_promotion_gate_validate_method(self) -> None:
        gate = PromotionGate()

        class MockSkill:
            name = "test"

        result = gate.validate(MockSkill(), ("r1", "r2", "r3"))
        assert isinstance(result, GateResult)

    def test_gate_check_immutable(self) -> None:
        check = GateCheck(
            check_name="c",
            passed=True,
            score=1.0,
            reviewer_agent="a",
            notes="n",
        )
        with pytest.raises(AttributeError):
            check.passed = False  # type: ignore[misc]

    def test_gate_result_checks_are_tuple(self) -> None:
        class MockSkill:
            name = "test"

        result = validate(
            MockSkill(), ("r1", "r2", "r3"), GateConfig(required_approvals=0)
        )
        assert isinstance(result.checks, tuple)


# =========================================================================
# instinct_extractor tests
# =========================================================================


class TestInstinctExtractor:
    def test_instinct_type_enum(self) -> None:
        assert InstinctType.TOOL_USAGE.value == "tool_usage"
        assert InstinctType.WORKFLOW.value == "workflow"
        assert InstinctType.ERROR_RECOVERY.value == "error_recovery"
        assert InstinctType.OPTIMIZATION.value == "optimization"

    def test_instinct_frozen_dataclass(self) -> None:
        instinct = Instinct(
            pattern_name="test_pattern",
            trigger_condition="on event X",
            action_template="do Y",
            confidence=0.85,
            occurrence_count=5,
        )
        assert instinct.pattern_name == "test_pattern"
        assert instinct.confidence == 0.85
        assert instinct.occurrence_count == 5

    def test_extraction_config_defaults(self) -> None:
        cfg = ExtractionConfig()
        assert cfg.min_occurrences == 3
        assert cfg.min_confidence == 0.5
        assert cfg.max_instincts == 20

    def test_extract_from_sessions_valid(self) -> None:
        instincts = extract_from_sessions(
            ("session_1", "session_2", "session_3", "session_4")
        )
        assert len(instincts) > 0
        for inst in instincts:
            assert isinstance(inst, Instinct)
            assert inst.occurrence_count >= 3

    def test_extract_from_sessions_empty_raises(self) -> None:
        with pytest.raises(
            ValueError, match="Session list cannot be empty for extraction"
        ):
            extract_from_sessions(())

    def test_extract_from_sessions_respects_max_instincts(self) -> None:
        cfg = ExtractionConfig(max_instincts=2)
        instincts = extract_from_sessions(
            ("s1", "s2", "s3", "s4", "s5"), cfg
        )
        assert len(instincts) <= 2

    def test_validate_instinct_with_test_sessions(self) -> None:
        instinct = Instinct(
            pattern_name="test",
            trigger_condition="on X",
            action_template="do Y",
            confidence=0.8,
            occurrence_count=5,
        )
        result = validate_instinct(instinct, ("test_s1", "test_s2"))
        assert isinstance(result, bool)

    def test_validate_instinct_low_confidence(self) -> None:
        instinct = Instinct(
            pattern_name="test",
            trigger_condition="on X",
            action_template="do Y",
            confidence=0.2,
            occurrence_count=5,
        )
        assert validate_instinct(instinct, ("s1",)) is False

    def test_validate_instinct_few_occurrences(self) -> None:
        instinct = Instinct(
            pattern_name="test",
            trigger_condition="on X",
            action_template="do Y",
            confidence=0.8,
            occurrence_count=1,
        )
        assert validate_instinct(instinct, ("s1",)) is False

    def test_validate_instinct_empty_sessions(self) -> None:
        instinct = Instinct(
            pattern_name="test",
            trigger_condition="on X",
            action_template="do Y",
            confidence=0.8,
            occurrence_count=5,
        )
        assert validate_instinct(instinct, ()) is False

    def test_instinct_extractor_default_config(self) -> None:
        extractor = InstinctExtractor()
        assert extractor.config.max_instincts == 20

    def test_instinct_extractor_extract_method(self) -> None:
        extractor = InstinctExtractor()
        instincts = extractor.extract_from_sessions(
            ("s1", "s2", "s3", "s4")
        )
        assert len(instincts) > 0

    def test_instinct_extractor_validate_method(self) -> None:
        extractor = InstinctExtractor()
        instinct = Instinct(
            pattern_name="test",
            trigger_condition="on X",
            action_template="do Y",
            confidence=0.9,
            occurrence_count=10,
        )
        result = extractor.validate_instinct(instinct, ("ts1", "ts2"))
        assert isinstance(result, bool)

    def test_extract_varied_instinct_types(self) -> None:
        sessions = tuple(f"session_{i}" for i in range(20))
        instincts = extract_from_sessions(sessions)
        {i.pattern_name.split("_")[0] for i in instincts}
        assert len(instincts) > 1


# =========================================================================
# confidence_scorer tests
# =========================================================================


class TestConfidenceScorer:
    def test_evidence_type_enum(self) -> None:
        assert EvidenceType.SUCCESSFUL_USE.value == "successful_use"
        assert EvidenceType.FAILED_USE.value == "failed_use"
        assert EvidenceType.EXPERT_REVIEW.value == "expert_review"
        assert EvidenceType.CROSS_VALIDATION.value == "cross_validation"
        assert EvidenceType.BENCHMARK.value == "benchmark"

    def test_evidence_item_frozen(self) -> None:
        item = EvidenceItem(
            type=EvidenceType.SUCCESSFUL_USE,
            strength=0.9,
            source="test_log",
        )
        assert item.type == EvidenceType.SUCCESSFUL_USE
        assert item.strength == 0.9
        assert item.source == "test_log"

    def test_confidence_score_frozen(self) -> None:
        cs = ConfidenceScore(
            skill_id="test_skill",
            score=0.85,
            evidence_items=(),
            uncertainty=0.2,
        )
        assert cs.skill_id == "test_skill"
        assert cs.score == 0.85
        assert cs.uncertainty == 0.2

    def test_score_with_positive_evidence(self) -> None:
        evidence = [
            EvidenceItem(
                type=EvidenceType.SUCCESSFUL_USE,
                strength=0.8,
                source="test",
            ),
            EvidenceItem(
                type=EvidenceType.EXPERT_REVIEW,
                strength=0.9,
                source="review",
            ),
        ]
        result = score("skill_1", evidence)
        assert result.skill_id == "skill_1"
        assert result.score > 0.5
        assert result.uncertainty >= 0.0

    def test_score_with_negative_evidence(self) -> None:
        evidence = [
            EvidenceItem(
                type=EvidenceType.FAILED_USE,
                strength=1.0,
                source="test",
            ),
        ]
        result = score("skill_2", evidence)
        assert result.score < 0.5

    def test_score_empty_evidence_returns_default(self) -> None:
        result = score("skill_3", [])
        assert result.score == 0.5
        assert result.uncertainty == 1.0

    def test_score_empty_skill_id_raises(self) -> None:
        with pytest.raises(ValueError, match="skill_id cannot be empty"):
            score("", [EvidenceItem(
                type=EvidenceType.BENCHMARK,
                strength=0.5,
                source="test",
            )])

    def test_score_clamps_to_range(self) -> None:
        evidence = [
            EvidenceItem(
                type=EvidenceType.FAILED_USE,
                strength=10.0,
                source="test",
            ),
        ]
        result = score("skill_4", evidence)
        assert 0.0 <= result.score <= 1.0

    def test_update_score_combines_evidence(self) -> None:
        existing = ConfidenceScore(
            skill_id="skill_u",
            score=0.6,
            evidence_items=(
                EvidenceItem(
                    type=EvidenceType.SUCCESSFUL_USE,
                    strength=0.5,
                    source="log",
                ),
            ),
            uncertainty=0.3,
        )
        new_evidence = [
            EvidenceItem(
                type=EvidenceType.EXPERT_REVIEW,
                strength=0.9,
                source="reviewer",
            ),
        ]
        updated = update_score(existing, new_evidence)
        assert len(updated.evidence_items) == 2
        assert updated.score > 0.0

    def test_update_score_without_new_evidence(self) -> None:
        existing = ConfidenceScore(
            skill_id="skill_u",
            score=0.8,
            evidence_items=(),
            uncertainty=0.2,
        )
        updated = update_score(existing, [])
        assert len(updated.evidence_items) == 0

    def test_decay_confidence_reduces_score_above_mid(self) -> None:
        cs = ConfidenceScore(
            skill_id="skill_d",
            score=0.9,
            evidence_items=(),
            uncertainty=0.1,
        )
        decayed = decay_confidence(cs, time_elapsed=10.0)
        assert decayed.score < cs.score
        assert decayed.uncertainty > cs.uncertainty

    def test_decay_confidence_zero_time(self) -> None:
        cs = ConfidenceScore(
            skill_id="skill_d",
            score=0.8,
            evidence_items=(),
            uncertainty=0.2,
        )
        decayed = decay_confidence(cs, time_elapsed=0)
        assert decayed.score == cs.score
        assert decayed.uncertainty == cs.uncertainty

    def test_decay_confidence_below_mid_approaches_half(self) -> None:
        cs = ConfidenceScore(
            skill_id="skill_d",
            score=0.3,
            evidence_items=(),
            uncertainty=0.1,
        )
        decayed = decay_confidence(cs, time_elapsed=100.0)
        assert decayed.score >= 0.3
        assert decayed.uncertainty > cs.uncertainty

    def test_decay_confidence_negative_time_no_change(self) -> None:
        cs = ConfidenceScore(
            skill_id="skill_d",
            score=0.8,
            evidence_items=(),
            uncertainty=0.2,
        )
        decayed = decay_confidence(cs, time_elapsed=-5.0)
        assert decayed == cs

    def test_get_reliability_tier_high(self) -> None:
        cs = ConfidenceScore(
            skill_id="s",
            score=0.9,
            evidence_items=(),
            uncertainty=0.2,
        )
        assert get_reliability_tier(cs) == "HIGH"

    def test_get_reliability_tier_high_with_high_uncertainty(self) -> None:
        cs = ConfidenceScore(
            skill_id="s",
            score=0.9,
            evidence_items=(),
            uncertainty=0.5,
        )
        assert get_reliability_tier(cs) == "MEDIUM"

    def test_get_reliability_tier_medium(self) -> None:
        cs = ConfidenceScore(
            skill_id="s",
            score=0.7,
            evidence_items=(),
            uncertainty=0.3,
        )
        assert get_reliability_tier(cs) == "MEDIUM"

    def test_get_reliability_tier_low(self) -> None:
        cs = ConfidenceScore(
            skill_id="s",
            score=0.4,
            evidence_items=(),
            uncertainty=0.3,
        )
        assert get_reliability_tier(cs) == "LOW"

    def test_get_reliability_tier_untrusted(self) -> None:
        cs = ConfidenceScore(
            skill_id="s",
            score=0.2,
            evidence_items=(),
            uncertainty=0.3,
        )
        assert get_reliability_tier(cs) == "UNTRUSTED"

    def test_confidence_scorer_score_method(self) -> None:
        scorer = ConfidenceScorer()
        evidence = [
            EvidenceItem(
                type=EvidenceType.BENCHMARK,
                strength=0.7,
                source="bench",
            ),
        ]
        result = scorer.score("skill_s", evidence)
        assert isinstance(result, ConfidenceScore)

    def test_confidence_scorer_update_method(self) -> None:
        scorer = ConfidenceScorer()
        cs = ConfidenceScore(
            skill_id="s",
            score=0.5,
            evidence_items=(),
            uncertainty=0.5,
        )
        new_evidence = [
            EvidenceItem(
                type=EvidenceType.CROSS_VALIDATION,
                strength=0.8,
                source="cv",
            ),
        ]
        updated = scorer.update_score(cs, new_evidence)
        assert isinstance(updated, ConfidenceScore)

    def test_confidence_scorer_decay_method(self) -> None:
        scorer = ConfidenceScorer()
        cs = ConfidenceScore(
            skill_id="s",
            score=0.8,
            evidence_items=(),
            uncertainty=0.2,
        )
        decayed = scorer.decay_confidence(cs, 5.0)
        assert isinstance(decayed, ConfidenceScore)

    def test_confidence_scorer_tier_method(self) -> None:
        scorer = ConfidenceScorer()
        cs = ConfidenceScore(
            skill_id="s",
            score=0.9,
            evidence_items=(),
            uncertainty=0.1,
        )
        assert scorer.get_reliability_tier(cs) == "HIGH"


# =========================================================================
# marketplace_sync tests
# =========================================================================


class TestMarketplaceSync:
    def test_registry_entry_frozen(self) -> None:
        entry = RegistryEntry(
            skill_id="test_skill",
            version="1.0.0",
            publisher="test_user",
            signature="abc123",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert entry.skill_id == "test_skill"
        assert entry.version == "1.0.0"
        assert entry.publisher == "test_user"
        assert entry.signature == "abc123"
        assert entry.timestamp == "2025-01-01T00:00:00Z"

    def test_sync_config_defaults(self) -> None:
        cfg = SyncConfig()
        assert cfg.registries == ()
        assert cfg.sync_interval == 3600
        assert cfg.auto_publish is False

    def test_sync_result_dataclass(self) -> None:
        result = SyncResult(
            pulled=(),
            pushed=(),
            conflicts=("c1",),
            errors=(),
        )
        assert result.conflicts == ("c1",)
        assert result.pulled == ()
        assert result.pushed == ()
        assert result.errors == ()

    def test_pull_from_registry_valid(self) -> None:
        entries = pull_from_registry("https://registry.example.com")
        assert len(entries) > 0
        for e in entries:
            assert isinstance(e, RegistryEntry)

    def test_pull_from_registry_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Registry URL cannot be empty"):
            pull_from_registry("")

    def test_pull_from_registry_blank_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Registry URL cannot be empty"):
            pull_from_registry("   ")

    def test_push_to_registry_valid(self) -> None:
        skill = MagicMock()
        skill.name = "test_skill"
        result = push_to_registry(skill, "https://registry.example.com")
        assert result is True

    def test_push_to_registry_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Registry URL cannot be empty"):
            push_to_registry(MagicMock(), "")

    def test_check_for_updates_no_local(self) -> None:
        updates = check_for_updates([])
        assert updates == []

    def test_check_for_updates_with_local(self) -> None:
        local = [
            RegistryEntry(
                skill_id="local_skill",
                version="1.0.0",
                publisher="me",
                signature="sig",
                timestamp="2025-01-01T00:00:00Z",
            ),
        ]
        updates = check_for_updates(local)
        assert len(updates) == 1
        assert updates[0].skill_id == "local_skill"
        assert updates[0].version > "1.0.0"

    def test_resolve_conflict_local_wins(self) -> None:
        local = RegistryEntry(
            skill_id="s",
            version="1.0.0",
            publisher="local",
            signature="sig_l",
            timestamp="2025-06-01T00:00:00Z",
        )
        remote = RegistryEntry(
            skill_id="s",
            version="2.0.0",
            publisher="remote",
            signature="sig_r",
            timestamp="2025-01-01T00:00:00Z",
        )
        resolved = resolve_conflict(local, remote)
        assert resolved == local

    def test_resolve_conflict_remote_wins(self) -> None:
        local = RegistryEntry(
            skill_id="s",
            version="1.0.0",
            publisher="local",
            signature="sig_l",
            timestamp="2025-01-01T00:00:00Z",
        )
        remote = RegistryEntry(
            skill_id="s",
            version="2.0.0",
            publisher="remote",
            signature="sig_r",
            timestamp="2025-06-01T00:00:00Z",
        )
        resolved = resolve_conflict(local, remote)
        assert resolved == remote

    def test_resolve_conflict_equal_timestamp_local_wins(self) -> None:
        local = RegistryEntry(
            skill_id="s",
            version="1.0.0",
            publisher="local",
            signature="sig_l",
            timestamp="2025-01-01T00:00:00Z",
        )
        remote = RegistryEntry(
            skill_id="s",
            version="2.0.0",
            publisher="remote",
            signature="sig_r",
            timestamp="2025-01-01T00:00:00Z",
        )
        resolved = resolve_conflict(local, remote)
        assert resolved == local

    def test_marketplace_sync_default_config(self) -> None:
        sync = MarketplaceSync()
        assert sync.config.sync_interval == 3600

    def test_marketplace_sync_custom_config(self) -> None:
        cfg = SyncConfig(registries=("r1",), auto_publish=True)
        sync = MarketplaceSync(config=cfg)
        assert sync.config.registries == ("r1",)
        assert sync.config.auto_publish is True

    def test_marketplace_sync_pull_method(self) -> None:
        sync = MarketplaceSync()
        entries = sync.pull_from_registry("https://registry.example.com")
        assert len(entries) > 0

    def test_marketplace_sync_push_method(self) -> None:
        sync = MarketplaceSync()
        skill = MagicMock()
        skill.name = "test"
        result = sync.push_to_registry(skill, "https://registry.example.com")
        assert result is True

    def test_marketplace_sync_check_updates_method(self) -> None:
        sync = MarketplaceSync()
        local = [
            RegistryEntry(
                skill_id="s1",
                version="1.0.0",
                publisher="me",
                signature="sig",
                timestamp="2025-01-01T00:00:00Z",
            ),
        ]
        updates = sync.check_for_updates(local)
        assert len(updates) == 1

    def test_marketplace_sync_resolve_conflict_method(self) -> None:
        sync = MarketplaceSync()
        local = RegistryEntry(
            skill_id="s",
            version="1.0.0",
            publisher="local",
            signature="sig",
            timestamp="2025-01-01T00:00:00Z",
        )
        remote = RegistryEntry(
            skill_id="s",
            version="2.0.0",
            publisher="remote",
            signature="sig",
            timestamp="2025-06-01T00:00:00Z",
        )
        resolved = sync.resolve_conflict(local, remote)
        assert resolved == remote


# =========================================================================
# exceptions tests
# =========================================================================


class TestExceptions:
    def test_curator_error_is_base(self) -> None:
        assert issubclass(MiningError, CuratorError)
        assert issubclass(EvaluationError, CuratorError)
        assert issubclass(PromotionError, CuratorError)
        assert issubclass(ExtractionError, CuratorError)
        assert issubclass(ScorerError, CuratorError)
        assert issubclass(SyncError, CuratorError)

    def test_curator_error_instantiation(self) -> None:
        err = CuratorError("something went wrong")
        assert str(err) == "something went wrong"

    def test_mining_error_instantiation(self) -> None:
        err = MiningError("mining failed")
        assert str(err) == "mining failed"

    def test_evaluation_error_instantiation(self) -> None:
        err = EvaluationError("eval failed")
        assert str(err) == "eval failed"

    def test_promotion_error_instantiation(self) -> None:
        err = PromotionError("promo failed")
        assert str(err) == "promo failed"

    def test_extraction_error_instantiation(self) -> None:
        err = ExtractionError("extraction failed")
        assert str(err) == "extraction failed"

    def test_scorer_error_instantiation(self) -> None:
        err = ScorerError("scoring failed")
        assert str(err) == "scoring failed"

    def test_sync_error_instantiation(self) -> None:
        err = SyncError("sync failed")
        assert str(err) == "sync failed"

    def test_curator_error_catch_all(self) -> None:
        errors: list[CuratorError] = [
            MiningError("m"),
            EvaluationError("e"),
            PromotionError("p"),
            ExtractionError("x"),
            ScorerError("s"),
            SyncError("y"),
        ]
        for err in errors:
            assert isinstance(err, CuratorError)


# =========================================================================
# __init__ tests
# =========================================================================


class TestInit:
    def test_version_exported(self) -> None:
        from lyra_skill_curator import __version__

        assert __version__ == "0.1.0"

    def test_all_modules_exported(self) -> None:
        from lyra_skill_curator import __all__

        assert "CuratorAction" in __all__
        assert "SkillPatch" in __all__
        assert "SkillMiner" in __all__
        assert "QualityEvaluator" in __all__
        assert "PromotionGate" in __all__
        assert "InstinctExtractor" in __all__
        assert "ConfidenceScorer" in __all__
        assert "MarketplaceSync" in __all__
        assert "CuratorConfig" in __all__
        assert "EvaluationConfig" in __all__
        assert "GateConfig" in __all__
        assert "SyncConfig" in __all__
