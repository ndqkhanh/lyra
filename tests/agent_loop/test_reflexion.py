"""
Tests for ReflexionLoop, Lesson, LessonGenerator, ReflectionMemory, StrategyInjector.

Covers:
  - Lesson dataclass (creation, content_hash, immutability)
  - LessonGenerator (extraction from errors, tool calls, content, fallbacks)
  - ReflectionMemory (store, retrieve, deduplication, statistics)
  - StrategyInjector (message injection with and without system messages)
  - ReflexionLoop (run, statistics, context building)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lyra.agent_loop.executor import AgentLoopExecutor, HookBlockedError
from lyra.agent_loop.reflexion import (
    DEFAULT_MAX_ITERATIONS,
    MAX_LESSONS_PER_TRAJECTORY,
    REFLECTION_MEMORY_SLOT,
    SIMILARITY_TRIGGER_THRESHOLD,
    Lesson,
    LessonGenerator,
    ReflectionMemory,
    ReflexionLoop,
    StrategyInjector,
)
from lyra.core.task import Result, TaskStatus
from lyra.routing.provider.types import Message, ToolCall, TokenUsage


# ======================================================================
# Lesson tests
# ======================================================================


class TestLesson:
    """Tests for the Lesson dataclass."""

    def test_create_lesson(self) -> None:
        lesson = Lesson(
            lesson_id="abc123",
            source_task_id="task_001",
            outcome="failure",
            principle="Always validate input before calling external APIs",
            trigger_conditions=("validation", "api"),
            task_type="coding",
            metadata={"agent": "test"},
        )

        assert lesson.lesson_id == "abc123"
        assert lesson.source_task_id == "task_001"
        assert lesson.outcome == "failure"
        assert lesson.principle == "Always validate input before calling external APIs"
        assert lesson.trigger_conditions == ("validation", "api")
        assert lesson.task_type == "coding"
        assert lesson.metadata == {"agent": "test"}

    def test_lesson_default_created_at(self) -> None:
        """created_at is auto-set when not provided."""
        lesson = Lesson(
            lesson_id="x",
            source_task_id="t",
            outcome="success",
            principle="p",
        )
        assert lesson.created_at > 0

    def test_lesson_provided_created_at(self) -> None:
        """created_at is preserved when explicitly set."""
        lesson = Lesson(
            lesson_id="x",
            source_task_id="t",
            outcome="success",
            principle="p",
            created_at=12345.0,
        )
        assert lesson.created_at == 12345.0

    def test_lesson_is_frozen(self) -> None:
        """Lesson is immutable."""
        lesson = Lesson(
            lesson_id="x",
            source_task_id="t",
            outcome="success",
            principle="p",
        )
        with pytest.raises((AttributeError, TypeError)):
            lesson.principle = "changed"  # type: ignore[misc]

    def test_content_hash_is_deterministic(self) -> None:
        """Same content produces same hash."""
        a = Lesson(
            lesson_id="id_a",
            source_task_id="t1",
            outcome="success",
            principle="Validate inputs",
            trigger_conditions=("validation",),
        )
        b = Lesson(
            lesson_id="id_b",
            source_task_id="t2",
            outcome="success",
            principle="Validate inputs",
            trigger_conditions=("validation",),
        )
        assert a.content_hash == b.content_hash

    def test_content_hash_different_content(self) -> None:
        """Different content produces different hash."""
        a = Lesson(
            lesson_id="x",
            source_task_id="t",
            outcome="success",
            principle="Validate inputs",
        )
        b = Lesson(
            lesson_id="y",
            source_task_id="t",
            outcome="success",
            principle="Sanitize outputs",
        )
        assert a.content_hash != b.content_hash

    def test_content_hash_short_length(self) -> None:
        """Content hash is a short hex string (12 chars)."""
        lesson = Lesson(
            lesson_id="x",
            source_task_id="t",
            outcome="success",
            principle="Test principle",
        )
        assert len(lesson.content_hash) == 12

    def test_lesson_default_trigger_conditions(self) -> None:
        """Default trigger_conditions is empty tuple."""
        lesson = Lesson(
            lesson_id="x",
            source_task_id="t",
            outcome="success",
            principle="p",
        )
        assert lesson.trigger_conditions == ()

    def test_lesson_default_task_type(self) -> None:
        """Default task_type is empty string."""
        lesson = Lesson(
            lesson_id="x",
            source_task_id="t",
            outcome="success",
            principle="p",
        )
        assert lesson.task_type == ""


# ======================================================================
# LessonGenerator tests
# ======================================================================


class TestLessonGenerator:
    """Tests for LessonGenerator — extraction from trajectories."""

    def test_extract_from_failure_with_error(self) -> None:
        """Failure with error messages triggers lesson extraction."""
        gen = LessonGenerator()
        outcome = Result(
            task_id="t1", success=False, error="TimeoutError: API timed out"
        )
        trajectory = [Message(role="assistant", content="I'll call the API.")]

        lessons = gen.extract(trajectory, outcome)
        assert len(lessons) >= 1
        assert any("timeout" in l.principle.lower() for l in lessons)
        assert all(l.outcome == "failure" for l in lessons)

    def test_extract_from_failure_no_error(self) -> None:
        """Failure without recognized error keywords still produces fallback lesson."""
        gen = LessonGenerator()
        outcome = Result(
            task_id="t1", success=False, error="UnknownError: something broke"
        )
        trajectory = [Message(role="assistant", content="Done.")]

        lessons = gen.extract(trajectory, outcome)
        assert len(lessons) >= 1  # fallback

    def test_extract_from_success(self) -> None:
        """Success produces a lesson (fallback if no signals)."""
        gen = LessonGenerator()
        outcome = Result(
            task_id="t1", success=True, data="All good", metadata={}
        )
        trajectory = [Message(role="assistant", content="Completed.")]

        lessons = gen.extract(trajectory, outcome)
        assert len(lessons) >= 1

    def test_extract_respects_max_lessons(self) -> None:
        """Max lessons limit is enforced."""
        gen = LessonGenerator(max_lessons=1)
        outcome = Result(
            task_id="t1",
            success=False,
            error="TimeoutError: server did not respond",
        )
        # Trajectory with many reflective messages
        trajectory = [
            Message(
                role="assistant",
                content="I should try a different approach next time.",
            ),
            Message(
                role="assistant",
                content="Next time I will use a better pattern instead.",
            ),
            Message(
                role="assistant",
                content="Better to use exponential backoff.",
            ),
        ]

        lessons = gen.extract(trajectory, outcome)
        # 1 from error + 1 from content (capped by max_lessons=1, but error comes first)
        assert len(lessons) <= MAX_LESSONS_PER_TRAJECTORY

    def test_extract_empty_trajectory(self) -> None:
        """Empty trajectory still produces fallback lesson."""
        gen = LessonGenerator()
        outcome = Result(task_id="t1", success=True, data="ok")
        lessons = gen.extract([], outcome)
        assert len(lessons) >= 1

    def test_extract_from_tool_call_failure(self) -> None:
        """Tool calls on failure produce caution lessons."""
        gen = LessonGenerator()
        outcome = Result(task_id="t1", success=False, error="Something broke")
        trajectory = [
            Message(
                role="assistant",
                content="Calling the search tool.",
                tool_calls=(
                    ToolCall(id="c1", name="search_tool", arguments={"q": "test"}),
                ),
            )
        ]

        lessons = gen.extract(trajectory, outcome)
        tool_lessons = [l for l in lessons if "search_tool" in l.principle]
        assert len(tool_lessons) >= 1

    def test_extract_from_tool_call_success_no_extraction(self) -> None:
        """Tool calls on success do not produce caution lessons."""
        gen = LessonGenerator()
        outcome = Result(task_id="t1", success=True, data="ok")
        trajectory = [
            Message(
                role="assistant",
                content="Calling the search tool.",
                tool_calls=(
                    ToolCall(id="c1", name="search_tool", arguments={"q": "test"}),
                ),
            )
        ]

        lessons = gen.extract(trajectory, outcome)
        # No caution lesson for successful tool use
        tool_lessons = [l for l in lessons if "search_tool" in l.principle]
        assert len(tool_lessons) == 0

    def test_extract_from_content_with_reflection_signals(self) -> None:
        """Assistant content with reflection signals produces lessons."""
        gen = LessonGenerator()
        outcome = Result(task_id="t1", success=True, data="ok")
        trajectory = [
            Message(
                role="assistant",
                content="I should use pagination for large result sets. "
                "Better to limit queries.",
            )
        ]

        lessons = gen.extract(trajectory, outcome)
        content_lessons = [l for l in lessons if len(l.trigger_conditions) > 0]
        assert len(content_lessons) >= 1

    def test_extract_from_content_no_signals(self) -> None:
        """Content without reflection signals does not produce content lessons."""
        gen = LessonGenerator()
        outcome = Result(task_id="t1", success=True, data="ok")
        trajectory = [
            Message(role="assistant", content="The sky is blue and the grass is green.")
        ]

        lessons = gen.extract(trajectory, outcome)
        # Should only contain the fallback generic lesson
        assert len(lessons) == 1
        assert "review approach" in lessons[0].principle.lower()

    def test_extract_from_error_timeout(self) -> None:
        """Timeout errors produce timeout trigger condition."""
        gen = LessonGenerator()
        lesson = gen._extract_from_error(
            error="TimeoutError: request timed out after 30s",
            trajectory=[],
            task_id="t1",
        )
        assert lesson is not None
        assert "timeout" in lesson.trigger_conditions

    def test_extract_from_error_rate_limit(self) -> None:
        """Rate limit errors produce rate_limit trigger."""
        gen = LessonGenerator()
        # The check is for "rate limit" (space-separated) in the lowercased error
        lesson = gen._extract_from_error(
            error="You hit a rate limit. Please slow down.",
            trajectory=[],
            task_id="t1",
        )
        assert lesson is not None
        assert "rate_limit" in lesson.trigger_conditions

    def test_extract_from_error_validation(self) -> None:
        """Validation errors produce validation trigger."""
        gen = LessonGenerator()
        lesson = gen._extract_from_error(
            error="ValidationError: invalid input",
            trajectory=[],
            task_id="t1",
        )
        assert lesson is not None
        assert "validation" in lesson.trigger_conditions

    def test_extract_from_error_not_found(self) -> None:
        """Not found errors produce not_found trigger."""
        gen = LessonGenerator()
        lesson = gen._extract_from_error(
            error="NotFoundError: resource not found",
            trajectory=[],
            task_id="t1",
        )
        assert lesson is not None
        assert "not_found" in lesson.trigger_conditions

    def test_extract_from_error_permission(self) -> None:
        """Permission errors produce permission_denied trigger."""
        gen = LessonGenerator()
        lesson = gen._extract_from_error(
            error="PermissionDeniedError: access denied",
            trajectory=[],
            task_id="t1",
        )
        assert lesson is not None
        assert "permission_denied" in lesson.trigger_conditions

    def test_extract_from_error_no_match(self) -> None:
        """Errors without known keywords return None."""
        gen = LessonGenerator()
        lesson = gen._extract_from_error(
            error="UnknownError: something unexpected happened",
            trajectory=[],
            task_id="t1",
        )
        assert lesson is None

    def test_extract_from_content_full_sentence(self) -> None:
        """Content extraction finds the sentence with the reflection signal."""
        gen = LessonGenerator()
        lesson = gen._extract_from_content(
            content="I made a mistake. Next time I will validate first. This is important.",
            task_id="t1",
            outcome="failure",
        )
        assert lesson is not None
        assert "Next time I will validate first" in lesson.principle

    def test_extract_from_content_no_sentence_delimiter(self) -> None:
        """Content without periods still extracts first 200 chars."""
        gen = LessonGenerator()
        long_text = "next time do better " * 50
        lesson = gen._extract_from_content(
            content=long_text,
            task_id="t1",
            outcome="failure",
        )
        assert lesson is not None
        assert len(lesson.principle) < len(long_text) + 100  # bounded

    def test_extract_with_mixed_signals(self) -> None:
        """Multiple error and signal types produce multiple lessons."""
        gen = LessonGenerator()
        outcome = Result(
            task_id="t1",
            success=False,
            error="TimeoutError: API call timed out",
        )
        trajectory = [
            Message(role="assistant", content=""),
            Message(
                role="assistant",
                content="I should retry with backoff instead of immediate retry.",
                tool_calls=(
                    ToolCall(id="c1", name="api_call", arguments={"url": "https://example.com"}),
                ),
            ),
        ]

        lessons = gen.extract(trajectory, outcome)
        assert len(lessons) >= 2

    def test_fallback_lesson_has_trigger_conditions(self) -> None:
        """Fallback lesson uses outcome as trigger condition."""
        gen = LessonGenerator()
        outcome = Result(task_id="t1", success=True, data="ok")
        lessons = gen.extract([], outcome)
        assert len(lessons) == 1
        assert "success" in lessons[0].trigger_conditions

    def test_extract_with_metadata_in_outcome(self) -> None:
        """Task type from metadata is passed to fallback lesson."""
        gen = LessonGenerator()
        outcome = Result(
            task_id="t1",
            success=False,
            error="error",
            metadata={"task_type": "coding"},
        )
        lessons = gen.extract([], outcome)
        assert lessons[0].task_type == "coding"


# ======================================================================
# ReflectionMemory tests
# ======================================================================


class TestReflectionMemory:
    """Tests for ReflectionMemory — storage and retrieval of lessons."""

    def test_store_and_retrieve(self) -> None:
        mem = ReflectionMemory()
        lesson = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="Avoid timeout errors",
            trigger_conditions=("timeout",),
        )
        mem.store(lesson)
        assert mem.lesson_count == 1
        results = mem.retrieve("There was a timeout error", max_results=5)
        assert len(results) == 1
        assert results[0].lesson_id == "l1"

    def test_store_deduplication(self) -> None:
        mem = ReflectionMemory()
        lesson_a = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="Avoid timeout errors",
            trigger_conditions=("timeout",),
        )
        lesson_b = Lesson(
            lesson_id="l2",
            source_task_id="t2",
            outcome="failure",
            principle="Avoid timeout errors",
            trigger_conditions=("timeout",),
        )
        mem.store(lesson_a)
        mem.store(lesson_b)
        # Same content_hash -> only 1 stored (first-write-wins)
        assert mem.lesson_count == 1

    def test_store_batch_returns_count(self) -> None:
        mem = ReflectionMemory()
        lessons = [
            Lesson(
                lesson_id=f"l{i}",
                source_task_id="t1",
                outcome="failure",
                principle=f"Principle {i}",
                trigger_conditions=(f"cond{i}",),
            )
            for i in range(3)
        ]
        stored = mem.store_batch(lessons)
        assert stored == 3
        assert mem.lesson_count == 3

    def test_store_batch_all_duplicates(self) -> None:
        mem = ReflectionMemory()
        lesson = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="Avoid timeout errors",
            trigger_conditions=("timeout",),
        )
        mem.store(lesson)
        stored = mem.store_batch([lesson])
        assert stored == 0

    def test_retrieve_no_match(self) -> None:
        mem = ReflectionMemory()
        lesson = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="Avoid timeout errors",
            trigger_conditions=("timeout",),
        )
        mem.store(lesson)
        results = mem.retrieve("database connection issues", max_results=5)
        assert len(results) == 0

    def test_retrieve_respects_max_results(self) -> None:
        mem = ReflectionMemory()
        for i in range(10):
            mem.store(
                Lesson(
                    lesson_id=f"l{i}",
                    source_task_id="t1",
                    outcome="failure",
                    principle=f"Principle {i}",
                    trigger_conditions=("common",),
                )
            )
        results = mem.retrieve("common trigger", max_results=3)
        assert len(results) == 3

    def test_retrieve_sorted_by_created_at_desc(self) -> None:
        mem = ReflectionMemory()
        lessons = []
        for i in range(5):
            l = Lesson(
                lesson_id=f"l{i}",
                source_task_id="t1",
                outcome="failure",
                principle=f"Unique principle {i}",
                trigger_conditions=("common",),
                created_at=float(i),
            )
            lessons.append(l)
            mem.store(l)

        results = mem.retrieve("common", max_results=5)
        # Most recent (highest created_at) first
        timestamps = [l.created_at for l in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_retrieve_by_task_type(self) -> None:
        mem = ReflectionMemory()
        mem.store(
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="failure",
                principle="Coding lesson",
                task_type="coding",
                trigger_conditions=("code",),
            )
        )
        mem.store(
            Lesson(
                lesson_id="l2",
                source_task_id="t1",
                outcome="success",
                principle="Research lesson",
                task_type="research",
                trigger_conditions=("research",),
            )
        )
        results = mem.retrieve_by_task_type("coding")
        assert len(results) == 1
        assert results[0].lesson_id == "l1"

    def test_retrieve_by_task_type_no_match(self) -> None:
        mem = ReflectionMemory()
        results = mem.retrieve_by_task_type("nonexistent")
        assert results == []

    def test_retrieve_by_task_type_empty_memory(self) -> None:
        mem = ReflectionMemory()
        assert mem.retrieve_by_task_type("anything") == []

    def test_get_statistics(self) -> None:
        mem = ReflectionMemory()
        mem.store(
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="success",
                principle="Do X",
                task_type="code",
                trigger_conditions=("x",),
            )
        )
        mem.store(
            Lesson(
                lesson_id="l2",
                source_task_id="t1",
                outcome="failure",
                principle="Avoid Y",
                task_type="code",
                trigger_conditions=("y",),
            )
        )
        stats = mem.get_statistics()
        assert stats["total_lessons"] == 2
        assert stats["success_lessons"] == 1
        assert stats["failure_lessons"] == 1
        assert stats["task_types"] == {"code"}

    def test_get_statistics_empty(self) -> None:
        mem = ReflectionMemory()
        stats = mem.get_statistics()
        assert stats["total_lessons"] == 0
        assert stats["success_lessons"] == 0
        assert stats["failure_lessons"] == 0
        assert stats["task_types"] == set()

    def test_compute_relevance(self) -> None:
        mem = ReflectionMemory()
        lesson = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="p",
            trigger_conditions=("timeout", "retry"),
        )
        # Full match
        score = mem._compute_relevance(lesson, "there was a timeout error with retry")
        assert score == 1.0

    def test_compute_relevance_partial(self) -> None:
        mem = ReflectionMemory()
        lesson = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="p",
            trigger_conditions=("timeout", "retry", "validation"),
        )
        score = mem._compute_relevance(lesson, "there was a timeout error")
        assert 0.0 < score < 1.0

    def test_compute_relevance_no_match(self) -> None:
        mem = ReflectionMemory()
        lesson = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="p",
            trigger_conditions=("timeout",),
        )
        score = mem._compute_relevance(lesson, "database connection error")
        assert score == 0.0

    def test_compute_relevance_empty_conditions(self) -> None:
        mem = ReflectionMemory()
        lesson = Lesson(
            lesson_id="l1",
            source_task_id="t1",
            outcome="failure",
            principle="p",
            trigger_conditions=(),
        )
        score = mem._compute_relevance(lesson, "anything at all")
        assert score == 0.0

    def test_retrieve_with_threshold(self) -> None:
        """Only lessons above SIMILARITY_TRIGGER_THRESHOLD are returned."""
        mem = ReflectionMemory()
        mem.store(
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="failure",
                principle="Timeout lesson",
                trigger_conditions=("timeout", "retry"),  # 2 conditions
            )
        )
        # With 1 of 2 matching: 0.5 >= 0.5 -> included
        results = mem.retrieve("there was a timeout error", max_results=5)
        assert len(results) == 1


# ======================================================================
# StrategyInjector tests
# ======================================================================


class TestStrategyInjector:
    """Tests for StrategyInjector — injecting lessons into messages."""

    def test_inject_with_system_message(self) -> None:
        injector = StrategyInjector()
        lessons = [
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="failure",
                principle="Validate inputs",
                trigger_conditions=("validation",),
            )
        ]
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Do something."),
        ]

        result = injector.inject(lessons, messages)
        assert len(result) == 2
        assert "[FAILURE]" in result[0].content
        assert "Validate inputs" in result[0].content
        assert result[1].content == "Do something."

    def test_inject_without_system_message(self) -> None:
        injector = StrategyInjector()
        lessons = [
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="success",
                principle="Use pagination",
            )
        ]
        messages = [
            Message(role="user", content="Fetch data."),
        ]

        result = injector.inject(lessons, messages)
        # System message was prepended
        assert len(result) == 2
        assert result[0].role == "system"
        assert "[SUCCESS]" in result[0].content
        assert "Use pagination" in result[0].content
        assert result[1].role == "user"

    def test_inject_empty_lessons(self) -> None:
        injector = StrategyInjector()
        messages = [Message(role="system", content="System prompt.")]
        result = injector.inject([], messages)
        assert len(result) == 1
        assert result[0].content == "System prompt."

    def test_inject_multiple_lessons(self) -> None:
        injector = StrategyInjector()
        lessons = [
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="failure",
                principle="Avoid timeouts",
            ),
            Lesson(
                lesson_id="l2",
                source_task_id="t1",
                outcome="success",
                principle="Use pagination",
            ),
        ]
        messages = [Message(role="system", content="System.")]

        result = injector.inject(lessons, messages)
        assert "Avoid timeouts" in result[0].content
        assert "Use pagination" in result[0].content
        assert "1. [FAILURE]" in result[0].content
        assert "2. [SUCCESS]" in result[0].content

    def test_inject_does_not_mutate_original(self) -> None:
        injector = StrategyInjector()
        lessons = [
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="failure",
                principle="Avoid timeouts",
            )
        ]
        original = [Message(role="system", content="System.")]
        result = injector.inject(lessons, original)

        assert original[0].content == "System."
        assert result[0].content != original[0].content


# ======================================================================
# ReflexionLoop tests
# ======================================================================


class TestReflexionLoop:
    """Tests for the ReflexionLoop class."""

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        exe = MagicMock(spec=AgentLoopExecutor)
        exe.execute = AsyncMock()
        return exe

    @pytest.fixture
    def mock_provider(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_tools(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_memory(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_hooks(self) -> MagicMock:
        return MagicMock()

    def test_loop_with_mock_executor(self, mock_executor: MagicMock) -> None:
        """ReflexionLoop stores the provided executor."""
        loop = ReflexionLoop(executor=mock_executor)
        assert loop.executor is mock_executor

    def test_loop_with_executor(self, mock_executor: MagicMock) -> None:
        loop = ReflexionLoop(executor=mock_executor)
        assert loop.executor is mock_executor

    def test_lesson_count_empty(self, mock_executor: MagicMock) -> None:
        loop = ReflexionLoop(executor=mock_executor)
        assert loop.lesson_count == 0

    def test_lesson_count_after_storage(self, mock_executor: MagicMock) -> None:
        loop = ReflexionLoop(executor=mock_executor)
        loop.reflection_memory.store(
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="failure",
                principle="Test",
                trigger_conditions=("test",),
            )
        )
        assert loop.lesson_count == 1

    def test_lesson_count_delegates_to_memory(self, mock_executor: MagicMock) -> None:
        loop = ReflexionLoop(executor=mock_executor)
        loop.reflection_memory.store_batch(
            [
                Lesson(
                    lesson_id=f"l{i}",
                    source_task_id="t1",
                    outcome="success",
                    principle=f"P{i}",
                    trigger_conditions=(f"c{i}",),
                )
                for i in range(3)
            ]
        )
        assert loop.lesson_count == 3

    def test_get_statistics(self, mock_executor: MagicMock) -> None:
        loop = ReflexionLoop(executor=mock_executor)
        loop.reflection_memory.store(
            Lesson(
                lesson_id="l1",
                source_task_id="t1",
                outcome="failure",
                principle="Test",
                trigger_conditions=("test",),
            )
        )
        stats = loop.get_statistics()
        assert stats["max_iterations"] == DEFAULT_MAX_ITERATIONS
        assert stats["current_trajectory_length"] == 0
        assert stats["reflection_memory"]["total_lessons"] == 1

    async def test_run_success_first_attempt(
        self, mock_executor: MagicMock
    ) -> None:
        """Successful first attempt returns immediately with lessons stored."""
        mock_executor.execute.return_value = Result(
            task_id="t1",
            success=True,
            data="Task completed successfully",
            metadata={"task_type": "test"},
        )

        loop = ReflexionLoop(executor=mock_executor)

        task = MagicMock()
        task.description = "Test task"
        task.task_id = "t1"

        result = await loop.run(
            task=task,
            agent=MagicMock(),
            provider=MagicMock(),
            tools=MagicMock(),
            memory=MagicMock(),
            hooks=MagicMock(),
        )

        assert result.success is True
        assert result.data == "Task completed successfully"
        # One lesson should have been stored
        assert loop.lesson_count >= 1
        mock_executor.execute.assert_called_once()

    async def test_run_failure_then_success(
        self, mock_executor: MagicMock
    ) -> None:
        """Failed first attempt is retried with injected lessons."""
        mock_executor.execute.side_effect = [
            Result(
                task_id="t1",
                success=False,
                error="TimeoutError: API call failed",
                metadata={"task_type": "test"},
            ),
            Result(
                task_id="t1",
                success=True,
                data="Completed on retry",
                metadata={"task_type": "test"},
            ),
        ]

        loop = ReflexionLoop(executor=mock_executor)
        task = MagicMock()
        task.description = "Test task"
        task.task_id = "t1"

        result = await loop.run(
            task=task,
            agent=MagicMock(),
            provider=MagicMock(),
            tools=MagicMock(),
            memory=MagicMock(),
            hooks=MagicMock(),
        )

        assert result.success is True
        assert result.data == "Completed on retry"
        assert mock_executor.execute.call_count == 2
        # Lessons from first failure should be stored
        assert loop.lesson_count >= 1

    async def test_run_all_failures(
        self, mock_executor: MagicMock
    ) -> None:
        """All attempts fail, returns last failure result."""
        mock_executor.execute.return_value = Result(
            task_id="t1",
            success=False,
            error="Persistent failure",
            metadata={"task_type": "test"},
        )

        loop = ReflexionLoop(executor=mock_executor)
        task = MagicMock()
        task.description = "Test task"
        task.task_id = "t1"

        result = await loop.run(
            task=task,
            agent=MagicMock(),
            provider=MagicMock(),
            tools=MagicMock(),
            memory=MagicMock(),
            hooks=MagicMock(),
        )

        assert result.success is False
        assert result.error == "Persistent failure"
        assert mock_executor.execute.call_count == DEFAULT_MAX_ITERATIONS

    async def test_run_custom_max_iterations(
        self, mock_executor: MagicMock
    ) -> None:
        """Custom max_iterations is respected."""
        mock_executor.execute.return_value = Result(
            task_id="t1",
            success=False,
            error="Failed",
            metadata={"task_type": "test"},
        )

        loop = ReflexionLoop(executor=mock_executor, max_iterations=2)
        task = MagicMock()
        task.description = "Test"
        task.task_id = "t1"

        result = await loop.run(
            task=task,
            agent=MagicMock(),
            provider=MagicMock(),
            tools=MagicMock(),
            memory=MagicMock(),
            hooks=MagicMock(),
        )

        assert mock_executor.execute.call_count == 2

    def test_build_context_summary(self, mock_executor: MagicMock) -> None:
        """Context summary includes task description."""
        loop = ReflexionLoop(executor=mock_executor)
        task = MagicMock()
        task.description = "Write unit tests"
        summary = loop._build_context_summary(task, None)
        assert "Write unit tests" in summary

    def test_build_context_summary_with_error(self, mock_executor: MagicMock) -> None:
        """Context summary includes last error."""
        loop = ReflexionLoop(executor=mock_executor)
        task = MagicMock()
        task.description = "Call API"
        last = Result(
            task_id="t1",
            success=False,
            error="TimeoutError: API timed out",
        )
        summary = loop._build_context_summary(task, last)
        assert "Call API" in summary
        assert "TimeoutError" in summary

    def test_build_context_summary_with_success_result(self, mock_executor: MagicMock) -> None:
        """Context summary works with successful last result."""
        loop = ReflexionLoop(executor=mock_executor)
        task = MagicMock()
        task.description = "Do work"
        last = Result(task_id="t1", success=True, data="ok")
        summary = loop._build_context_summary(task, last)
        assert "Do work" in summary
        # No error appended for success

    def test_build_context_summary_task_without_description(self, mock_executor: MagicMock) -> None:
        """Context summary handles task without description attribute."""
        loop = ReflexionLoop(executor=mock_executor)
        task = "raw string task"
        summary = loop._build_context_summary(task, None)
        assert "raw string task" in summary

    async def test_trajectory_grows_on_iterations(
        self, mock_executor: MagicMock
    ) -> None:
        """Trajectory length increases with each iteration."""
        mock_executor.execute.return_value = Result(
            task_id="t1",
            success=False,
            error="Failed",
            metadata={"task_type": "test"},
        )

        loop = ReflexionLoop(executor=mock_executor, max_iterations=3)
        task = MagicMock()
        task.description = "Test"
        task.task_id = "t1"

        await loop.run(
            task=task,
            agent=MagicMock(),
            provider=MagicMock(),
            tools=MagicMock(),
            memory=MagicMock(),
            hooks=MagicMock(),
        )

        # Should have trajectory entries for each iteration
        assert len(loop._trajectory) == 3

    def test_reflexion_memory_slot_constant(self) -> None:
        """REFLECTION_MEMORY_SLOT is a known string."""
        assert REFLECTION_MEMORY_SLOT == "reflexion_lessons"

    async def test_trajectory_message_format(self, mock_executor: MagicMock) -> None:
        """Trajectory messages contain iteration details."""
        mock_executor.execute.return_value = Result(
            task_id="t1",
            success=True,
            data="ok",
            metadata={"task_type": "test"},
        )

        loop = ReflexionLoop(executor=mock_executor)
        task = MagicMock()
        task.description = "Test"
        task.task_id = "t1"

        await loop.run(
            task=task,
            agent=MagicMock(),
            provider=MagicMock(),
            tools=MagicMock(),
            memory=MagicMock(),
            hooks=MagicMock(),
        )

        assert len(loop._trajectory) == 1
        msg = loop._trajectory[0]
        assert "success=True" in msg.content
        assert msg.name == "reflexion_loop"
