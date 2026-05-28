"""Entropic Consolidation — free-energy minimization for robust memory retention.

Based on the Free Energy Principle applied to memory consolidation. Minimizes
variational free energy during memory consolidation to filter out noise and
preserve salient information structures under uncertainty.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class ConsolidationPhase(StrEnum):
    WAKE = "wake"
    NREM_LIGHT = "nrem_light"
    NREM_DEEP = "nrem_deep"
    REM = "rem"
    REHEARSAL = "rehearsal"


@dataclass(frozen=True)
class MemoryFragment:
    fragment_id: str
    content: str
    salience: float
    novelty: float
    emotional_valence: float
    source: str
    timestamp: float


@dataclass(frozen=True)
class ConsolidatedMemory:
    memory_id: str
    fragments: tuple[str, ...]
    summary: str
    free_energy: float
    retained_salience: float
    compression_ratio: float
    phase: ConsolidationPhase


@dataclass
class EntropicConfig:
    temperature: float = 1.0
    salience_threshold: float = 0.1
    novelty_decay: float = 0.95
    max_fragments_per_cycle: int = 100
    free_energy_threshold: float = 0.01
    convergence_iterations: int = 50


class EntropicConsolidator:
    """Free-energy minimization consolidation engine.

    Applies the Free Energy Principle to memory consolidation:
    - WAKE phase: encode new fragments, compute initial salience
    - NREM_LIGHT: cluster related fragments, prune low-salience noise
    - NREM_DEEP: minimize free energy via iterative refinement
    - REM: synthesize abstract patterns across fragments
    - REHEARSAL: strengthen retained memories, decay unused ones
    """

    def __init__(self, config: EntropicConfig | None = None) -> None:
        self.config = config or EntropicConfig()
        self._fragments: dict[str, MemoryFragment] = {}
        self._consolidated: list[ConsolidatedMemory] = []
        self._cycle_count: int = 0

    def ingest(self, fragments: list[MemoryFragment]) -> None:
        """Ingest new memory fragments for consolidation."""
        for frag in fragments:
            self._fragments[frag.fragment_id] = frag

    def consolidate(self, phase: ConsolidationPhase = ConsolidationPhase.NREM_DEEP) -> list[ConsolidatedMemory]:
        """Run one consolidation cycle.

        Returns consolidated memories that emerged from this cycle.
        """
        self._cycle_count += 1
        results: list[ConsolidatedMemory] = []

        if not self._fragments:
            return results

        frags = list(self._fragments.values())

        if phase == ConsolidationPhase.NREM_DEEP:
            results = self._deep_consolidation(frags)
        elif phase == ConsolidationPhase.NREM_LIGHT:
            results = self._light_consolidation(frags)
        elif phase == ConsolidationPhase.REM:
            results = self._rem_synthesis(frags)

        self._consolidated.extend(results)

        # Remove consolidated fragments
        for result in results:
            for fid in result.fragments:
                self._fragments.pop(fid, None)

        return results

    def _light_consolidation(self, frags: list[MemoryFragment]) -> list[ConsolidatedMemory]:
        """NREM Light: prune low-salience fragments, basic clustering."""
        threshold = self.config.salience_threshold
        kept = [f for f in frags if f.salience >= threshold]

        if not kept:
            return []

        # Simple similarity-based clustering
        clusters = _cluster_by_salience(kept, threshold=0.3)

        results: list[ConsolidatedMemory] = []
        for i, cluster in enumerate(clusters):
            if len(cluster) < 2:
                continue
            summary = " | ".join(f.content[:80] for f in cluster[:3])
            avg_salience = sum(f.salience for f in cluster) / len(cluster)
            fe = _compute_free_energy(cluster, self.config.temperature)

            results.append(ConsolidatedMemory(
                memory_id=f"mem-l-{self._cycle_count:04d}-{i:03d}",
                fragments=tuple(f.fragment_id for f in cluster),
                summary=summary,
                free_energy=round(fe, 6),
                retained_salience=round(avg_salience, 4),
                compression_ratio=round(len(cluster) / max(len(frags), 1), 4),
                phase=ConsolidationPhase.NREM_LIGHT,
            ))

        return results

    def _deep_consolidation(self, frags: list[MemoryFragment]) -> list[ConsolidatedMemory]:
        """NREM Deep: minimize free energy via iterative refinement."""
        if len(frags) < 2:
            return []

        # Iteratively refine: find fragment groupings that minimize free energy
        best_fe = float("inf")
        best_cluster: list[MemoryFragment] = []

        for _ in range(min(self.config.convergence_iterations, len(frags))):
            # Random subset for variational optimization
            subset = _sample_subset(frags, min(10, len(frags)))
            fe = _compute_free_energy(subset, self.config.temperature)

            if fe < best_fe and fe < self.config.free_energy_threshold:
                best_fe = fe
                best_cluster = list(subset)

        if not best_cluster:
            return []

        summary = " ; ".join(f.content[:60] for f in best_cluster[:3])
        avg_salience = sum(f.salience for f in best_cluster) / len(best_cluster)

        return [ConsolidatedMemory(
            memory_id=f"mem-d-{self._cycle_count:04d}",
            fragments=tuple(f.fragment_id for f in best_cluster),
            summary=summary,
            free_energy=round(best_fe, 6),
            retained_salience=round(avg_salience, 4),
            compression_ratio=round(len(best_cluster) / max(len(frags), 1), 4),
            phase=ConsolidationPhase.NREM_DEEP,
        )]

    def _rem_synthesis(self, frags: list[MemoryFragment]) -> list[ConsolidatedMemory]:
        """REM: synthesize abstract patterns across diverse fragments."""
        if len(frags) < 3:
            return []

        # Select high-novelty fragments from different sources
        novel = sorted(frags, key=lambda f: f.novelty, reverse=True)[:10]
        sources = list({f.source for f in novel})

        if len(sources) < 2:
            return []

        summary = " ↔ ".join(f"{f.source}:{f.content[:40]}" for f in novel[:5])
        avg_salience = sum(f.salience for f in novel) / len(novel)
        fe = _compute_free_energy(novel, self.config.temperature * 1.5)

        return [ConsolidatedMemory(
            memory_id=f"mem-r-{self._cycle_count:04d}",
            fragments=tuple(f.fragment_id for f in novel),
            summary=summary,
            free_energy=round(fe, 6),
            retained_salience=round(avg_salience, 4),
            compression_ratio=round(len(novel) / max(len(frags), 1), 4),
            phase=ConsolidationPhase.REM,
        )]

    @property
    def pending_fragments(self) -> int:
        return len(self._fragments)

    @property
    def consolidated_count(self) -> int:
        return len(self._consolidated)

    def stats(self) -> dict:
        return {
            "pending_fragments": len(self._fragments),
            "consolidated_memories": len(self._consolidated),
            "cycles": self._cycle_count,
            "mean_free_energy": round(
                sum(m.free_energy for m in self._consolidated) / max(len(self._consolidated), 1), 6
            ),
        }


def _compute_free_energy(fragments: list[MemoryFragment], temperature: float) -> float:
    """Compute variational free energy for a set of fragments.

    F = E - T*S where E is energy (inverse salience dispersion) and
    S is entropy (diversity of sources/valences).
    """
    if not fragments:
        return float("inf")

    n = len(fragments)
    mean_salience = sum(f.salience for f in fragments) / n
    variance = sum((f.salience - mean_salience) ** 2 for f in fragments) / max(n - 1, 1)
    energy = variance + (1.0 - mean_salience)

    # Entropy: diversity of sources and emotional valences
    sources = list({f.source for f in fragments})
    valences = [f.emotional_valence for f in fragments]
    valence_var = sum((v - sum(valences) / n) ** 2 for v in valences) / max(n - 1, 1)
    entropy = math.log(max(len(sources), 1) + 1) + math.log(valence_var + 1)

    return energy - temperature * entropy


def _cluster_by_salience(
    frags: list[MemoryFragment],
    threshold: float,
) -> list[list[MemoryFragment]]:
    """Simple clustering by salience similarity."""
    if not frags:
        return []
    sorted_frags = sorted(frags, key=lambda f: f.salience, reverse=True)
    clusters: list[list[MemoryFragment]] = []
    current: list[MemoryFragment] = [sorted_frags[0]]

    for frag in sorted_frags[1:]:
        if abs(frag.salience - current[-1].salience) <= threshold:
            current.append(frag)
        else:
            clusters.append(current)
            current = [frag]
    clusters.append(current)
    return clusters


def _sample_subset(frags: list[MemoryFragment], size: int) -> list[MemoryFragment]:
    """Sample a weighted subset favoring high-salience fragments."""
    if len(frags) <= size:
        return list(frags)

    weights = [f.salience + f.novelty * 0.5 for f in frags]
    total = sum(weights)
    if total == 0:
        return frags[:size]

    probs = [w / total for w in weights]
    selected: set[int] = set()
    import random
    while len(selected) < min(size, len(frags)):
        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                selected.add(i)
                break
    return [frags[i] for i in selected]
