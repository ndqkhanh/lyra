"""
Memory Consolidation - Move memories from short-term to long-term.

Provides:
  - MemoryConsolidator with configurable policies
  - ConsolidationPolicy: IMMEDIATE, THRESHOLD, PERIODIC, MANUAL, AUTO
  - AutoConsolidationScheduler: learns optimal consolidation frequency
  - BackgroundConsolidationDaemon: runs consolidation during idle periods
"""

from __future__ import annotations

import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra.memory.long_term_memory import LongTermMemory
from lyra.memory.memory_store import Memory, MemoryType
from lyra.memory.short_term_memory import ConversationTurn, ShortTermMemory


class ConsolidationPolicy(Enum):
    """When to trigger consolidation."""
    IMMEDIATE = "immediate"        # After every turn
    THRESHOLD = "threshold"        # When buffer reaches threshold
    PERIODIC = "periodic"          # At regular intervals
    MANUAL = "manual"              # Only when explicitly called
    AUTO = "auto"                  # Learned optimal frequency


@dataclass
class ConsolidationResult:
    """
    Result of a consolidation operation.

    Attributes:
        memories_created: Number of new long-term memories
        memories_merged: Number of memories merged
        patterns_extracted: Number of patterns found
        duration: Time taken (seconds)
    """
    memories_created: int
    memories_merged: int
    patterns_extracted: int
    duration: float


@dataclass
class ConsolidationStats:
    """Running statistics for auto-scheduling.

    Attributes:
        interval_history: Recent consolidation intervals (seconds).
        yield_history: Recent yields — items consolidated per second.
        avg_items_per_run: Average memories created per consolidation run.
        avg_duration: Average duration per run (seconds).
        optimal_interval: Estimated optimal interval between runs (seconds).
    """

    interval_history: list[float] = field(default_factory=list)
    yield_history: list[float] = field(default_factory=list)
    avg_items_per_run: float = 0.0
    avg_duration: float = 0.0
    optimal_interval: float = 300.0  # Default 5 minutes

    def to_dict(self) -> dict[str, Any]:
        return {
            "avg_items_per_run": round(self.avg_items_per_run, 2),
            "avg_duration": round(self.avg_duration, 2),
            "optimal_interval": round(self.optimal_interval, 1),
        }


# =============================================================================
# Auto-Consolidation Scheduler
# =============================================================================


class AutoConsolidationScheduler:
    """Learns the optimal consolidation interval from session patterns.

    The scheduler tracks the yield (items consolidated per second) of each
    consolidation run and adjusts the interval to maximise yield.
    """

    def __init__(
        self,
        min_interval: float = 30.0,
        max_interval: float = 900.0,
        adaptation_rate: float = 0.1,
        window_size: int = 10,
    ):
        """
        Args:
            min_interval: Minimum allowed interval (seconds).
            max_interval: Maximum allowed interval (seconds).
            adaptation_rate: How quickly the interval adjusts (0-1).
            window_size: Number of recent runs to consider.
        """
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.adaptation_rate = adaptation_rate
        self.window_size = window_size
        self._stats = ConsolidationStats()
        self._run_count = 0

    def record_run(self, result: ConsolidationResult):
        """Record a consolidation run and update the optimal interval.

        Args:
            result: The result of the consolidation operation.
        """
        duration = max(result.duration, 0.01)
        items = result.memories_created + result.memories_merged
        item_yield = items / duration

        # Update history
        self._stats.interval_history.append(duration)
        self._stats.yield_history.append(item_yield)
        if len(self._stats.interval_history) > self.window_size:
            self._stats.interval_history.pop(0)
            self._stats.yield_history.pop(0)

        self._run_count += 1

        # Update rolling averages
        n = len(self._stats.yield_history)
        self._stats.avg_items_per_run = (
            (self._stats.avg_items_per_run * (n - 1) + items) / max(n, 1)
        )
        self._stats.avg_duration = (
            (self._stats.avg_duration * (n - 1) + duration) / max(n, 1)
        )

        # Adaptive interval adjustment
        # If yield is increasing, we might benefit from more frequent runs
        if len(self._stats.yield_history) >= 2:
            yield_trend = (
                self._stats.yield_history[-1] - self._stats.yield_history[-2]
            )
            if yield_trend > 0 and items > 0:
                # Yield improving: reduce interval gradually
                self._stats.optimal_interval *= (1.0 - self.adaptation_rate * 0.5)
            elif yield_trend < 0 and items == 0:
                # Low yield: stretch interval
                self._stats.optimal_interval *= (1.0 + self.adaptation_rate * 0.3)

        # Clamp
        self._stats.optimal_interval = max(
            self.min_interval,
            min(self.max_interval, self._stats.optimal_interval),
        )

    def should_consolidate(self, time_since_last: float) -> bool:
        """Check if it is time to consolidate based on learned interval.

        Args:
            time_since_last: Seconds since the last consolidation.

        Returns:
            True if consolidation should occur.
        """
        return time_since_last >= self._stats.optimal_interval

    def get_stats(self) -> ConsolidationStats:
        """Return a copy of the current statistics."""
        import copy
        return copy.copy(self._stats)

    def reset(self):
        """Reset all learned statistics."""
        self._stats = ConsolidationStats()


# =============================================================================
# Background Consolidation Daemon
# =============================================================================


class BackgroundConsolidationDaemon:
    """Runs consolidation during idle periods in a background thread.

    The daemon periodically checks whether consolidation is needed and,
    if so, runs it in a daemon thread. It respects an optional minimum
    idle time before triggering, so it does not interfere with active
    agent work.

    Usage::

        daemon = BackgroundConsolidationDaemon(consolidator)
        daemon.start()
        # ... agent works ...
        daemon.stop()
    """

    def __init__(
        self,
        consolidator: MemoryConsolidator,
        check_interval: float = 10.0,
        idle_threshold: float = 5.0,
        auto_stop_if_idle: float = 300.0,
    ):
        """
        Args:
            consolidator: The MemoryConsolidator to run.
            check_interval: How often to check consolidation readiness (seconds).
            idle_threshold: Minimum time since last agent operation to
                consider the system idle (seconds).
            auto_stop_if_idle: If no successful consolidation happens for
                this many seconds, the daemon stops itself automatically.
        """
        self.consolidator = consolidator
        self.check_interval = check_interval
        self.idle_threshold = idle_threshold
        self.auto_stop_if_idle = auto_stop_if_idle

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_agent_activity = time.time()
        self._running = False

        # Tracking
        self._runs_completed: int = 0
        self._results: deque[ConsolidationResult] = deque(maxlen=20)
        self._last_run_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start the background consolidation daemon thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="bg-consolidation-daemon",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Signal the daemon to stop and wait for it."""
        if not self._running:
            return
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._running = False

    def report_activity(self):
        """Notify the daemon that the agent is active.

        Call this after any agent operation so the daemon can respect
        the idle threshold.
        """
        self._last_agent_activity = time.time()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def runs_completed(self) -> int:
        return self._runs_completed

    def get_recent_results(self) -> list[ConsolidationResult]:
        return list(self._results)

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _run_loop(self):
        """Main daemon loop — runs in a background thread."""
        while not self._stop_event.is_set():
            self._stop_event.wait(self.check_interval)
            if self._stop_event.is_set():
                break

            try:
                self._tick()
            except Exception:
                # Suppress exceptions in daemon thread
                pass

    def _tick(self):
        """Single daemon tick: check and consolidate if appropriate."""
        # Check whether the system is idle
        idle_time = time.time() - self._last_agent_activity
        if idle_time < self.idle_threshold:
            return  # Not idle yet

        # Check auto-stop
        if self._last_run_time > 0:
            time_since_last_run = time.time() - self._last_run_time
            if time_since_last_run > self.auto_stop_if_idle:
                # No recent successful runs — stop
                self.stop()
                return

        # Check if consolidation is needed
        if self.consolidator.should_consolidate():
            result = self.consolidator.consolidate()
            self._results.append(result)
            self._runs_completed += 1
            self._last_run_time = time.time()

    @property
    def stats(self) -> dict[str, Any]:
        """Return operational statistics."""
        return {
            "running": self._running,
            "runs_completed": self._runs_completed,
            "last_run_time": self._last_run_time,
            "idle_time": time.time() - self._last_agent_activity,
            "recent_results": [r.to_dict() if hasattr(r, 'to_dict') else {
                "memories_created": r.memories_created,
                "memories_merged": r.memories_merged,
                "duration": round(r.duration, 3),
            } for r in list(self._results)[-5:]],
        }


# =============================================================================
# Enhanced MemoryConsolidator
# =============================================================================


class MemoryConsolidator:
    """
    Consolidate memories from short-term to long-term.

    Responsibilities:
    - Move important short-term memories to long-term
    - Merge similar memories
    - Extract patterns and knowledge
    - Apply consolidation policies (including AUTO with learned schedule)
    """

    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        policy: ConsolidationPolicy = ConsolidationPolicy.THRESHOLD,
        importance_threshold: float = 0.5,
        auto_scheduler: AutoConsolidationScheduler | None = None,
    ):
        """
        Initialize memory consolidator.

        Args:
            short_term: Short-term memory
            long_term: Long-term memory
            policy: Consolidation policy
            importance_threshold: Minimum importance to consolidate
            auto_scheduler: Auto-scheduler for AUTO policy. Created
                with defaults if not provided and policy is AUTO.
        """
        self.short_term = short_term
        self.long_term = long_term
        self.policy = policy
        self.importance_threshold = importance_threshold
        self.last_consolidation = time.time()
        self.auto_scheduler = auto_scheduler or (
            AutoConsolidationScheduler() if policy == ConsolidationPolicy.AUTO
            else None
        )
        self._run_count = 0

    def should_consolidate(self) -> bool:
        """
        Check if consolidation should occur.

        Returns:
            True if should consolidate
        """
        if self.policy == ConsolidationPolicy.IMMEDIATE:
            return True

        elif self.policy == ConsolidationPolicy.THRESHOLD:
            return self.short_term.should_consolidate()

        elif self.policy == ConsolidationPolicy.PERIODIC:
            # Consolidate every 5 minutes
            time_since_last = time.time() - self.last_consolidation
            return time_since_last >= 300

        elif self.policy == ConsolidationPolicy.AUTO:
            if self.auto_scheduler is None:
                return False
            time_since_last = time.time() - self.last_consolidation
            return self.auto_scheduler.should_consolidate(time_since_last)

        elif self.policy == ConsolidationPolicy.MANUAL:
            return False

        return False

    def consolidate(self) -> ConsolidationResult:
        """
        Perform memory consolidation.

        Returns:
            Consolidation result
        """
        start_time = time.time()

        # Consolidate conversation turns
        memories_created = self.short_term.consolidate_to_long_term(
            self.long_term.store,
            self.importance_threshold,
        )

        # Extract patterns
        patterns_extracted = self._extract_patterns()

        # Merge similar memories
        memories_merged = self.long_term.merge_similar()

        # Update last consolidation time
        self.last_consolidation = time.time()

        duration = time.time() - start_time

        result = ConsolidationResult(
            memories_created=memories_created,
            memories_merged=memories_merged,
            patterns_extracted=patterns_extracted,
            duration=duration,
        )

        self._run_count += 1

        # Record with auto-scheduler if active
        if self.auto_scheduler is not None:
            self.auto_scheduler.record_run(result)

        return result

    def _extract_patterns(self) -> int:
        """
        Extract patterns from recent memories.

        Returns:
            Number of patterns extracted
        """
        # Get recent episodic memories
        recent = self.long_term.get_recent(limit=20)
        episodic = [m for m in recent if m.memory_type == MemoryType.EPISODIC]

        if len(episodic) < 3:
            return 0

        # Look for repeated patterns
        patterns = self._find_repeated_patterns(episodic)

        # Create semantic memories from patterns
        patterns_created = 0
        for pattern in patterns:
            self.long_term.add(
                content=pattern["description"],
                memory_type=MemoryType.SEMANTIC,
                importance=pattern["importance"],
                tags=["pattern", "learned"],
                context={"occurrences": pattern["count"]},
            )
            patterns_created += 1

        return patterns_created

    def _find_repeated_patterns(self, memories: list[Memory]) -> list[dict]:
        """
        Find repeated patterns in memories.

        Args:
            memories: List of memories to analyze

        Returns:
            List of patterns found
        """
        patterns = []

        # Simple pattern detection: look for repeated keywords
        keyword_counts = {}

        for memory in memories:
            words = memory.content.lower().split()
            for word in words:
                if len(word) > 4:  # Only meaningful words
                    keyword_counts[word] = keyword_counts.get(word, 0) + 1

        # Find frequently occurring keywords
        for keyword, count in keyword_counts.items():
            if count >= 3:  # Appears at least 3 times
                patterns.append({
                    "description": f"Frequently discussed: {keyword}",
                    "importance": min(1.0, 0.5 + (count * 0.1)),
                    "count": count,
                })

        return patterns

    def consolidate_specific(
        self,
        turns: list[ConversationTurn],
        memory_type: MemoryType = MemoryType.EPISODIC,
    ) -> int:
        """
        Consolidate specific conversation turns.

        Args:
            turns: Turns to consolidate
            memory_type: Type of memory to create

        Returns:
            Number of memories created
        """
        created = 0

        for turn in turns:
            # Calculate importance
            importance = self._calculate_turn_importance(turn)

            if importance >= self.importance_threshold:
                self.long_term.add(
                    content=f"{turn.role}: {turn.content}",
                    memory_type=memory_type,
                    importance=importance,
                    tags=[turn.role, "conversation"],
                    context={
                        "timestamp": turn.timestamp,
                        "metadata": turn.metadata,
                    },
                )
                created += 1

        return created

    def _calculate_turn_importance(self, turn: ConversationTurn) -> float:
        """
        Calculate importance of a conversation turn.

        Args:
            turn: Conversation turn

        Returns:
            Importance score (0.0 - 1.0)
        """
        importance = 0.5

        # User turns are more important
        if turn.role == "user":
            importance += 0.2

        # Longer content is more important
        content_length = len(turn.content)
        if content_length > 100:
            importance += 0.1
        if content_length > 500:
            importance += 0.1

        # Metadata can indicate importance
        if turn.metadata.get("important"):
            importance += 0.2

        return min(1.0, importance)

    def extract_knowledge(self, topic: str) -> Memory | None:
        """
        Extract knowledge about a topic from recent memories.

        Args:
            topic: Topic to extract knowledge about

        Returns:
            Semantic memory with extracted knowledge
        """
        # Search for relevant memories
        relevant = self.long_term.search_by_content(topic, limit=10)

        if not relevant:
            return None

        # Combine information
        knowledge_points = []
        for memory in relevant:
            if topic.lower() in memory.content.lower():
                knowledge_points.append(memory.content)

        if not knowledge_points:
            return None

        # Create semantic memory
        knowledge = self.long_term.add(
            content=f"Knowledge about {topic}: " + "; ".join(knowledge_points[:3]),
            memory_type=MemoryType.SEMANTIC,
            importance=0.7,
            tags=[topic, "knowledge", "extracted"],
            context={"source_count": len(knowledge_points)},
        )

        return knowledge

    def create_procedure(
        self,
        name: str,
        steps: list[str],
        importance: float = 0.6,
    ) -> Memory:
        """
        Create a procedural memory.

        Args:
            name: Procedure name
            steps: List of steps
            importance: Importance score

        Returns:
            Created procedural memory
        """
        content = f"Procedure: {name}\n"
        for i, step in enumerate(steps, 1):
            content += f"{i}. {step}\n"

        return self.long_term.add(
            content=content,
            memory_type=MemoryType.PROCEDURAL,
            importance=importance,
            tags=[name, "procedure"],
            context={"step_count": len(steps)},
        )

    def auto_consolidate(self) -> ConsolidationResult | None:
        """
        Automatically consolidate if policy allows.

        Returns:
            Consolidation result if consolidation occurred
        """
        if self.should_consolidate():
            return self.consolidate()
        return None

    def get_statistics(self) -> dict:
        """
        Get consolidation statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "policy": self.policy.value,
            "importance_threshold": self.importance_threshold,
            "last_consolidation": self.last_consolidation,
            "time_since_last": time.time() - self.last_consolidation,
            "should_consolidate": self.should_consolidate(),
        }
