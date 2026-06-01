"""Structured forum with status lifecycle.

Extends DiscussionForum with explicit thread lifecycle states,
transition validation, and aging/staleness tracking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_core.collective import DiscussionForum, ForumPost


class ForumLifecycle(str, Enum):
    """Explicit lifecycle states for discussion threads.

    States follow a linear progression with re-open support:
      OPEN → ACTIVE → CONVERGING → RESOLVED | DEAD_END | STALE
    """

    OPEN = "open"             # Created, awaiting participants
    ACTIVE = "active"         # Active discussion underway
    CONVERGING = "converging"  # Consensus forming, nearing resolution
    RESOLVED = "resolved"     # Consensus reached
    DEAD_END = "dead_end"     # Determined to be a dead end
    STALE = "stale"           # Inactive too long, needs revival
    CLOSED = "closed"         # Administratively closed


# Valid transitions
_LIFECYCLE_TRANSITIONS: dict[ForumLifecycle, set[ForumLifecycle]] = {
    ForumLifecycle.OPEN: {ForumLifecycle.ACTIVE, ForumLifecycle.CLOSED, ForumLifecycle.STALE},
    ForumLifecycle.ACTIVE: {ForumLifecycle.CONVERGING, ForumLifecycle.DEAD_END,
                            ForumLifecycle.STALE, ForumLifecycle.CLOSED},
    ForumLifecycle.CONVERGING: {ForumLifecycle.RESOLVED, ForumLifecycle.ACTIVE,
                                ForumLifecycle.DEAD_END, ForumLifecycle.STALE},
    ForumLifecycle.RESOLVED: {ForumLifecycle.ACTIVE},  # Can re-open
    ForumLifecycle.DEAD_END: {ForumLifecycle.ACTIVE},  # Can re-open if new evidence
    ForumLifecycle.STALE: {ForumLifecycle.ACTIVE, ForumLifecycle.CLOSED},
    ForumLifecycle.CLOSED: set(),
}


@dataclass
class LifecycleTransition:
    """Record of a lifecycle state change."""

    from_state: ForumLifecycle
    to_state: ForumLifecycle
    timestamp: float = field(default_factory=time.time)
    reason: str = ""


@dataclass
class StructuredThread:
    """A discussion thread with explicit lifecycle management.

    Wraps a DiscussionThread with lifecycle state tracking.
    """

    thread: DiscussionThread
    lifecycle: ForumLifecycle = ForumLifecycle.OPEN
    transition_history: list[LifecycleTransition] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)
    stale_after_s: float = 3600.0  # 1 hour default

    @property
    def is_stale(self) -> bool:
        """Thread is stale if inactive beyond stale_after_s."""
        if self.lifecycle in (ForumLifecycle.RESOLVED, ForumLifecycle.CLOSED):
            return False
        return (time.time() - self.last_activity) > self.stale_after_s

    @property
    def is_terminal(self) -> bool:
        return self.lifecycle in (ForumLifecycle.RESOLVED, ForumLifecycle.CLOSED)

    def transition(self, to_state: ForumLifecycle, reason: str = "") -> bool:
        """Attempt a lifecycle transition. Returns True if valid."""
        valid = _LIFECYCLE_TRANSITIONS.get(self.lifecycle, set())
        if to_state not in valid:
            return False
        transition = LifecycleTransition(
            from_state=self.lifecycle, to_state=to_state, reason=reason,
        )
        self.transition_history.append(transition)
        self.lifecycle = to_state
        self.last_activity = time.time()
        return True

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def check_staleness(self) -> bool:
        """Check and auto-transition to STALE if needed."""
        if self.is_stale and self.lifecycle not in (
            ForumLifecycle.STALE, ForumLifecycle.RESOLVED, ForumLifecycle.CLOSED,
        ):
            self.transition(ForumLifecycle.STALE, "Auto-stale: inactivity timeout")
            return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread.id,
            "topic": self.thread.topic,
            "lifecycle": self.lifecycle.value,
            "post_count": self.thread.post_count,
            "consensus": self.thread.consensus.value,
            "is_stale": self.is_stale,
            "is_terminal": self.is_terminal,
            "transitions": len(self.transition_history),
            "last_activity": self.last_activity,
        }


class StructuredForum:
    """Forum with lifecycle-managed threads.

    Wraps DiscussionForum and adds lifecycle tracking, staleness
    detection, and structured transition validation.

    Usage::

        forum = StructuredForum()
        sthread = forum.create_thread("t1", "Q: optimal batch size?", "H: 32")
        forum.activate("t1")
        forum.converge("t1")
        forum.resolve("t1", "Confirmed: 32 is optimal")
    """

    def __init__(self) -> None:
        self._forum = DiscussionForum()
        self._threads: dict[str, StructuredThread] = {}

    def create_thread(
        self,
        thread_id: str,
        topic: str = "",
        hypothesis: str = "",
        *,
        stale_after_s: float = 3600.0,
    ) -> StructuredThread:
        """Create a new lifecycle-managed thread."""
        thread = self._forum.create_thread(thread_id, topic, hypothesis)
        sthread = StructuredThread(
            thread=thread, stale_after_s=stale_after_s,
        )
        self._threads[thread_id] = sthread
        return sthread

    def get_thread(self, thread_id: str) -> StructuredThread | None:
        return self._threads.get(thread_id)

    def post(self, thread_id: str, post: ForumPost) -> bool:
        """Add a post to a thread, updating lifecycle activity."""
        sthread = self._threads.get(thread_id)
        if sthread is None:
            return False
        self._forum.post(thread_id, post)
        sthread.touch()
        return True

    # ── Lifecycle helpers ──────────────────────────────────────────────

    def activate(self, thread_id: str) -> bool:
        sthread = self._threads.get(thread_id)
        if sthread is None:
            return False
        return sthread.transition(ForumLifecycle.ACTIVE, "Discussion started")

    def converge(self, thread_id: str) -> bool:
        sthread = self._threads.get(thread_id)
        if sthread is None:
            return False
        return sthread.transition(ForumLifecycle.CONVERGING, "Consensus forming")

    def resolve(self, thread_id: str, resolution: str = "") -> bool:
        sthread = self._threads.get(thread_id)
        if sthread is None:
            return False
        if sthread.transition(ForumLifecycle.RESOLVED, resolution):
            self._forum.resolve_thread(thread_id, resolution)
            return True
        return False

    def mark_dead_end(self, thread_id: str, reason: str = "") -> bool:
        sthread = self._threads.get(thread_id)
        if sthread is None:
            return False
        if sthread.transition(ForumLifecycle.DEAD_END, reason):
            self._forum.mark_dead_end(thread_id, reason)
            return True
        return False

    def close(self, thread_id: str, reason: str = "") -> bool:
        sthread = self._threads.get(thread_id)
        if sthread is None:
            return False
        return sthread.transition(ForumLifecycle.CLOSED, reason)

    def reopen(self, thread_id: str, reason: str = "") -> bool:
        """Re-open a resolved or dead-ended thread."""
        sthread = self._threads.get(thread_id)
        if sthread is None:
            return False
        return sthread.transition(ForumLifecycle.ACTIVE, reason)

    # ── Maintenance ────────────────────────────────────────────────────

    def check_all_staleness(self) -> list[str]:
        """Check all threads for staleness. Returns IDs of newly-stale threads."""
        stale = []
        for tid, sthread in self._threads.items():
            if sthread.check_staleness():
                stale.append(tid)
        return stale

    def stale_threads(self) -> list[StructuredThread]:
        return [s for s in self._threads.values() if s.is_stale]

    def active_threads(self) -> list[StructuredThread]:
        return [
            s for s in self._threads.values()
            if s.lifecycle in (ForumLifecycle.OPEN, ForumLifecycle.ACTIVE,
                               ForumLifecycle.CONVERGING)
        ]

    def terminal_threads(self) -> list[StructuredThread]:
        return [s for s in self._threads.values() if s.is_terminal]

    def thread_count(self) -> int:
        return len(self._threads)

    def summary(self) -> dict[str, Any]:
        return {
            "total_threads": len(self._threads),
            "by_lifecycle": {
                state.value: len([
                    s for s in self._threads.values()
                    if s.lifecycle == state
                ])
                for state in ForumLifecycle
            },
            "stale_count": len(self.stale_threads()),
            "active_count": len(self.active_threads()),
            "terminal_count": len(self.terminal_threads()),
        }
