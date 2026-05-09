"""Neural Garbage Collection compactor.

Replaces the v1.7.3 LLM-driven ``/compact`` for users who opt in.
Instead of asking the model "summarise the transcript," NGC runs
a **grow-then-evict** pass on the structured context items and
logs every keep/evict decision (plus the downstream outcome) to
``compactor-outcomes.jsonl`` so an offline classifier can be
trained on the log.

The v1 policy is:

* Always keep the ``N`` most recent items.
* Always keep anchor items (``must_keep=True``) such as plan text,
  pinned rules, safety findings.
* Score remaining items by ``usage_signal`` (caller-supplied,
  e.g. how often the item was attended to) and evict the lowest-
  scoring ones until ``token_budget`` is met.

The policy is pluggable: swap in a neural scorer later and the
outcome log becomes its training data.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence


__all__ = [
    "NGCCompactor",
    "NGCDecision",
    "NGCItem",
    "NGCOutcomeLogger",
    "NGCResult",
]


@dataclass(frozen=True)
class NGCItem:
    """One compactable item."""

    id: str
    tokens: int
    must_keep: bool = False
    usage_signal: float = 0.0
    kind: str = "turn"
    content_preview: str = ""


@dataclass(frozen=True)
class NGCDecision:
    """Keep / evict verdict for a single item."""

    item_id: str
    kept: bool
    reason: str


@dataclass(frozen=True)
class NGCResult:
    """Aggregate compaction outcome."""

    kept: tuple[NGCItem, ...]
    evicted: tuple[NGCItem, ...]
    decisions: tuple[NGCDecision, ...]
    token_count_before: int
    token_count_after: int

    @property
    def tokens_freed(self) -> int:
        return self.token_count_before - self.token_count_after

    def to_dict(self) -> dict[str, object]:
        return {
            "kept": [i.id for i in self.kept],
            "evicted": [i.id for i in self.evicted],
            "token_count_before": self.token_count_before,
            "token_count_after": self.token_count_after,
            "tokens_freed": self.tokens_freed,
            "decisions": [
                {"item_id": d.item_id, "kept": d.kept, "reason": d.reason}
                for d in self.decisions
            ],
        }


# ---- outcome logger -----------------------------------------------


@dataclass
class NGCOutcomeLogger:
    """Append-only ``compactor-outcomes.jsonl`` writer.

    Each line shape:
    ``{"turn": int, "kept": [...], "evicted": [...], "outcome": str}``.

    ``outcome`` is supplied by the caller after the turn completes
    ("pass" / "fail" / free-form).  Logging never raises — we
    degrade to a no-op when the path is unwritable so compaction
    can never be blocked by telemetry.
    """

    path: Path

    def log(
        self,
        *,
        turn: int,
        result: NGCResult,
        outcome: str,
    ) -> None:
        record = {
            "turn": turn,
            "kept": [i.id for i in result.kept],
            "evicted": [i.id for i in result.evicted],
            "tokens_freed": result.tokens_freed,
            "outcome": outcome,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True))
                fh.write("\n")
        except OSError:
            # Telemetry is best-effort — never let it take the run down.
            return


# ---- compactor ----------------------------------------------------


Scorer = Callable[[NGCItem], float]


def _default_scorer(item: NGCItem) -> float:
    return item.usage_signal


@dataclass
class NGCCompactor:
    """Grow-then-evict compactor."""

    token_budget: int
    keep_recent: int = 3
    scorer: Scorer = _default_scorer

    def __post_init__(self) -> None:
        if self.token_budget < 0:
            raise ValueError("token_budget must be >= 0")
        if self.keep_recent < 0:
            raise ValueError("keep_recent must be >= 0")

    def compact(self, items: Sequence[NGCItem]) -> NGCResult:
        before = sum(i.tokens for i in items)
        if before <= self.token_budget:
            # Nothing to evict.
            return NGCResult(
                kept=tuple(items),
                evicted=tuple(),
                decisions=tuple(
                    NGCDecision(item_id=i.id, kept=True, reason="under budget")
                    for i in items
                ),
                token_count_before=before,
                token_count_after=before,
            )

        n = len(items)
        recent_ids = {i.id for i in items[max(0, n - self.keep_recent):]}

        anchors = [i for i in items if i.must_keep or i.id in recent_ids]
        anchor_tokens = sum(i.tokens for i in anchors)
        if anchor_tokens > self.token_budget:
            # Anchors alone blow the budget; keep them but report.
            decisions = [
                NGCDecision(item_id=i.id, kept=True, reason="anchor (over budget)")
                for i in anchors
            ] + [
                NGCDecision(
                    item_id=i.id,
                    kept=False,
                    reason="non-anchor evicted (anchors saturate budget)",
                )
                for i in items
                if i not in anchors
            ]
            return NGCResult(
                kept=tuple(anchors),
                evicted=tuple(i for i in items if i not in anchors),
                decisions=tuple(decisions),
                token_count_before=before,
                token_count_after=anchor_tokens,
            )

        # Budget left for non-anchor items, picked highest-score first.
        remaining_budget = self.token_budget - anchor_tokens
        non_anchors = [i for i in items if i not in anchors]
        ranked = sorted(non_anchors, key=lambda i: self.scorer(i), reverse=True)

        kept_non_anchor: list[NGCItem] = []
        decisions: list[NGCDecision] = []
        for item in ranked:
            if item.tokens <= remaining_budget:
                kept_non_anchor.append(item)
                decisions.append(
                    NGCDecision(
                        item_id=item.id,
                        kept=True,
                        reason=f"fits (score={self.scorer(item):.3f})",
                    )
                )
                remaining_budget -= item.tokens
            else:
                decisions.append(
                    NGCDecision(
                        item_id=item.id,
                        kept=False,
                        reason=(
                            f"evicted (score={self.scorer(item):.3f}, "
                            f"remaining_budget={remaining_budget})"
                        ),
                    )
                )

        for anchor in anchors:
            decisions.insert(
                0,
                NGCDecision(item_id=anchor.id, kept=True, reason="anchor"),
            )

        kept = set(i.id for i in anchors) | set(i.id for i in kept_non_anchor)
        kept_items = [i for i in items if i.id in kept]  # preserve order
        evicted_items = [i for i in items if i.id not in kept]
        after = sum(i.tokens for i in kept_items)
        return NGCResult(
            kept=tuple(kept_items),
            evicted=tuple(evicted_items),
            decisions=tuple(decisions),
            token_count_before=before,
            token_count_after=after,
        )
