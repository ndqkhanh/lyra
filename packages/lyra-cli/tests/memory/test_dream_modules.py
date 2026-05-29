"""Tests for dream modules — QuestionDrivenReflector and DreamScheduler."""

import time

import pytest
from lyra_cli.memory.dream_reflector import (
    QuestionDrivenReflector,
    QuestionType,
    ReflectionQuestion,
    ReflectionSession,
    ReflectionSignal,
    SignalStrength,
)
from lyra_cli.memory.dream_scheduler import (
    DreamScheduler,
    DreamScheduleTrigger,
    ScheduleEntry,
    SchedulerState,
)


class TestQuestionType:
    def test_all_types(self):
        assert QuestionType.FACTUAL.value == "factual"
        assert QuestionType.RELATIONAL.value == "relational"
        assert QuestionType.APPLIED.value == "applied"


class TestSignalStrength:
    def test_all_strengths(self):
        assert SignalStrength.STRONG.value == "strong"
        assert SignalStrength.MODERATE.value == "moderate"
        assert SignalStrength.WEAK.value == "weak"


class TestReflectionQuestion:
    def test_creation(self):
        q = ReflectionQuestion(
            question_id="q1",
            question_type=QuestionType.FACTUAL,
            text="What is Python?",
            source_memory_id="m1",
            created_at=time.time(),
        )
        assert q.question_id == "q1"
        assert q.question_type == QuestionType.FACTUAL
        assert q.source_memory_id == "m1"

    def test_frozen(self):
        q = ReflectionQuestion(
            question_id="q1",
            question_type=QuestionType.FACTUAL,
            text="test",
            source_memory_id="m1",
            created_at=time.time(),
        )
        with pytest.raises(Exception):
            q.text = "new"  # type: ignore[misc]


class TestReflectionSignal:
    def test_creation(self):
        rs = ReflectionSignal(
            memory_id="m1",
            strength=SignalStrength.STRONG,
            score=0.95,
            question_count=3,
            weak_questions=[],
            timestamp=time.time(),
        )
        assert rs.memory_id == "m1"
        assert rs.strength == SignalStrength.STRONG
        assert rs.score == 0.95

    def test_frozen(self):
        rs = ReflectionSignal(
            memory_id="m1",
            strength=SignalStrength.WEAK,
            score=0.2,
            question_count=1,
            weak_questions=["q1"],
            timestamp=time.time(),
        )
        with pytest.raises(Exception):
            rs.score = 1.0  # type: ignore[misc]


class TestQuestionDrivenReflector:
    def test_init(self):
        reflector = QuestionDrivenReflector()
        assert reflector.stats()["weak_threshold"] == 0.4
        assert reflector.stats()["strong_threshold"] == 0.8

    def test_reflect_empty_fragments(self):
        reflector = QuestionDrivenReflector()
        session = reflector.reflect([])
        assert isinstance(session, ReflectionSession)
        assert session.questions_generated == 0
        assert session.weak_memories == 0

    def test_reflect_single_fragment(self):
        reflector = QuestionDrivenReflector()
        fragments = [
            {
                "id": "m1",
                "entity": "Python",
                "name": "Python",
                "content":(
                    "Python is a high-level programming language known for its readability and"
                    "versatility."
                ),
            }
        ]
        session = reflector.reflect(fragments)
        assert session.questions_generated >= 2
        assert len(session.signals) == 1

    def test_reflect_with_related_entities(self):
        reflector = QuestionDrivenReflector()
        fragments = [
            {
                "id": "m1",
                "entity": "Python",
                "name": "Python",
                "content": "Python is a programming language.",
            }
        ]
        related = {"m1": ["JavaScript", "TypeScript"]}
        session = reflector.reflect(fragments, related_entities=related)
        assert session.questions_generated >= 2

    def test_reflect_detailed_content_scores_higher(self):
        reflector = QuestionDrivenReflector()
        detailed = [
            {
                "id": "m1",
                "entity": "Django",
                "name": "Django",
                "content":(
                    "Django is a high-level Python web framework that encourages rapid development"
                    "and clean, pragmatic design. It follows the model-template-view architectural"
                    "pattern."
                ),
            }
        ]
        sparse = [
            {
                "id": "m2",
                "entity": "Flask",
                "name": "Flask",
                "content": "Flask micro.",
            }
        ]
        session_detailed = reflector.reflect(detailed)
        session_sparse = reflector.reflect(sparse)
        assert session_detailed.signals[0].score >= session_sparse.signals[0].score

    def test_reflect_multiple_fragments(self):
        reflector = QuestionDrivenReflector()
        fragments = [
            {
                "id": f"m{i}",
                "entity": f"Entity{i}",
                "name": f"Entity{i}",
                "content": f"Content about entity {i} " * 10,
            }
            for i in range(5)
        ]
        session = reflector.reflect(fragments)
        assert len(session.signals) == 5
        assert session.elapsed_ms >= 0

    def test_reflect_fragment_without_entity(self):
        reflector = QuestionDrivenReflector()
        fragments = [{"id": "m1", "content": "just content no entity"}]
        session = reflector.reflect(fragments)
        assert session.questions_generated == 0


class TestDreamScheduleTrigger:
    def test_all_triggers(self):
        assert DreamScheduleTrigger.CYCLE.value == "consolidation.cycle"
        assert DreamScheduleTrigger.DEEP.value == "consolidation.deep"
        assert DreamScheduleTrigger.REVIEW.value == "consolidation.review"
        assert DreamScheduleTrigger.PRUNE.value == "consolidation.prune"
        assert DreamScheduleTrigger.ARCHIVE.value == "consolidation.archive"


class TestScheduleEntry:
    def test_creation(self):
        now = time.time()
        se = ScheduleEntry(
            trigger=DreamScheduleTrigger.CYCLE,
            interval_sec=21600,
            last_run=0.0,
            next_run=now + 21600,
        )
        assert se.trigger == DreamScheduleTrigger.CYCLE
        assert se.interval_sec == 21600
        assert se.enabled is True

    def test_frozen(self):
        now = time.time()
        se = ScheduleEntry(
            trigger=DreamScheduleTrigger.CYCLE,
            interval_sec=3600,
            last_run=0.0,
            next_run=now,
        )
        with pytest.raises(Exception):
            se.enabled = False  # type: ignore[misc]


class TestDreamScheduler:
    def test_init(self):
        scheduler = DreamScheduler()
        stats = scheduler.stats()
        assert stats["total_runs"] == 0
        assert len(stats["entries"]) == 5

    def test_all_triggers_registered(self):
        scheduler = DreamScheduler()
        for trigger in DreamScheduleTrigger:
            entry = scheduler.get_entry(trigger)
            assert entry is not None
            assert entry.enabled is True

    def test_tick_nothing_due_initially(self):
        scheduler = DreamScheduler()
        due = scheduler.tick()
        assert len(due) == 0

    def test_mark_run_updates_entry(self):
        scheduler = DreamScheduler()
        entry = scheduler.mark_run(DreamScheduleTrigger.CYCLE)
        assert entry.last_run > 0
        assert entry.next_run > entry.last_run
        assert scheduler.stats()["total_runs"] == 1

    def test_disable_and_enable(self):
        scheduler = DreamScheduler()
        scheduler.disable(DreamScheduleTrigger.CYCLE)
        entry = scheduler.get_entry(DreamScheduleTrigger.CYCLE)
        assert entry is not None
        assert entry.enabled is False

        scheduler.enable(DreamScheduleTrigger.CYCLE)
        entry = scheduler.get_entry(DreamScheduleTrigger.CYCLE)
        assert entry is not None
        assert entry.enabled is True

    def test_set_interval(self):
        scheduler = DreamScheduler()
        scheduler.set_interval(DreamScheduleTrigger.CYCLE, 3600.0)
        entry = scheduler.get_entry(DreamScheduleTrigger.CYCLE)
        assert entry is not None
        assert entry.interval_sec == 3600.0

    def test_get_state(self):
        scheduler = DreamScheduler()
        state = scheduler.get_state()
        assert isinstance(state, SchedulerState)
        assert len(state.entries) == 5
        assert state.total_runs == 0

    def test_run_due_when_nothing_due(self):
        scheduler = DreamScheduler()
        state = scheduler.run_due()
        assert state.total_runs == 0
        assert state.last_action == "none"

    def test_stats_has_all_triggers(self):
        scheduler = DreamScheduler()
        stats = scheduler.stats()
        for trigger in DreamScheduleTrigger:
            assert trigger.value in stats["entries"]

    def test_stats_entry_structure(self):
        scheduler = DreamScheduler()
        stats = scheduler.stats()
        entry = stats["entries"]["consolidation.cycle"]
        assert "interval_h" in entry
        assert "enabled" in entry
        assert "due" in entry
