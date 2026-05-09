"""Episodic → semantic consolidation cycle (steal from agentmemory).

agentmemory pumps memories along a four-tier ladder during its
heartbeat: raw observations → episodic summaries → semantic facts →
procedural workflows. Lyra already has the substrates (HIR events,
auto_memory, reasoning_bank, procedural) but no compression cycle.

This module ships the **episodic → semantic** step: scan recent
:class:`~lyra_core.memory.auto_memory.MemoryEntry` rows, cluster them
by token overlap, and for any cluster of ≥ ``min_cluster_size``
entries propose a single consolidated semantic lesson candidate.

Like :mod:`contradictions`, the consolidator returns *proposals*. It
never writes to ``reasoning_bank``: the host harness picks which
proposals to commit (typically behind ``BL-PROMOTE-SKILL``).

The remaining tier transitions (working → episodic, semantic →
procedural) plug in via the same surface; this MVP focuses on the
edge with the highest leverage — most agent rot accumulates as
duplicate episodic entries that nobody promoted.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
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
class ConsolidationProposal:
    """One cluster the consolidator suggests promoting to a semantic lesson.

    The host harness picks whether to commit this as a reasoning_bank
    lesson, a procedural skill, or to discard it after review.
    """

    cluster_kind: MemoryKind
    member_entry_ids: tuple[str, ...]
    shared_tokens: tuple[str, ...]          # the high-frequency token core
    proposed_title: str
    proposed_body: str
    cohesion: float                          # mean pairwise Jaccard

    @property
    def member_count(self) -> int:
        return len(self.member_entry_ids)


@dataclass
class MemoryConsolidator:
    """Cluster auto_memory entries; propose semantic-lesson promotions."""

    similarity_threshold: float = 0.30
    min_cluster_size: int = 3
    only_kinds: tuple[MemoryKind, ...] = (
        MemoryKind.PROJECT, MemoryKind.FEEDBACK,
    )
    max_proposals: int = 25                  # safety cap per cycle

    def propose(
        self, entries: Iterable[MemoryEntry],
    ) -> tuple[ConsolidationProposal, ...]:
        """Group entries; return one proposal per qualifying cluster."""
        active = [
            e for e in entries
            if not e.deleted and e.kind in self.only_kinds
        ]
        if len(active) < self.min_cluster_size:
            return ()

        # Greedy single-link clustering. For each entry, attach to an
        # existing cluster if its mean Jaccard ≥ threshold; else seed
        # a new one. Order-stable for deterministic tests.
        clusters: list[list[tuple[MemoryEntry, set[str]]]] = []
        for entry in sorted(active, key=lambda e: e.created_ts):
            tok = _tokens(f"{entry.title} {entry.body}")
            if not tok:
                continue
            placed = False
            for cluster in clusters:
                mean_sim = sum(
                    _jaccard(tok, t) for _, t in cluster
                ) / len(cluster)
                if mean_sim >= self.similarity_threshold:
                    cluster.append((entry, tok))
                    placed = True
                    break
            if not placed:
                clusters.append([(entry, tok)])

        proposals: list[ConsolidationProposal] = []
        for cluster in clusters:
            if len(cluster) < self.min_cluster_size:
                continue
            proposal = self._synthesise(cluster)
            if proposal is not None:
                proposals.append(proposal)
            if len(proposals) >= self.max_proposals:
                break
        return tuple(proposals)

    # --- internals ----------------------------------------------------

    def _synthesise(
        self, cluster: list[tuple[MemoryEntry, set[str]]],
    ) -> ConsolidationProposal | None:
        if not cluster:
            return None
        tokens_per_entry = [tok for _, tok in cluster]
        # Shared-tokens core = tokens appearing in ≥ 50% of entries.
        counts: Counter[str] = Counter()
        for tok in tokens_per_entry:
            counts.update(tok)
        majority_threshold = max(2, len(cluster) // 2)
        shared = tuple(
            t for t, c in counts.most_common()
            if c >= majority_threshold
        )[:24]
        if not shared:
            return None

        kind = cluster[0][0].kind
        # Mean pairwise cohesion (upper triangle).
        n = len(cluster)
        sims: list[float] = []
        for i in range(n):
            for j in range(i + 1, n):
                sims.append(_jaccard(tokens_per_entry[i], tokens_per_entry[j]))
        cohesion = (sum(sims) / len(sims)) if sims else 1.0

        member_ids = tuple(e.entry_id for e, _ in cluster)
        # Title = first 8 shared tokens joined; body = bullet list of
        # member titles for review.
        proposed_title = " ".join(shared[:8])
        proposed_body = (
            f"Consolidates {n} {kind.value} entries sharing core tokens "
            f"({', '.join(shared[:6])}…). Members:\n"
            + "\n".join(f"- {e.title}" for e, _ in cluster[:8])
        )
        return ConsolidationProposal(
            cluster_kind=kind,
            member_entry_ids=member_ids,
            shared_tokens=shared,
            proposed_title=proposed_title,
            proposed_body=proposed_body,
            cohesion=cohesion,
        )


__all__ = ["ConsolidationProposal", "MemoryConsolidator"]
