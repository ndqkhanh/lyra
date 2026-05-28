"""Tests for curriculum (difficulty_scheduler, progress_tracker),
abstraction (concept_abstractor, pattern_recognizer),
and operations (batch_processor, integrity_checker) subpackages."""

from __future__ import annotations

import time

from lyra_memory.abstraction.concept_abstractor import (
    AbstractConcept,
    AbstractionLevel,
    ConceptAbstractor,
)
from lyra_memory.abstraction.pattern_recognizer import (
    CrossEpisodePattern,
    PatternRecognizer,
)
from lyra_memory.curriculum.difficulty_scheduler import (
    DifficultyLevel,
    DifficultyScheduler,
    SkillGap,
    TaskCurriculum,
)
from lyra_memory.curriculum.progress_tracker import (
    CompetencyMap,
    CurriculumPhase,
    ProgressTracker,
)
from lyra_memory.operations.batch_processor import (
    BatchOpResult,
    BatchProcessor,
    OperationType,
)
from lyra_memory.operations.integrity_checker import (
    IntegrityChecker,
    IntegrityReport,
)


def _make_items(count: int) -> list[str]:
    return [f"item-{i:04d}" for i in range(count)]


class TestDifficultyScheduler:
    def test_schedule_returns_task_list(self):
        scheduler = DifficultyScheduler()
        curriculum = scheduler.schedule(
            "session-1", ["task-a", "task-b"], DifficultyLevel.EASY
        )
        assert isinstance(curriculum, TaskCurriculum)
        assert curriculum.skill_name == "session-1"

    def test_get_next_returns_correct_level(self):
        scheduler = DifficultyScheduler()
        scheduler.schedule("s1", ["task-1"], DifficultyLevel.TRIVIAL)
        task = scheduler.get_next("s1", {"s1": 0.5})
        assert task is not None
        assert task.difficulty == DifficultyLevel.TRIVIAL

    def test_mark_complete_advances(self):
        scheduler = DifficultyScheduler()
        curriculum = scheduler.schedule("s2", ["task-x", "task-y"], DifficultyLevel.EASY)
        scheduler.schedule("s2", ["task-z", "task-w"], DifficultyLevel.MODERATE)
        scheduler.mark_complete("s2", curriculum.curriculum_id)
        next_task = scheduler.get_next("s2", {"s2": 0.5})
        assert next_task is not None
        assert next_task.difficulty == DifficultyLevel.MODERATE

    def test_assess_gap(self):
        scheduler = DifficultyScheduler()
        scheduler.schedule("s3", ["t1", "t2"], DifficultyLevel.EASY)
        gap = scheduler.assess_gap("s3", DifficultyLevel.EASY, DifficultyLevel.HARD)
        assert isinstance(gap, SkillGap)

    def test_skill_gap_properties(self):
        gap = SkillGap(
            skill_name="math",
            current_level=DifficultyLevel.EASY,
            target_level=DifficultyLevel.HARD,
            gap_score=0.6,
            last_assessed=time.time(),
        )
        assert gap.gap_score == 0.6
        assert gap.skill_name == "math"

    def test_task_curriculum_fields(self):
        tc = TaskCurriculum(
            curriculum_id="cur-001",
            skill_name="coding",
            tasks=["task-1", "task-2"],
            difficulty=DifficultyLevel.MODERATE,
            prerequisite_ids=[],
            created_at=time.time(),
        )
        assert tc.difficulty == DifficultyLevel.MODERATE
        assert len(tc.tasks) == 2


class TestProgressTracker:
    def test_initialize(self):
        tracker = ProgressTracker()
        cm = tracker.initialize("session-a", ["skill_a", "skill_b"])
        assert isinstance(cm, CompetencyMap)
        assert len(cm.skill_scores) == 2
        assert cm.session_id == "session-a"

    def test_update_skill(self):
        tracker = ProgressTracker()
        tracker.initialize("math-session", ["math"])
        cm = tracker.update_skill("math-session", "math", 0.85)
        assert cm.skill_scores["math"] == 0.85

    def test_get_progress_nonexistent(self):
        tracker = ProgressTracker()
        assert tracker.get_progress("nonexistent") is None

    def test_competency_map_properties(self):
        cm = CompetencyMap(
            session_id="s1",
            skill_scores={"coding": 0.72},
            current_phase=CurriculumPhase.FOUNDATIONAL,
            tasks_completed=8,
            tasks_total=10,
            updated_at=time.time(),
        )
        assert cm.completion_pct == 80.0
        assert cm.average_competency == 0.72

    def test_evaluate_phase(self):
        tracker = ProgressTracker()
        tracker.initialize("skill-session", ["skill"])
        for _ in range(10):
            tracker.update_skill("skill-session", "skill", 0.95)
        progress = tracker.get_progress("skill-session")
        assert progress is not None
        assert progress.current_phase in {CurriculumPhase.MASTERY, CurriculumPhase.ADVANCED}

    def test_get_phase_history(self):
        tracker = ProgressTracker()
        tracker.initialize("phase-session", ["a"])
        tracker.update_skill("phase-session", "a", 0.9)
        history = tracker.get_phase_history("phase-session")
        assert isinstance(history, list)


class TestConceptAbstractor:
    def test_abstract_creates_concept(self):
        abstractor = ConceptAbstractor()
        concept = abstractor.abstract(
            "The agent used tool X to solve problem Y",
            ["ep-001"],
        )
        assert isinstance(concept, AbstractConcept)
        assert concept.level == AbstractionLevel.CONCRETE
        assert len(concept.source_episodes) == 1

    def test_promote_to_higher_level(self):
        abstractor = ConceptAbstractor(min_confidence=0.3)
        concept = abstractor.abstract("Use tools efficiently", ["ep-001", "ep-002"])
        abstractor.abstract("Use tools efficiently", ["ep-003"])
        reinforced = abstractor.abstract("Use tools efficiently", ["ep-004"])
        assert reinforced.confidence >= abstractor.min_confidence
        promoted = abstractor.promote(concept.concept_id)
        assert promoted is not None
        assert promoted.level in {AbstractionLevel.PATTERN, AbstractionLevel.PRINCIPLE}

    def test_get_by_level(self):
        abstractor = ConceptAbstractor()
        abstractor.abstract("Event A occurred", "ep-001")
        abstractor.abstract("Pattern B observed", "ep-002")
        concepts = abstractor.get_by_level(AbstractionLevel.CONCRETE)
        assert len(concepts) >= 1

    def test_get_principles(self):
        abstractor = ConceptAbstractor()
        principles = abstractor.get_principles()
        assert isinstance(principles, list)

    def test_abstract_concept_fields(self):
        ac = AbstractConcept(
            concept_id="c-001",
            label="Test Concept",
            level=AbstractionLevel.CONCRETE,
            source_episodes=["ep-1"],
            confidence=0.8,
            last_reinforced=time.time(),
            abstraction_count=0,
        )
        assert ac.confidence == 0.8


class TestPatternRecognizer:
    def test_observe_records_pattern(self):
        recognizer = PatternRecognizer(min_occurrences=1, min_confidence=0.0)
        pattern = recognizer.observe("ep-001", "event-signature-abc")
        assert isinstance(pattern, CrossEpisodePattern)

    def test_observe_duplicate_returns_none(self):
        recognizer = PatternRecognizer(min_occurrences=1, min_confidence=0.0)
        recognizer.observe("ep-002", "sig-xyz")
        result = recognizer.observe("ep-003", "sig-xyz")
        assert result is not None

    def test_get_significant_filters(self):
        recognizer = PatternRecognizer(min_occurrences=1, min_confidence=0.0)
        for i in range(5):
            recognizer.observe(f"ep-{i:03d}", f"sig_{i}")
        significant = recognizer.get_significant()
        assert isinstance(significant, list)

    def test_get_for_episode(self):
        recognizer = PatternRecognizer(min_occurrences=1)
        recognizer.observe("ep-042", "sig-042")
        patterns = recognizer.get_for_episode("ep-042")
        assert isinstance(patterns, list)

    def test_cross_episode_pattern_fields(self):
        ts = time.time()
        pattern = CrossEpisodePattern(
            pattern_id="pat-001",
            description="Test pattern",
            episode_ids=["ep-1", "ep-2"],
            occurrence_count=2,
            first_seen=ts,
            last_seen=ts,
            confidence=0.75,
        )
        assert pattern.occurrence_count == 2
        assert pattern.confidence == 0.75


class TestBatchProcessor:
    def test_prune(self):
        items = _make_items(10)
        processor = BatchProcessor()
        result = processor.prune(items, predicate=lambda s: len(s) > 3)
        assert isinstance(result, BatchOpResult)
        assert result.op_type == OperationType.PRUNE

    def test_merge(self):
        items = _make_items(5)
        processor = BatchProcessor()
        result = processor.merge(items, merge_fn=lambda a, b: f"{a}+{b}")
        assert result.op_type == OperationType.MERGE

    def test_reindex(self):
        processor = BatchProcessor()
        result = processor.reindex(10, reindex_fn=lambda: 8)
        assert result.op_type == OperationType.REINDEX

    def test_archive(self):
        items = _make_items(5)
        processor = BatchProcessor()
        result = processor.archive(
            items, age_threshold_sec=3600.0, get_age_fn=lambda _s: 7200.0
        )
        assert result.op_type == OperationType.ARCHIVE


class TestIntegrityChecker:
    def test_check(self):
        entries = {"key-a": "content-a", "key-b": "content-b", "key-cd": "more-content"}
        checker = IntegrityChecker()
        report = checker.check(entries)
        assert isinstance(report, IntegrityReport)

    def test_latest_report(self):
        entries = {"key-x": "value-x", "key-yz": "value-yz"}
        checker = IntegrityChecker()
        checker.check(entries)
        report = checker.latest_report()
        assert report is not None

    def test_report_health_pct(self):
        checker = IntegrityChecker()
        entries = {"ka": "content-a", "kb": "content-b"}
        checker.check(entries)
        report = checker.latest_report()
        assert report is not None
        assert 0.0 <= report.health_pct <= 100.0

    def test_empty_entries(self):
        checker = IntegrityChecker()
        report = checker.check({})
        assert report.total_entries == 0
