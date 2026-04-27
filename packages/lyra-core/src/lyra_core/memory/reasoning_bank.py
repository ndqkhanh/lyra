"""ReasoningBank with failure-distillation + MaTTS (v1.8 Wave-1 §3.2).

Inspired by *ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory*
(Google Research, 2025 — arXiv:2509.25140, mirrored under
``papers/reasoningbank-mattS.pdf``).

Design intent:

- A ``ReasoningBank`` records *both* successful and failed agent trajectories,
  distils each into a generalisable "lesson" (a short, retrievable strategy or
  anti-pattern), and surfaces the relevant lessons on the next invocation.
- *Failure-distillation* is the novel piece: a failed trajectory becomes an
  "anti-skill" — a description of a misstep + the recovery move that would
  have helped. Anti-skills are first-class memories, not throwaway logs.
- *MaTTS* (memory-aware test-time scaling) pairs the bank with the v1.8
  Tournament TTS (``..tts.tournament``): each tournament attempt receives
  the top-k relevant lessons as a context prefix, accelerating convergence
  and diversifying the candidate pool.

Phase 0: contracts only. Distillation, MaTTS injection, and persistence
are stubs that raise ``NotImplementedError``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class TrajectoryOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class TrajectoryStep:
    """One observable step inside a trajectory (tool call, message, edit)."""

    index: int
    kind: str           # e.g. "tool_call", "message", "edit"
    payload: str        # opaque to the bank; carried for distillation


@dataclass(frozen=True)
class Trajectory:
    """The full record of one agent attempt."""

    id: str
    task_signature: str           # canonicalised intent — used for retrieval
    outcome: TrajectoryOutcome
    steps: tuple[TrajectoryStep, ...]
    final_artefact: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Lesson:
    """A distilled, retrievable reasoning fragment.

    A *positive* lesson encodes a known-good strategy; a *negative* lesson
    (anti-skill) encodes a known-bad pattern + the suggested recovery.
    Both are returned by ``ReasoningBank.recall``.
    """

    id: str
    polarity: TrajectoryOutcome   # SUCCESS == strategy; FAILURE == anti-skill
    title: str
    body: str
    task_signatures: tuple[str, ...]
    source_trajectory_ids: tuple[str, ...]


class Distiller(Protocol):
    """Turns one trajectory into 0..N lessons.

    Implementations are expected to be deterministic for a fixed
    ``(trajectory, model)`` pair so that snapshotting works.
    """

    def distill(self, trajectory: Trajectory) -> Sequence[Lesson]: ...


class ReasoningBank:
    """Persistent reasoning memory.

    Phase 1 (v1.8) ships an **in-memory store** that satisfies the full
    public surface (`record`, `recall`, `matts_prefix`); Phase 2 will
    swap the backing list for the same SQLite + FTS5 store Lyra v1.7
    already uses for sessions, behind the same protocol-shape so
    callers don't notice.
    """

    def __init__(self, distiller: Distiller) -> None:
        self._distiller = distiller
        self._lessons: list[Lesson] = []

    def record(self, trajectory: Trajectory) -> tuple[Lesson, ...]:
        """Distill a trajectory; persist + return its lessons.

        Failure trajectories are first-class — the distiller is expected
        to emit at least one *anti-skill* lesson per failure so the bank
        always grows on a learning event (the failure-distillation
        contract from arXiv:2509.25140).
        """
        lessons = tuple(self._distiller.distill(trajectory))
        self._lessons.extend(lessons)
        return lessons

    def recall(
        self,
        task_signature: str,
        *,
        k: int = 3,
        polarity: TrajectoryOutcome | None = None,
        diversity_weighted: bool = False,
    ) -> tuple[Lesson, ...]:
        """Top-k lessons relevant to ``task_signature``.

        ``polarity=None`` returns mixed strategies + anti-skills;
        passing one filters.

        ``diversity_weighted=True`` (v1.8 Phase 6) routes the rank through
        :func:`lyra_core.diversity.mmr_select` so the returned lessons are
        relevant *and* mutually distinct — the documented Echo-Chamber
        counter-measure (arXiv:2604.18005). Default ``False`` preserves the
        cheap top-k behaviour for callers that don't care about coupling.

        Phase 1 ranking is intentionally simple:

        - **Exact matches** on ``task_signature`` win first.
        - **Substring matches** (caller-signature is a substring of any
          stored signature, or vice-versa) win second.
        - Older lessons fall to the bottom.

        Phase 2 will replace this with FTS5 BM25 ranking; the contract
        on the return shape is identical.
        """
        if k <= 0:
            return ()

        candidates = (
            [lesson for lesson in self._lessons if lesson.polarity is polarity]
            if polarity is not None
            else list(self._lessons)
        )

        sig_norm = task_signature.strip().lower()

        def _rank(lesson: Lesson) -> tuple[int, int]:
            sigs = tuple(s.strip().lower() for s in lesson.task_signatures)
            if sig_norm in sigs:
                return (0, -self._lessons.index(lesson))
            if any(sig_norm in s or s in sig_norm for s in sigs if s):
                return (1, -self._lessons.index(lesson))
            return (2, -self._lessons.index(lesson))

        ranked = sorted(candidates, key=_rank)

        if diversity_weighted and len(ranked) > k:
            from lyra_core.diversity import mmr_select

            relevance: dict[str, float] = {}
            id_to_lesson: dict[str, Lesson] = {}
            for lesson in ranked:
                key = lesson.body or lesson.title or lesson.id
                relevance[key] = max(
                    relevance.get(key, 0.0),
                    1.0 / (1 + ranked.index(lesson)),
                )
                id_to_lesson[key] = lesson
            picked_keys = mmr_select(
                tuple(relevance.keys()),
                k=k,
                relevance=relevance,
            )
            return tuple(id_to_lesson[picked] for picked in picked_keys)

        return tuple(ranked[:k])

    def matts_prefix(
        self,
        task_signature: str,
        attempt_index: int,
        *,
        k: int = 3,
    ) -> str:
        """Prefix string injected into a Tournament-TTS attempt prompt.

        Different ``attempt_index`` values must produce *different*
        prefixes — that's the MaTTS contract (the ReasoningBank
        deliberately diversifies the candidate pool to dodge the
        Echo-Chamber failure mode in arXiv:2604.18005 §4).

        Phase 1 strategy: rotate the recall window by ``attempt_index``
        so each attempt sees a different *slice* of the recalled
        lessons. With N lessons available and k=3, attempt 0 sees
        ``[0,1,2]``, attempt 1 sees ``[1,2,3]``, etc., wrapping around.
        Combined with the per-attempt index suffix, this guarantees a
        distinct prefix for every attempt index that the bank has
        material to draw on.
        """
        pool = self.recall(task_signature, k=max(k * 2, k + attempt_index + 1))
        if not pool:
            return f"# matts attempt={attempt_index} signature={task_signature} (no lessons)"
        rotated = pool[attempt_index % len(pool):] + pool[: attempt_index % len(pool)]
        chosen = rotated[:k]
        body = "\n".join(f"- {lesson.title}: {lesson.body}" for lesson in chosen)
        return (
            f"# matts attempt={attempt_index} signature={task_signature}\n"
            f"{body}"
        )
