"""Phase O.2 — bridge between the chat lifecycle and the skill ledger.

When a turn fires, the harness needs three things to keep the ledger
honest:

1. **Capture which skills were activated this turn.** The renderer
   side (:func:`skills_inject.render_skill_block_with_activations`)
   already emits the list — we just remember it on the recorder
   keyed by ``(session_id, turn)``.
2. **Watch the lifecycle for the verdict.** ``turn_complete`` is a
   success signal; ``turn_rejected`` is a failure with a reason.
3. **Write back to the ledger.** Bookkeeping happens in one place
   (this module) so future code paths (the future LSP-style
   ``/skill verdict`` slash command, the ``lyra serve`` HTTP API)
   can hook the same recorder without each owning a copy of the
   "load → record → save" dance.

Design notes
------------

* The recorder is intentionally **stateless across processes**:
  the source of truth is the ledger file. We only keep a tiny
  per-process map (``(session, turn) → [(skill, reason), …]``)
  to bridge the two events that bound a turn.
* A turn that activated *zero* skills writes nothing — the ledger
  shouldn't grow phantom rows just because a turn ran.
* A failure that arrives *before* any ``note_activation`` call
  (``provider_init_failed`` etc.) is a no-op: there's nothing to
  attribute it to. We could attribute to "the model itself" in
  the future but that belongs in the burn dashboard, not the
  skill ledger.
* The recorder honours an injected timestamp factory so tests can
  pin time without ``freezegun``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from lyra_skills.ledger import (
    OUTCOME_FAILURE,
    OUTCOME_SUCCESS,
    SkillOutcome,
    record_outcome,
)


@dataclass
class _Activation:
    skill_id: str
    reason: str


@dataclass
class SkillActivationRecorder:
    """Per-process bridge: lifecycle events → skill ledger writes.

    Owned by the :class:`InteractiveSession` (one per REPL) and by
    the embedded :class:`LyraClient` for non-REPL programmatic
    access. Both feed it via :meth:`note_activation` after the
    skill block renders, then call :meth:`on_turn_complete` /
    :meth:`on_turn_rejected` from their lifecycle handlers.
    """

    ledger_path: Path | None = None
    now: Callable[[], float] = field(default_factory=lambda: time.time)
    _pending: dict[tuple[str, int], list[_Activation]] = field(default_factory=dict)

    def note_activation(
        self,
        *,
        session_id: str,
        turn: int,
        skill_id: str,
        reason: str,
    ) -> None:
        """Mark *skill_id* as active for the given ``(session, turn)``.

        Multiple calls for the same turn accumulate — a turn that
        activates ``tdd-discipline`` and ``surgical-changes`` will
        record an outcome against *both* when the verdict arrives.
        """
        key = (session_id, int(turn))
        bucket = self._pending.setdefault(key, [])
        bucket.append(_Activation(skill_id=skill_id, reason=reason or ""))

    def on_turn_complete(self, *, session_id: str, turn: int) -> None:
        """Lifecycle hook — chalk every activation up as a success."""
        self._settle(
            session_id=session_id,
            turn=turn,
            kind=OUTCOME_SUCCESS,
            failure_reason="",
        )

    def on_turn_rejected(
        self,
        *,
        session_id: str,
        turn: int,
        reason: str,
    ) -> None:
        """Lifecycle hook — chalk every activation up as a failure."""
        self._settle(
            session_id=session_id,
            turn=turn,
            kind=OUTCOME_FAILURE,
            failure_reason=reason,
        )

    def discard_turn(self, *, session_id: str, turn: int) -> None:
        """Drop any pending activations without writing to the ledger.

        Used when a turn neither completes nor is rejected — e.g.
        the user hits Ctrl-C mid-stream — and we don't want a
        zombie record waiting in the recorder forever.
        """
        self._pending.pop((session_id, int(turn)), None)

    def _settle(
        self,
        *,
        session_id: str,
        turn: int,
        kind: str,
        failure_reason: str,
    ) -> None:
        key = (session_id, int(turn))
        activations = self._pending.pop(key, None)
        if not activations:
            return
        ts = float(self.now())
        for act in activations:
            detail = act.reason if kind == OUTCOME_SUCCESS else (
                failure_reason or act.reason or "turn rejected"
            )
            record_outcome(
                act.skill_id,
                SkillOutcome(
                    ts=ts,
                    session_id=session_id,
                    turn=int(turn),
                    kind=kind,
                    detail=detail,
                ),
                path=self.ledger_path,
            )


__all__ = ["SkillActivationRecorder"]
