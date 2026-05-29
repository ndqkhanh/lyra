"""Tests for Phase 7: Experience & Learning Engine."""

from __future__ import annotations

import pytest
from lyra_core.experience import (
    AntiPattern,
    AntiPatternRegistry,
    DistillationResult,
    DistilledSkill,
    ExperienceExtractor,
    ExperienceRecord,
    ExtractedPattern,
    ImprovementCycle,
    LearningLoop,
    LoopConfig,
    LoopState,
    MatchResult,
    PatternType,
    SkillCandidate,
    SkillDistiller,
)

# ═══════════════════════════════════════════════════════════════════════════════
# ExperienceRecord
# ═══════════════════════════════════════════════════════════════════════════════


class TestExperienceRecord:
    def test_create_success_record(self):
        rec = ExperienceRecord(
            id="er1", session_id="s1", task_signature="analyze code",
            outcome="success", turn_count=3,
        )
        assert rec.id == "er1"
        assert rec.is_success
        assert not rec.is_failure

    def test_create_failure_record(self):
        rec = ExperienceRecord(
            id="er2", session_id="s2", task_signature="build app",
            outcome="failure", turn_count=10, error_message="timeout",
        )
        assert rec.is_failure
        assert not rec.is_success
        assert rec.error_message == "timeout"

    def test_create_partial_record(self):
        rec = ExperienceRecord(
            id="er3", session_id="s3", task_signature="refactor module",
            outcome="partial", turn_count=5,
        )
        assert not rec.is_success
        assert not rec.is_failure

    def test_defaults(self):
        rec = ExperienceRecord(
            id="er4", session_id="s4", task_signature="test",
            outcome="success", turn_count=1,
        )
        assert rec.tool_calls == ()
        assert rec.final_artefact == ""
        assert rec.duration_ms == 0.0
        assert rec.metadata == {}

    def test_to_dict(self):
        rec = ExperienceRecord(
            id="er5", session_id="s5", task_signature="test",
            outcome="success", turn_count=2,
            tool_calls=({"name": "write", "args": {}},),
        )
        d = rec.to_dict()
        assert d["id"] == "er5"
        assert d["tool_calls"] == [{"name": "write", "args": {}}]

    def test_from_dict(self):
        rec = ExperienceRecord.from_dict({
            "id": "er6", "session_id": "s6", "task_signature": "test",
            "outcome": "failure", "turn_count": 1, "tool_calls": [],
        })
        assert rec.id == "er6"
        assert rec.is_failure

    def test_created_at_auto_set(self):
        rec = ExperienceRecord(
            id="er7", session_id="s7", task_signature="test",
            outcome="success", turn_count=1,
        )
        assert rec.created_at > 0


# ═══════════════════════════════════════════════════════════════════════════════
# PatternType
# ═══════════════════════════════════════════════════════════════════════════════


class TestPatternType:
    def test_all_values(self):
        values = {p.value for p in PatternType}
        assert "success_strategy" in values
        assert "failure_mode" in values
        assert "recovery_path" in values
        assert "optimization" in values
        assert "workaround" in values
        assert "anti_pattern" in values


# ═══════════════════════════════════════════════════════════════════════════════
# ExtractedPattern
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractedPattern:
    def test_create(self):
        ep = ExtractedPattern(
            id="ep1", pattern_type=PatternType.SUCCESS_STRATEGY,
            title="Fast fix", description="Completed quickly",
            source_record_ids=("er1",), confidence=0.9,
        )
        assert ep.pattern_type == PatternType.SUCCESS_STRATEGY
        assert ep.confidence == 0.9
        assert ep.tags == ()

    def test_with_tags(self):
        ep = ExtractedPattern(
            id="ep2", pattern_type=PatternType.FAILURE_MODE,
            title="Bad approach", description="Avoid this",
            source_record_ids=("er2",), confidence=0.7,
            tags=("error", "slow"),
        )
        assert ep.tags == ("error", "slow")


# ═══════════════════════════════════════════════════════════════════════════════
# ExperienceExtractor
# ═══════════════════════════════════════════════════════════════════════════════


class TestExperienceExtractor:
    def test_extract_success_record(self):
        extractor = ExperienceExtractor()
        rec = ExperienceRecord(
            id="er1", session_id="s1", task_signature="write tests",
            outcome="success", turn_count=2,
        )
        patterns = extractor.extract_one(rec)
        assert len(patterns) >= 1
        assert patterns[0].pattern_type == PatternType.SUCCESS_STRATEGY

    def test_extract_failure_record(self):
        extractor = ExperienceExtractor()
        rec = ExperienceRecord(
            id="er2", session_id="s2", task_signature="deploy app",
            outcome="failure", turn_count=8, error_message="connection refused",
        )
        patterns = extractor.extract_one(rec)
        assert any(p.pattern_type == PatternType.FAILURE_MODE for p in patterns)

    def test_extract_partial_record(self):
        extractor = ExperienceExtractor()
        rec = ExperienceRecord(
            id="er3", session_id="s3", task_signature="refactor",
            outcome="partial", turn_count=5,
        )
        patterns = extractor.extract_one(rec)
        assert any(p.pattern_type == PatternType.RECOVERY_PATH for p in patterns)

    def test_extract_batch(self):
        extractor = ExperienceExtractor()
        records = [
            ExperienceRecord(id=f"er{i}", session_id="s1",
                           task_signature="task", outcome="success", turn_count=2)
            for i in range(5)
        ]
        patterns = extractor.extract(records)
        assert len(patterns) == 5

    def test_respects_max_patterns(self):
        extractor = ExperienceExtractor(max_patterns_per_run=3)
        records = [
            ExperienceRecord(id=f"er{i}", session_id="s1",
                           task_signature="task", outcome="success", turn_count=2)
            for i in range(10)
        ]
        patterns = extractor.extract(records)
        assert len(patterns) <= 3

    def test_find_similar_by_tags(self):
        extractor = ExperienceExtractor()
        ep1 = ExtractedPattern(
            id="ep1", pattern_type=PatternType.SUCCESS_STRATEGY,
            title="A", description="desc", source_record_ids=("er1",),
            confidence=0.9, tags=("fast", "python"),
        )
        ep2 = ExtractedPattern(
            id="ep2", pattern_type=PatternType.FAILURE_MODE,
            title="B", description="desc", source_record_ids=("er2",),
            confidence=0.7, tags=("error", "python"),
        )
        ep3 = ExtractedPattern(
            id="ep3", pattern_type=PatternType.OPTIMIZATION,
            title="C", description="desc", source_record_ids=("er3",),
            confidence=0.8, tags=("javascript",),
        )
        similar = extractor.find_similar(ep1, [ep2, ep3])
        assert len(similar) == 1  # ep2 shares "python" tag
        assert similar[0].id == "ep2"

    def test_stats(self):
        extractor = ExperienceExtractor()
        rec = ExperienceRecord(
            id="er1", session_id="s1", task_signature="task",
            outcome="success", turn_count=1,
        )
        extractor.extract_one(rec)
        stats = extractor.stats
        assert stats["records_processed"] == 0  # extract_one doesn't increment
        assert stats["patterns_extracted"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# AntiPattern
# ═══════════════════════════════════════════════════════════════════════════════


class TestAntiPattern:
    def test_create(self):
        ap = AntiPattern(
            id="ap1", name="hardcoded_secret", description="API key in code",
            severity="critical", pattern_source="code_review",
            detection_rule="api_key", suggested_fix="Use env var",
        )
        assert ap.severity == "critical"
        assert ap.occurrence_count == 0

    def test_with_occurrence_returns_new(self):
        ap = AntiPattern(
            id="ap1", name="test", description="desc",
            severity="low", pattern_source="test",
        )
        ap2 = ap.with_occurrence()
        assert ap2.occurrence_count == 1
        assert ap.occurrence_count == 0  # Original unchanged
        assert ap2.id == ap.id


# ═══════════════════════════════════════════════════════════════════════════════
# MatchResult
# ═══════════════════════════════════════════════════════════════════════════════


class TestMatchResult:
    def test_matched(self):
        ap = AntiPattern(
            id="ap1", name="test", description="desc",
            severity="low", pattern_source="test",
        )
        mr = MatchResult(anti_pattern=ap, matched=True, confidence=0.9,
                        evidence="found match")
        assert mr.matched
        assert mr.confidence == 0.9

    def test_not_matched(self):
        ap = AntiPattern(
            id="ap2", name="test2", description="desc",
            severity="medium", pattern_source="test",
        )
        mr = MatchResult(anti_pattern=ap, matched=False, confidence=0.1)
        assert not mr.matched


# ═══════════════════════════════════════════════════════════════════════════════
# AntiPatternRegistry
# ═══════════════════════════════════════════════════════════════════════════════


class TestAntiPatternRegistry:
    def test_register_and_count(self):
        reg = AntiPatternRegistry()
        ap = AntiPattern(
            id="ap1", name="test", description="desc",
            severity="high", pattern_source="test",
        )
        reg.register(ap)
        assert reg.count == 1

    def test_unregister(self):
        reg = AntiPatternRegistry()
        ap = AntiPattern(
            id="ap1", name="test", description="desc",
            severity="low", pattern_source="test",
        )
        reg.register(ap)
        assert reg.unregister("ap1")
        assert reg.count == 0

    def test_unregister_nonexistent(self):
        reg = AntiPatternRegistry()
        assert not reg.unregister("nope")

    def test_match_by_detection_rule(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="hardcoded_key", description="API key in source",
            severity="critical", pattern_source="audit",
            detection_rule="sk-",
        ))
        results = reg.match("const key = 'sk-abc123'")
        assert len(results) >= 1
        assert results[0].matched

    def test_match_by_name_fallback(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="sql_injection", description="Unsafe SQL",
            severity="critical", pattern_source="audit",
        ))
        results = reg.match("possible sql_injection in query")
        assert len(results) >= 1

    def test_match_respects_min_confidence(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="test_pattern", description="desc",
            severity="low", pattern_source="test",
        ))
        results = reg.match("test_pattern here", min_confidence=0.9)
        assert len(results) == 0  # Name match is 0.5

    def test_match_no_rule_name_fallback(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="orphan", description="No detection rule",
            severity="low", pattern_source="test",
        ))
        results = reg.match("orphan mentioned here")
        assert len(results) == 1  # Name fallback still matches

    def test_match_all(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="debug_print", description="Debug statement",
            severity="low", pattern_source="lint",
            detection_rule="print(",
        ))
        results = reg.match_all(["print('hello')", "print('world')"])
        assert len(results) == 2

    def test_get_by_severity(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="critical_1", description="d",
            severity="critical", pattern_source="test",
        ))
        reg.register(AntiPattern(
            id="ap2", name="low_1", description="d",
            severity="low", pattern_source="test",
        ))
        assert len(reg.get_by_severity("critical")) == 1
        assert len(reg.get_by_severity("low")) == 1

    def test_get_frequent(self):
        reg = AntiPatternRegistry()
        ap = AntiPattern(
            id="ap1", name="frequent", description="d",
            severity="medium", pattern_source="test",
            occurrence_count=10,
        )
        reg.register(ap)
        assert len(reg.get_frequent(min_occurrences=5)) == 1
        assert len(reg.get_frequent(min_occurrences=20)) == 0

    def test_merge_deduplicates_by_name(self):
        reg1 = AntiPatternRegistry()
        reg2 = AntiPatternRegistry()
        ap = AntiPattern(
            id="ap1", name="shared_pattern", description="d",
            severity="medium", pattern_source="a",
        )
        reg1.register(ap)
        reg2.register(AntiPattern(
            id="ap2", name="shared_pattern", description="d2",
            severity="medium", pattern_source="b",
        ))
        reg1.merge(reg2)
        assert reg1.count == 1  # Duplicate by name

    def test_to_list(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="p1", description="d",
            severity="low", pattern_source="test",
        ))
        lst = reg.to_list()
        assert len(lst) == 1
        assert lst[0].name == "p1"

    def test_by_tag(self):
        reg = AntiPatternRegistry()
        reg.register(AntiPattern(
            id="ap1", name="p1", description="d",
            severity="low", pattern_source="test",
            tags=("security", "auth"),
        ))
        reg.register(AntiPattern(
            id="ap2", name="p2", description="d",
            severity="medium", pattern_source="test",
            tags=("performance",),
        ))
        assert len(reg.by_tag("security")) == 1
        assert len(reg.by_tag("performance")) == 1

    def test_max_patterns_evicts_oldest(self):
        reg = AntiPatternRegistry(max_patterns=2)
        reg.register(AntiPattern(
            id="ap1", name="old", description="d",
            severity="low", pattern_source="test",
            last_seen=100.0,
        ))
        reg.register(AntiPattern(
            id="ap2", name="mid", description="d",
            severity="low", pattern_source="test",
            last_seen=200.0,
        ))
        reg.register(AntiPattern(
            id="ap3", name="new", description="d",
            severity="low", pattern_source="test",
            last_seen=300.0,
        ))
        assert reg.count == 2
        names = {p.name for p in reg.to_list()}
        assert "old" not in names


# ═══════════════════════════════════════════════════════════════════════════════
# SkillCandidate
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkillCandidate:
    def test_create(self):
        sc = SkillCandidate(
            id="sc1", name="Fast testing", description="Write tests quickly",
            trigger_condition="When testing is needed",
            source_patterns=("ep1",), confidence=0.85,
        )
        assert sc.confidence == 0.85
        assert sc.usage_estimate == 0


# ═══════════════════════════════════════════════════════════════════════════════
# DistilledSkill
# ═══════════════════════════════════════════════════════════════════════════════


class TestDistilledSkill:
    def test_create(self):
        ds = DistilledSkill(
            id="ds1", name="Fast testing", description="Test quickly",
            body="# Skill body", source_candidates=("sc1",),
            verification_score=0.9, verified=True,
        )
        assert ds.verified
        assert not ds.deployed

    def test_deploy_returns_new(self):
        ds = DistilledSkill(
            id="ds1", name="Fast testing", description="Test quickly",
            body="# body", source_candidates=("sc1",),
            verification_score=0.9, verified=True,
        )
        ds2 = ds.deploy()
        assert ds2.deployed
        assert not ds.deployed  # Original unchanged
        assert ds2.deployed_at is not None

    def test_undeploy(self):
        ds = DistilledSkill(
            id="ds1", name="Fast testing", description="Test quickly",
            body="# body", source_candidates=("sc1",),
            verification_score=0.9, verified=True, deployed=True,
        )
        ds2 = ds.undeploy()
        assert not ds2.deployed


# ═══════════════════════════════════════════════════════════════════════════════
# SkillDistiller
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkillDistiller:
    def test_propose_candidates_from_success_patterns(self):
        distiller = SkillDistiller(min_confidence=0.6)
        patterns = [
            ExtractedPattern(
                id="ep1", pattern_type=PatternType.SUCCESS_STRATEGY,
                title="Quick fix", description="Done fast",
                source_record_ids=("er1",), confidence=0.9,
            ),
        ]
        candidates = distiller.propose_candidates(patterns)
        assert len(candidates) == 1
        assert candidates[0].confidence == 0.9

    def test_skips_low_confidence_patterns(self):
        distiller = SkillDistiller(min_confidence=0.8)
        patterns = [
            ExtractedPattern(
                id="ep1", pattern_type=PatternType.SUCCESS_STRATEGY,
                title="Weak pattern", description="Low conf",
                source_record_ids=("er1",), confidence=0.5,
            ),
        ]
        candidates = distiller.propose_candidates(patterns)
        assert len(candidates) == 0

    def test_skips_failure_and_anti_patterns(self):
        distiller = SkillDistiller()
        patterns = [
            ExtractedPattern(
                id="ep1", pattern_type=PatternType.FAILURE_MODE,
                title="Bad", description="desc",
                source_record_ids=("er1",), confidence=0.9,
            ),
            ExtractedPattern(
                id="ep2", pattern_type=PatternType.ANTI_PATTERN,
                title="Worse", description="desc",
                source_record_ids=("er2",), confidence=0.9,
            ),
        ]
        candidates = distiller.propose_candidates(patterns)
        assert len(candidates) == 0

    def test_respects_max_per_run(self):
        distiller = SkillDistiller(max_skills_per_run=2)
        patterns = [
            ExtractedPattern(
                id=f"ep{i}", pattern_type=PatternType.SUCCESS_STRATEGY,
                title=f"Pattern {i}", description="desc",
                source_record_ids=(f"er{i}",), confidence=0.9,
            )
            for i in range(5)
        ]
        candidates = distiller.propose_candidates(patterns)
        assert len(candidates) == 2

    def test_evaluate_candidate_score(self):
        distiller = SkillDistiller()
        sc = SkillCandidate(
            id="sc1", name="test", description="desc",
            trigger_condition="when", source_patterns=("ep1", "ep2"),
            confidence=0.8, usage_estimate=5,
        )
        score = distiller.evaluate_candidate(sc)
        assert score > 0.8  # Bonus for usage_estimate>=3 and multiple sources

    def test_distill_verified_skills(self):
        distiller = SkillDistiller(min_confidence=0.6, require_verification=True)
        candidates = [
            SkillCandidate(
                id="sc1", name="Useful skill", description="Very useful",
                trigger_condition="Always", source_patterns=("ep1",),
                confidence=0.95, usage_estimate=4,
            ),
        ]
        result = distiller.distill(candidates)
        assert result.skills_distilled == 1
        assert result.skills_deployed == 1  # >= 0.85 auto-deployed
        assert result.skills_rejected == 0
        assert distiller.deployed_count >= 1

    def test_distill_rejects_below_threshold(self):
        distiller = SkillDistiller(min_confidence=0.8, require_verification=True)
        candidates = [
            SkillCandidate(
                id="sc1", name="Weak skill", description="desc",
                trigger_condition="rarely", source_patterns=("ep1",),
                confidence=0.5, usage_estimate=1,
            ),
        ]
        result = distiller.distill(candidates)
        assert result.skills_rejected == 1

    def test_deploy_and_undeploy(self):
        distiller = SkillDistiller(require_verification=False)
        candidates = [
            SkillCandidate(
                id="sc1", name="Deployable", description="d",
                trigger_condition="t", source_patterns=("ep1",),
                confidence=0.7, usage_estimate=1,
            ),
        ]
        distiller.distill(candidates)
        skills = distiller.get_deployed()
        assert len(skills) == 0  # Not auto-deployed (score 0.7 < 0.85)
        # Find the skill and manually deploy
        skill = distiller.get_by_name("Deployable")
        assert skill is not None
        assert distiller.deploy(skill.id)
        assert distiller.deployed_count == 1
        assert distiller.undeploy(skill.id)
        assert distiller.deployed_count == 0

    def test_deploy_nonexistent_returns_false(self):
        distiller = SkillDistiller()
        assert not distiller.deploy("nope")


# ═══════════════════════════════════════════════════════════════════════════════
# LoopConfig / LoopState
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoopConfig:
    def test_defaults(self):
        config = LoopConfig()
        assert config.min_records_before_extract == 10
        assert config.auto_promote_threshold == 0.8
        assert config.prune_older_than_days == 30

    def test_custom(self):
        config = LoopConfig(min_records_before_extract=5, max_anti_patterns=100)
        assert config.min_records_before_extract == 5
        assert config.max_anti_patterns == 100


class TestLoopState:
    def test_all_states(self):
        values = {s.value for s in LoopState}
        assert "idle" in values
        assert "collecting" in values
        assert "extracting" in values
        assert "evaluating" in values
        assert "integrating" in values
        assert "error" in values


# ═══════════════════════════════════════════════════════════════════════════════
# ImprovementCycle
# ═══════════════════════════════════════════════════════════════════════════════


class TestImprovementCycle:
    def test_create(self):
        cycle = ImprovementCycle(
            cycle_id="c1", state_before=LoopState.COLLECTING,
            state_after=LoopState.COLLECTING,
            records_processed=10, patterns_extracted=3,
            lessons_promoted=1, skills_distilled=1,
            anti_patterns_identified=2, duration_ms=150.0,
        )
        assert cycle.records_processed == 10
        assert cycle.patterns_extracted == 3

    def test_defaults(self):
        cycle = ImprovementCycle(
            cycle_id="c2", state_before=LoopState.IDLE,
            state_after=LoopState.IDLE,
            records_processed=0, patterns_extracted=0,
            lessons_promoted=0, skills_distilled=0,
            anti_patterns_identified=0, duration_ms=0.0,
        )
        assert cycle.error == ""
        assert cycle.timestamp > 0


# ═══════════════════════════════════════════════════════════════════════════════
# LearningLoop
# ═══════════════════════════════════════════════════════════════════════════════


class TestLearningLoop:
    def test_initial_state(self):
        loop = LearningLoop()
        assert loop.state == LoopState.IDLE
        assert not loop.is_running

    @pytest.mark.asyncio
    async def test_start_stop(self):
        loop = LearningLoop()
        await loop.start()
        assert loop.is_running
        assert loop.state == LoopState.COLLECTING
        await loop.stop()
        assert not loop.is_running
        assert loop.state == LoopState.IDLE

    @pytest.mark.asyncio
    async def test_submit_record(self):
        loop = LearningLoop()
        await loop.start()
        rec = ExperienceRecord(
            id="er1", session_id="s1", task_signature="task",
            outcome="success", turn_count=2,
        )
        await loop.submit_record(rec)
        assert len(loop.get_pending_records()) == 1

    @pytest.mark.asyncio
    async def test_run_cycle_insufficient_records(self):
        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=5),
        )
        await loop.start()
        cycle = await loop.run_cycle()
        assert cycle.records_processed == 0
        assert "Insufficient" in cycle.error

    @pytest.mark.asyncio
    async def test_run_cycle_extracts_patterns(self):
        extractor = ExperienceExtractor()
        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=2),
            extractor=extractor,
        )
        await loop.start()
        for i in range(3):
            rec = ExperienceRecord(
                id=f"er{i}", session_id="s1", task_signature="test",
                outcome="success", turn_count=1,
            )
            await loop.submit_record(rec)

        cycle = await loop.run_cycle()
        assert cycle.patterns_extracted >= 1
        assert cycle.records_processed == 3

    @pytest.mark.asyncio
    async def test_run_cycle_with_skill_distillation(self):
        extractor = ExperienceExtractor()
        distiller = SkillDistiller(min_confidence=0.5, max_skills_per_run=5)
        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=1),
            extractor=extractor,
            skill_distiller=distiller,
        )
        await loop.start()
        rec = ExperienceRecord(
            id="er1", session_id="s1", task_signature="optimize",
            outcome="success", turn_count=1, final_artefact="refactored code",
        )
        await loop.submit_record(rec)
        cycle = await loop.run_cycle()
        assert cycle.patterns_extracted >= 1
        assert cycle.skills_distilled >= 1

    @pytest.mark.asyncio
    async def test_run_cycle_registers_anti_patterns(self):
        extractor = ExperienceExtractor()
        anti_reg = AntiPatternRegistry()
        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=1),
            extractor=extractor,
            anti_pattern_registry=anti_reg,
        )
        await loop.start()
        rec = ExperienceRecord(
            id="er1", session_id="s1", task_signature="bad deploy",
            outcome="failure", turn_count=10, error_message="connection refused",
        )
        await loop.submit_record(rec)
        cycle = await loop.run_cycle()
        assert cycle.anti_patterns_identified >= 1
        assert anti_reg.count >= 1

    @pytest.mark.asyncio
    async def test_run_cycles_multiple(self):
        extractor = ExperienceExtractor()
        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=1),
            extractor=extractor,
        )
        await loop.start()
        for i in range(3):
            rec = ExperienceRecord(
                id=f"er{i}", session_id="s1", task_signature="task",
                outcome="success", turn_count=1,
            )
            await loop.submit_record(rec)

        cycles = await loop.run_cycles(2)
        assert len(cycles) == 2

    @pytest.mark.asyncio
    async def test_cycle_history(self):
        extractor = ExperienceExtractor()
        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=1),
            extractor=extractor,
        )
        await loop.start()
        rec = ExperienceRecord(
            id="er1", session_id="s1", task_signature="task",
            outcome="success", turn_count=1,
        )
        await loop.submit_record(rec)
        await loop.run_cycle()
        history = loop.cycle_history
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_total_patterns_extracted(self):
        extractor = ExperienceExtractor()
        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=1),
            extractor=extractor,
        )
        await loop.start()
        for i in range(2):
            rec = ExperienceRecord(
                id=f"er{i}", session_id="s1", task_signature="task",
                outcome="success", turn_count=1,
            )
            await loop.submit_record(rec)

        await loop.run_cycle()
        assert loop.total_patterns_extracted >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Extractor + Distiller + AntiPatterns
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_learning_pipeline(self):
        """End-to-end: records → extract → distill → anti-patterns."""
        extractor = ExperienceExtractor(min_confidence=0.5)
        distiller = SkillDistiller(min_confidence=0.5, max_skills_per_run=5)
        anti_reg = AntiPatternRegistry()

        loop = LearningLoop(
            config=LoopConfig(min_records_before_extract=2),
            extractor=extractor,
            skill_distiller=distiller,
            anti_pattern_registry=anti_reg,
        )
        await loop.start()

        # Submit mix of success and failure
        await loop.submit_record(ExperienceRecord(
            id="er1", session_id="s1", task_signature="optimize SQL",
            outcome="success", turn_count=2, final_artefact="optimized query",
        ))
        await loop.submit_record(ExperienceRecord(
            id="er2", session_id="s1", task_signature="deploy to prod",
            outcome="failure", turn_count=12,
            error_message="connection timeout to database",
        ))
        await loop.submit_record(ExperienceRecord(
            id="er3", session_id="s2", task_signature="refactor auth",
            outcome="success", turn_count=1, final_artefact="clean auth module",
        ))

        cycle = await loop.run_cycle()

        # Assertions
        assert cycle.patterns_extracted >= 3
        assert cycle.skills_distilled >= 1
        assert cycle.anti_patterns_identified >= 1
        assert anti_reg.count >= 1
        assert distiller.candidate_count >= 1

        await loop.stop()

    def test_extractor_and_distiller_composition(self):
        """Patterns extracted from records flow into skill candidates."""
        extractor = ExperienceExtractor(min_confidence=0.5)
        distiller = SkillDistiller(min_confidence=0.5)

        records = [
            ExperienceRecord(
                id=f"er{i}", session_id="s1", task_signature="write function",
                outcome="success", turn_count=1,
                final_artefact=f"def func_{i}(): pass",
            )
            for i in range(5)
        ]
        patterns = extractor.extract(records)
        candidates = distiller.propose_candidates(patterns)
        assert len(candidates) >= 1
        result = distiller.distill(candidates)
        assert result.skills_distilled >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# DistillationResult
# ═══════════════════════════════════════════════════════════════════════════════


class TestDistillationResult:
    def test_create(self):
        result = DistillationResult(
            run_id="r1", candidates_evaluated=5,
            skills_distilled=3, skills_deployed=2, skills_rejected=1,
            rejection_reasons=("low confidence",), duration_ms=100.0,
        )
        assert result.skills_distilled == 3
        assert result.skills_rejected == 1
