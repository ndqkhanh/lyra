"""SubAgentDigest broadcast bus — SRMT-style cross-agent coordination (Phase M5).

The closed-LLM analog of SRMT's pooled-memory cross-attention. Each sub-agent
emits a compact SubAgentDigest after every step; the orchestrator's prompt is
auto-augmented with the latest digest per peer (capped at 600 tokens total).

Key design:
  - Digests are NOT embedded / NOT part of vector search.
  - Stored in a dedicated fast-access table, keyed by (task_id, agent_id, step).
  - Retrieved by task_id to get all peer digests for orchestrator injection.
  - When two sub-agents write contradictory fragments, both are stored at task
    scope with a ConflictEvent(reason="agent_disagreement") logged. The
    orchestrator is prompted to resolve before T2 promotion.

Integration:
  - Wire into observability/event_bus.py: SubagentSpawned triggers digest slot
    creation; SubagentFinished finalizes it.
  - Orchestrator reads latest digest per sub-agent before each turn via
    recall_digests(task_id).

Research grounding:
  - SRMT (Sagirova et al. ICLR 2025) — pooled-memory cross-attention for
    multi-agent coordination.
  - Design proposal §9 multi-agent conflict resolution.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .schema import ConflictEvent, Fragment, SubAgentDigest


# ---------------------------------------------------------------------------
# DigestStore — fast-access table for SubAgentDigest
# ---------------------------------------------------------------------------


class DigestStore:
    """In-memory store for SubAgentDigest keyed by (task_id, agent_id, step).

    Thread-safe. Supports:
      - write(digest): store a new digest
      - get_latest(task_id, agent_id): get the most recent digest for an agent
      - get_all_latest(task_id): get latest digest per agent for a task
      - get_history(task_id, agent_id): get all digests for an agent in a task
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (task_id, agent_id, step) → SubAgentDigest
        self._digests: dict[tuple[str, str, int], SubAgentDigest] = {}
        # (task_id, agent_id) → max_step
        self._latest_step: dict[tuple[str, str], int] = {}

    def write(self, digest: SubAgentDigest) -> None:
        """Store a digest. Overwrites if (task_id, agent_id, step) exists."""
        key = (digest.task_id, digest.agent_id, digest.step)
        with self._lock:
            self._digests[key] = digest
            latest_key = (digest.task_id, digest.agent_id)
            current_max = self._latest_step.get(latest_key, -1)
            if digest.step > current_max:
                self._latest_step[latest_key] = digest.step

    def get_latest(self, task_id: str, agent_id: str) -> SubAgentDigest | None:
        """Get the most recent digest for (task_id, agent_id)."""
        with self._lock:
            latest_key = (task_id, agent_id)
            step = self._latest_step.get(latest_key)
            if step is None:
                return None
            key = (task_id, agent_id, step)
            return self._digests.get(key)

    def get_all_latest(self, task_id: str) -> list[SubAgentDigest]:
        """Get latest digest per agent for a task, sorted by agent_id."""
        with self._lock:
            agents = {
                agent_id
                for (tid, agent_id), _ in self._latest_step.items()
                if tid == task_id
            }
            digests = []
            for agent_id in sorted(agents):
                latest_key = (task_id, agent_id)
                step = self._latest_step.get(latest_key)
                if step is not None:
                    key = (task_id, agent_id, step)
                    digest = self._digests.get(key)
                    if digest:
                        digests.append(digest)
            return digests

    def get_history(self, task_id: str, agent_id: str) -> list[SubAgentDigest]:
        """Get all digests for (task_id, agent_id), sorted by step."""
        with self._lock:
            matches = [
                d
                for (tid, aid, _), d in self._digests.items()
                if tid == task_id and aid == agent_id
            ]
            return sorted(matches, key=lambda d: d.step)

    def clear_task(self, task_id: str) -> None:
        """Remove all digests for a task (cleanup after task completion)."""
        with self._lock:
            to_remove = [
                key for key in self._digests if key[0] == task_id
            ]
            for key in to_remove:
                del self._digests[key]
            to_remove_latest = [
                key for key in self._latest_step if key[0] == task_id
            ]
            for key in to_remove_latest:
                del self._latest_step[key]

    def __len__(self) -> int:
        with self._lock:
            return len(self._digests)


# ---------------------------------------------------------------------------
# DigestBus — orchestrator-facing API
# ---------------------------------------------------------------------------


@dataclass
class DigestSummary:
    """Compact summary of all peer digests for orchestrator prompt injection."""

    task_id: str
    digests: list[SubAgentDigest] = field(default_factory=list)
    total_chars: int = 0
    truncated: bool = False

    def render(self, max_chars: int = 600) -> str:
        """Render all digests into a compact text block for prompt injection."""
        if not self.digests:
            return ""

        lines = ["[Peer Agent Digests]"]
        budget = max_chars - len(lines[0]) - 10  # reserve for truncation marker
        used = 0

        for digest in self.digests:
            compact = digest.render_compact(max_chars=300)
            if used + len(compact) + 1 > budget:
                lines.append("... (truncated)")
                self.truncated = True
                break
            lines.append(compact)
            used += len(compact) + 1

        self.total_chars = sum(len(line) for line in lines)
        return "\n".join(lines)


class DigestBus:
    """High-level API for SubAgentDigest broadcast and retrieval.

    Usage::
        bus = DigestBus()

        # Sub-agent emits digest after each step
        digest = SubAgentDigest(
            agent_id="agent-1",
            task_id="task-123",
            step=1,
            last_action="ran pytest tests/test_auth.py; 3 failures",
            findings=["JWT secret not set in test env", "Mock user missing email field"],
            open_questions=["Should we use a test fixture for JWT secrets?"],
            next_intent="Fix JWT secret configuration",
            confidence=0.8,
        )
        bus.emit(digest)

        # Orchestrator retrieves all peer digests before next turn
        summary = bus.recall_digests("task-123", max_chars=600)
        prompt_with_context = base_prompt + "\n\n" + summary.render()
    """

    def __init__(self, store: DigestStore | None = None) -> None:
        self._store = store or DigestStore()
        self._conflict_log: list[ConflictEvent] = []
        self._lock = threading.Lock()

    @property
    def store(self) -> DigestStore:
        return self._store

    @property
    def conflicts(self) -> list[ConflictEvent]:
        with self._lock:
            return list(self._conflict_log)

    def emit(self, digest: SubAgentDigest) -> None:
        """Emit a digest from a sub-agent. Thread-safe."""
        self._store.write(digest)

    def recall_digests(
        self,
        task_id: str,
        max_chars: int = 600,
    ) -> DigestSummary:
        """Retrieve all latest digests for a task, formatted for orchestrator."""
        digests = self._store.get_all_latest(task_id)
        summary = DigestSummary(task_id=task_id, digests=digests)
        summary.render(max_chars=max_chars)
        return summary

    def get_agent_history(self, task_id: str, agent_id: str) -> list[SubAgentDigest]:
        """Get full digest history for a specific agent in a task."""
        return self._store.get_history(task_id, agent_id)

    def detect_conflicts(
        self,
        fragments: list[Fragment],
        task_id: str,
    ) -> list[ConflictEvent]:
        """Detect contradictions between fragments from different agents.

        When two sub-agents write contradictory fragments (overlapping entities,
        diverging content), both are stored at task scope with a
        ConflictEvent(reason="agent_disagreement") logged.

        The orchestrator is prompted to resolve before T2 promotion.
        """
        conflicts: list[ConflictEvent] = []
        task_fragments = [f for f in fragments if f.provenance.task_id == task_id]

        # Check all pairs for conflicts
        for i, frag_a in enumerate(task_fragments):
            if not frag_a.entities:
                continue

            for frag_b in task_fragments[i + 1 :]:
                if not frag_b.entities:
                    continue

                # Same agent → not a cross-agent conflict
                if frag_a.provenance.agent_id == frag_b.provenance.agent_id:
                    continue

                # Check for entity overlap
                entities_a = set(frag_a.entities)
                entities_b = set(frag_b.entities)
                if not (entities_a & entities_b):  # no overlap
                    continue

                # Check content divergence
                content_sim = self._content_similarity(
                    frag_a.content, frag_b.content
                )
                if content_sim < 0.7:  # diverging content
                    conflict = ConflictEvent.make(
                        old_id=frag_a.id,
                        new_id=frag_b.id,
                        reason="agent_disagreement",
                        resolution="human_required",
                    )
                    conflicts.append(conflict)

        with self._lock:
            self._conflict_log.extend(conflicts)

        return conflicts

    def clear_task(self, task_id: str) -> None:
        """Remove all digests for a task (cleanup after completion)."""
        self._store.clear_task(task_id)

    @staticmethod
    def _content_similarity(a: str, b: str) -> float:
        """Jaccard similarity of token sets."""
        def token_set(text: str) -> set[str]:
            return {w.lower() for w in text.split() if len(w) > 2}

        sa, sb = token_set(a), token_set(b)
        if not sa and not sb:
            return 1.0
        union = sa | sb
        return len(sa & sb) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


_DIGEST_BUS: DigestBus | None = None
_DIGEST_BUS_LOCK = threading.Lock()


def get_digest_bus() -> DigestBus:
    """Return the global singleton DigestBus, creating it on first call."""
    global _DIGEST_BUS
    if _DIGEST_BUS is None:
        with _DIGEST_BUS_LOCK:
            if _DIGEST_BUS is None:
                _DIGEST_BUS = DigestBus()
    return _DIGEST_BUS


def reset_digest_bus() -> None:
    """Reset the global singleton (test isolation only)."""
    global _DIGEST_BUS
    with _DIGEST_BUS_LOCK:
        _DIGEST_BUS = None


__all__ = [
    "DigestBus",
    "DigestStore",
    "DigestSummary",
    "get_digest_bus",
    "reset_digest_bus",
]
