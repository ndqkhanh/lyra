"""Contradiction detection over auto_memory entries.

Append-only memory has a quiet failure mode: the agent writes "user
prefers terse responses" on Monday, "user prefers thorough explanations"
on Friday, and both rows survive in the JSONL log. Retrieval surfaces
whichever scored higher, masking the conflict.

This module flags pairs of entries within the same :class:`MemoryKind`
where the **title** (the key) is similar but the **body** (the value)
diverges. The signal is heuristic — Jaccard token overlap, not LLM
judgment — but cheap enough to run on every ``improve()`` heartbeat.

The detector returns proposals; it never auto-resolves. The host
harness chooses to forget the older row, surface a clarifying prompt,
or merge — none of those decisions belong in a pure-Python heuristic.

Bright-line: ``LBL-MEMORY-CONTRADICTION-FLAG`` — a contradiction is a
hint to the host harness, not a verdict; resolution is human-in-loop
or LLM-judged at a higher tier.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from .auto_memory import MemoryEntry, MemoryKind


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z\-']{3,}")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return (len(a & b) / len(union)) if union else 0.0


@dataclass(frozen=True)
class ContradictionPair:
    """One flagged pair of entries that look contradictory."""

    older_entry_id: str
    newer_entry_id: str
    kind: MemoryKind
    title_jaccard: float
    body_jaccard: float
    rationale: str

    @property
    def confidence(self) -> str:
        """High when title overlap ≥ 0.7 AND body overlap ≤ 0.10."""
        if self.title_jaccard >= 0.7 and self.body_jaccard <= 0.10:
            return "high"
        return "soft"


@dataclass
class ContradictionDetector:
    """Scan auto_memory for title-similar / body-divergent pairs."""

    title_similarity_min: float = 0.5      # below → not the same key
    body_divergence_max: float = 0.20      # above → bodies agree enough
    only_kinds: tuple[MemoryKind, ...] = (
        MemoryKind.USER, MemoryKind.FEEDBACK, MemoryKind.PROJECT,
    )

    def detect(
        self, entries: Iterable[MemoryEntry],
    ) -> tuple[ContradictionPair, ...]:
        """Return all flagged pairs; ordered older → newer."""
        active = [e for e in entries if not e.deleted]
        # Group by kind so we don't mix a USER preference with a
        # PROJECT decision that happens to share a few tokens.
        by_kind: dict[MemoryKind, list[MemoryEntry]] = {}
        for e in active:
            by_kind.setdefault(e.kind, []).append(e)

        pairs: list[ContradictionPair] = []
        for kind, group in by_kind.items():
            if kind not in self.only_kinds:
                continue
            # Sort by created_ts asc so "older" / "newer" are well-defined.
            group.sort(key=lambda e: e.created_ts)
            for i in range(len(group)):
                ti = _tokens(group[i].title)
                bi = _tokens(group[i].body)
                if not ti:
                    continue
                for j in range(i + 1, len(group)):
                    tj = _tokens(group[j].title)
                    bj = _tokens(group[j].body)
                    if not tj:
                        continue
                    title_sim = _jaccard(ti, tj)
                    if title_sim < self.title_similarity_min:
                        continue
                    body_sim = _jaccard(bi, bj)
                    if body_sim > self.body_divergence_max:
                        continue
                    pairs.append(ContradictionPair(
                        older_entry_id=group[i].entry_id,
                        newer_entry_id=group[j].entry_id,
                        kind=kind,
                        title_jaccard=title_sim,
                        body_jaccard=body_sim,
                        rationale=(
                            f"title overlap {title_sim:.2f} ≥ "
                            f"{self.title_similarity_min:.2f}; "
                            f"body overlap {body_sim:.2f} ≤ "
                            f"{self.body_divergence_max:.2f}"
                        ),
                    ))
        return tuple(pairs)


__all__ = ["ContradictionDetector", "ContradictionPair"]
