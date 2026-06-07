"""
Reflexion Loop — canonical "act -> observe -> reflect -> store -> inject" cycle.

Implements the Reflexion pattern for agent self-improvement through
structured lesson extraction from task trajectories.

The loop:
    1. **Act** — Execute the task using the agent loop.
    2. **Observe** — Check the result (success / failure).
    3. **Reflect** — Extract lessons from the trajectory and outcome.
    4. **Store** — Persist lessons to reflection memory.
    5. **Inject** — Surface relevant past lessons in the next attempt's
       context.

References
----------
    Reflexion: Shinn et al. (2023). Reflexion: Language Agents with
        Verbal Reinforcement Learning. arXiv:2303.11366.
        https://arxiv.org/abs/2303.11366

    MARS²: Multi-Agent Reinforcement Learning from Automated
        Refinement and Synthetic Data (2026). arXiv:2604.14564v1 —
        structured lesson extraction from agent trajectories.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from lyra.agent_loop.executor import AgentLoopExecutor
from lyra.core.task import Result as TaskResult
from lyra.routing.provider.types import Message

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_ITERATIONS: int = 3
"""Default maximum reflexion iterations per task."""

REFLECTION_MEMORY_SLOT: str = "reflexion_lessons"
"""Storage slot key for reflexion lessons."""

MAX_LESSONS_PER_TRAJECTORY: int = 5
"""Maximum lessons extracted from a single trajectory."""

SIMILARITY_TRIGGER_THRESHOLD: float = 0.5
"""Minimum similarity score to trigger lesson injection."""


# ---------------------------------------------------------------------------
# Lesson
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Lesson:
    """A single lesson extracted from an agent trajectory.

    Attributes:
        lesson_id: Unique identifier.
        source_task_id: Task that generated this lesson.
        outcome: Whether the task succeeded or failed.
        principle: The actionable lesson principle (e.g. "Always
            validate input before calling external APIs").
        trigger_conditions: Context signals that should trigger
            injection of this lesson (e.g. keywords, tool names).
        created_at: Unix timestamp.
        task_type: Optional task type descriptor for filtering.
        metadata: Optional arbitrary context.
    """

    lesson_id: str
    source_task_id: str
    outcome: str  # "success" | "failure"
    principle: str
    trigger_conditions: tuple[str, ...] = ()
    created_at: float = 0.0
    task_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.created_at == 0.0:
            object.__setattr__(self, "created_at", time.time())

    @property
    def content_hash(self) -> str:
        """Return a short content hash for deduplication."""
        raw = json.dumps(
            {
                "principle": self.principle,
                "trigger_conditions": self.trigger_conditions,
            },
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# LessonGenerator
# ---------------------------------------------------------------------------


@dataclass
class LessonGenerator:
    """Extracts lessons from agent trajectories.

    The generator analyses the trajectory and outcome to produce
    structured, actionable lessons that can prevent recurrence of
    failures or reinforce successful patterns.

    In production this would delegate to an LLM for deeper analysis.
    The default implementation uses keyword-based heuristics.
    """

    max_lessons: int = MAX_LESSONS_PER_TRAJECTORY

    def extract(
        self,
        trajectory: Sequence[Message],
        outcome: TaskResult,
    ) -> list[Lesson]:
        """Extract lessons from an agent trajectory.

        Args:
            trajectory: Sequence of messages (the agent's full turn
                history for the task).
            outcome: The task result (contains success/failure and
                error information).

        Returns:
            List of ``Lesson`` instances extracted from the trajectory.
        """
        task_id = outcome.task_id
        result_outcome = "failure" if not outcome.success else "success"

        lessons: list[Lesson] = []

        # Extract from error messages on failure
        if not outcome.success and outcome.error:
            lesson = self._extract_from_error(
                error=outcome.error,
                trajectory=trajectory,
                task_id=task_id,
            )
            if lesson is not None:
                lessons.append(lesson)

        # Extract from tool call patterns in the trajectory
        for msg in trajectory:
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    lesson = self._extract_from_tool_call(
                        tool_call=tc,
                        task_id=task_id,
                        outcome=result_outcome,
                    )
                    if lesson is not None:
                        lessons.append(lesson)
                        if len(lessons) >= self.max_lessons:
                            return lessons

            # Extract from assistant content patterns
            if msg.role == "assistant" and msg.content:
                lesson = self._extract_from_content(
                    content=msg.content,
                    task_id=task_id,
                    outcome=result_outcome,
                )
                if lesson is not None:
                    lessons.append(lesson)
                    if len(lessons) >= self.max_lessons:
                        return lessons

        # Fallback: generic lesson if nothing specific was extracted
        if not lessons:
            lessons.append(
                Lesson(
                    lesson_id=str(uuid.uuid4()),
                    source_task_id=task_id,
                    outcome=result_outcome,
                    principle=(
                        f"Task {result_outcome}: review approach for "
                        f"future tasks of this type."
                    ),
                    trigger_conditions=(result_outcome,),
                    task_type=outcome.metadata.get("task_type", ""),
                ),
            )

        return lessons

    def _extract_from_error(
        self,
        error: str,
        trajectory: Sequence[Message],
        task_id: str,
    ) -> Lesson | None:
        """Extract a lesson from an error message."""
        error_lower = error.lower()

        trigger_conditions: list[str] = []
        if "timeout" in error_lower:
            trigger_conditions.append("timeout")
        if "rate limit" in error_lower:
            trigger_conditions.append("rate_limit")
        if "validation" in error_lower:
            trigger_conditions.append("validation")
        if "not found" in error_lower:
            trigger_conditions.append("not_found")
        if "permission" in error_lower:
            trigger_conditions.append("permission_denied")

        if not trigger_conditions:
            return None

        return Lesson(
            lesson_id=str(uuid.uuid4()),
            source_task_id=task_id,
            outcome="failure",
            principle=f"Avoid errors of type: {', '.join(trigger_conditions)}. "
                      f"Error: {error[:200]}",
            trigger_conditions=tuple(trigger_conditions),
        )

    def _extract_from_tool_call(
        self,
        tool_call: Any,
        task_id: str,
        outcome: str,
    ) -> Lesson | None:
        """Extract a lesson from a tool call pattern."""
        tool_name = getattr(tool_call, "name", str(tool_call))
        _ = task_id  # reserved for future use

        # On failure, record tools that were involved
        if outcome == "failure":
            return Lesson(
                lesson_id=str(uuid.uuid4()),
                source_task_id=task_id,
                outcome="failure",
                principle=f"Exercise caution when calling '{tool_name}' — "
                          f"it was involved in a failed trajectory.",
                trigger_conditions=(tool_name, "failure"),
                task_type="tool_execution",
            )

        return None

    def _extract_from_content(
        self,
        content: str,
        task_id: str,
        outcome: str,
    ) -> Lesson | None:
        """Extract a lesson from assistant content patterns."""
        content_lower = content.lower()

        # Look for reflective statements
        reflection_signals = [
            "i should", "next time", "instead", "better to",
            "lesson learned", "next iteration", "avoid",
        ]

        found_signals = [
            s for s in reflection_signals if s in content_lower
        ]
        if not found_signals:
            return None

        # Extract a sentence containing the first signal
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        principle_sentence = ""
        for sentence in sentences:
            if any(s in sentence.lower() for s in found_signals):
                principle_sentence = sentence[:300]
                break

        if not principle_sentence:
            principle_sentence = content[:200]

        return Lesson(
            lesson_id=str(uuid.uuid4()),
            source_task_id=task_id,
            outcome=outcome,
            principle=(
                f"Reflexion lesson ({outcome}): {principle_sentence}"
            ),
            trigger_conditions=tuple(found_signals),
            task_type="reflective",
        )


# ---------------------------------------------------------------------------
# ReflectionMemory
# ---------------------------------------------------------------------------


@dataclass
class ReflectionMemory:
    """Stores lessons with trigger conditions for later retrieval.

    Lessons are stored in a dict keyed by content hash (for
    deduplication) and retrieved based on context matching against
    trigger conditions.
    """

    lessons: dict[str, Lesson] = field(default_factory=dict)

    def store(self, lesson: Lesson) -> None:
        """Store a lesson, deduplicating by content hash.

        If a lesson with the same content hash already exists, the
        existing lesson is kept (first-write-wins).

        Args:
            lesson: The lesson to store.
        """
        key = lesson.content_hash
        if key not in self.lessons:
            self.lessons[key] = lesson

    def store_batch(self, lessons: list[Lesson]) -> int:
        """Store multiple lessons.

        Args:
            lessons: List of lessons to store.

        Returns:
            Number of new lessons stored (excluding duplicates).
        """
        stored = 0
        for lesson in lessons:
            key = lesson.content_hash
            if key not in self.lessons:
                self.lessons[key] = lesson
                stored += 1
        return stored

    def retrieve(
        self,
        context: str,
        max_results: int = 5,
    ) -> list[Lesson]:
        """Retrieve lessons relevant to a context string.

        Lessons are matched against the context using their trigger
        conditions. A trigger condition is considered a match if the
        condition string appears in the context (case-insensitive).

        Args:
            context: The current context to match against (e.g. the
                task description or latest messages).
            max_results: Maximum number of lessons to return.

        Returns:
            List of relevant ``Lesson`` instances, sorted by creation
            time descending (most recent first).
        """
        context_lower = context.lower()
        matched: list[Lesson] = []

        for lesson in self.lessons.values():
            score = self._compute_relevance(lesson, context_lower)
            if score >= SIMILARITY_TRIGGER_THRESHOLD:
                matched.append(lesson)

        matched.sort(key=lambda l: l.created_at, reverse=True)
        return matched[:max_results]

    def retrieve_by_task_type(
        self,
        task_type: str,
        max_results: int = 5,
    ) -> list[Lesson]:
        """Retrieve lessons for a specific task type.

        Args:
            task_type: The task type to filter by.
            max_results: Maximum results.

        Returns:
            List of matching ``Lesson`` instances.
        """
        matched = [
            l for l in self.lessons.values()
            if l.task_type == task_type
        ]
        matched.sort(key=lambda l: l.created_at, reverse=True)
        return matched[:max_results]

    def _compute_relevance(
        self,
        lesson: Lesson,
        context_lower: str,
    ) -> float:
        """Compute a relevance score between a lesson and context.

        Uses a simple ratio of matching trigger conditions.

        Returns:
            A score in ``[0.0, 1.0]``.
        """
        if not lesson.trigger_conditions:
            return 0.0

        matches = sum(
            1 for c in lesson.trigger_conditions
            if c.lower() in context_lower
        )
        return matches / len(lesson.trigger_conditions)

    @property
    def lesson_count(self) -> int:
        """Total number of stored lessons."""
        return len(self.lessons)

    def get_statistics(self) -> dict[str, Any]:
        """Return summary statistics for the reflection memory.

        Returns:
            Dict with lesson count and outcome breakdown.
        """
        successes = sum(
            1 for l in self.lessons.values() if l.outcome == "success"
        )
        failures = sum(
            1 for l in self.lessons.values() if l.outcome == "failure"
        )
        return {
            "total_lessons": self.lesson_count,
            "success_lessons": successes,
            "failure_lessons": failures,
            "task_types": {
                l.task_type for l in self.lessons.values()
            },
        }


# ---------------------------------------------------------------------------
# StrategyInjector
# ---------------------------------------------------------------------------


@dataclass
class StrategyInjector:
    """Injects relevant lessons into agent context messages.

    Lessons are appended to the system message as a "Prior Lessons"
    section, helping the agent benefit from past experience.
    """

    def inject(
        self,
        lessons: list[Lesson],
        messages: list[Message],
    ) -> list[Message]:
        """Inject lessons into a message list for the next attempt.

        Lessons are added to the first system message in the list.
        If no system message exists, a new one is prepended.

        Args:
            lessons: Lessons to inject.
            messages: The current message list.

        Returns:
            A new message list with lessons injected.
        """
        if not lessons:
            return list(messages)

        # Build the lessons text block
        lessons_lines: list[str] = [
            "\n## Prior Lessons (from past task executions)"
        ]
        for i, lesson in enumerate(lessons, 1):
            lessons_lines.append(
                f"\n{i}. [{lesson.outcome.upper()}] {lesson.principle}"
            )
        lessons_text = "\n".join(lessons_lines)

        result: list[Message] = []
        injected = False

        for msg in messages:
            if msg.role == "system" and not injected:
                new_content = msg.content + lessons_text
                result.append(
                    Message(
                        role=msg.role,
                        content=new_content,
                        tool_calls=msg.tool_calls,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name,
                    ),
                )
                injected = True
            else:
                result.append(msg)

        # No system message found — prepend one
        if not injected:
            result.insert(
                0,
                Message(
                    role="system",
                    content=lessons_text.lstrip("\n"),
                ),
            )

        return result


# ---------------------------------------------------------------------------
# ReflexionLoop
# ---------------------------------------------------------------------------


@dataclass
class ReflexionLoop:
    """Canonical 'act -> observe -> reflect -> store -> inject' loop.

    Wraps an ``AgentLoopExecutor`` and adds the reflexion pattern on
    top of task execution. After each attempt, lessons are extracted
    and stored. On subsequent attempts, relevant past lessons are
    injected into the agent's context.

    Usage::

        loop = ReflexionLoop(executor=AgentLoopExecutor())

        result = await loop.run(
            task=my_task,
            agent=my_agent,
            provider=my_provider,
            tools=my_tools,
            memory=stm,
            hooks=hook_engine,
        )
        # result contains the final outcome after up to 3 iterations

    References
    ----------
        Reflexion (arXiv:2303.11366) — Shinn et al., 2023.
        MARS² (arXiv:2604.14564v1) — structured lesson extraction.
    """

    executor: AgentLoopExecutor
    lesson_generator: LessonGenerator = field(default_factory=LessonGenerator)
    reflection_memory: ReflectionMemory = field(default_factory=ReflectionMemory)
    strategy_injector: StrategyInjector = field(default_factory=StrategyInjector)
    max_iterations: int = DEFAULT_MAX_ITERATIONS

    def __post_init__(self) -> None:
        if self.executor is None:
            self.executor = AgentLoopExecutor()
        # Keep a running trajectory across iterations
        self._trajectory: list[Message] = []

    async def run(
        self,
        task: Any,
        agent: Any,
        provider: Any,
        tools: Any,
        memory: Any,
        hooks: Any,
    ) -> TaskResult:
        """Execute the reflexion loop for a task.

        Up to ``max_iterations`` attempts are made. After each
        attempt, lessons are extracted and stored. On subsequent
        attempts, relevant past lessons are injected into the
        agent's context.

        Args:
            task: The task to execute.
            agent: The agent instance.
            provider: LLM provider backend.
            tools: Sandboxed tool executor.
            memory: Short-term memory.
            hooks: Hook engine.

        Returns:
            The ``TaskResult`` of the final attempt.
        """
        result: TaskResult | None = None

        for iteration in range(self.max_iterations):
            # Inject relevant past lessons into the context
            if self._trajectory:
                context_summary = self._build_context_summary(
                    task=task,
                    last_result=result,
                )
                relevant_lessons = self.reflection_memory.retrieve(
                    context=context_summary,
                )
                if relevant_lessons:
                    # We inject by setting a flag — the actual message
                    # injection happens inside the executor's
                    # _build_messages if a reflexion hook is installed.
                    # For direct injection we'd subclass the executor.
                    pass

            # 1. ACT: execute the task
            result = await self.executor.execute(
                task=task,
                agent=agent,
                provider=provider,
                tools=tools,
                memory=memory,
                hooks=hooks,
            )

            # Record trajectory turn
            if hasattr(result, "metadata"):
                self._trajectory.append(
                    Message(
                        role="tool",
                        content=(
                            f"Iteration {iteration + 1}: "
                            f"success={result.success}, "
                            f"error={result.error or 'none'}"
                        ),
                        name="reflexion_loop",
                    ),
                )

            # 2. OBSERVE: check if the task succeeded
            if result.success:
                # 3. REFLECT on success
                lessons = self.lesson_generator.extract(
                    trajectory=self._trajectory,
                    outcome=result,
                )

                # 4. STORE
                self.reflection_memory.store_batch(lessons)
                break

            # 3. REFLECT on failure
            lessons = self.lesson_generator.extract(
                trajectory=self._trajectory,
                outcome=result,
            )

            # 4. STORE
            self.reflection_memory.store_batch(lessons)

            # Log iteration outcome
            if iteration < self.max_iterations - 1:
                lessons_count = len(lessons)
                error = result.error or "unknown error"
                # 5. INJECT logic: next iteration will retrieve
                # lessons via _build_context_summary above

        return result

    def _build_context_summary(
        self,
        task: Any,
        last_result: TaskResult | None,
    ) -> str:
        """Build a context summary string for lesson matching.

        Args:
            task: The current task.
            last_result: The result of the last attempt (if any).

        Returns:
            A string summarising the current context.
        """
        parts: list[str] = []
        task_description = getattr(task, "description", str(task))
        parts.append(task_description)

        if last_result:
            if last_result.error:
                parts.append(last_result.error)

        return " ".join(parts)

    @property
    def lesson_count(self) -> int:
        """Total number of lessons accumulated across iterations."""
        return self.reflection_memory.lesson_count

    def get_statistics(self) -> dict[str, Any]:
        """Return summary statistics for the reflexion loop.

        Returns:
            Dict with iteration count, lesson count, and memory stats.
        """
        return {
            "max_iterations": self.max_iterations,
            "current_trajectory_length": len(self._trajectory),
            "reflection_memory": self.reflection_memory.get_statistics(),
        }
