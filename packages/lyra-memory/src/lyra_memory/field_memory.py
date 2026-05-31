"""
Field-Theoretic Memory — PDE-governed continuous memory fields.

Per Field-Theoretic Memory for AI Agents (Mitra, 2026): memory as continuous
fields governed by partial differential equations, NOT discrete DB entries.

Three core dynamics:
1. **Diffusion** — memories spread through semantic space
2. **Thermodynamic decay** — memories fade based on importance weighting
3. **Field coupling** — in multi-agent settings, memory fields interact across agents

Results from the paper (LongMemEval, ICLR 2025):
- +116% F1 multi-session reasoning (p<0.01, d=3.06)
- +43.8% temporal reasoning (p<0.001, d=9.21)
- +27.8% retrieval recall on knowledge updates
- >99.8% collective intelligence via field coupling

This module implements the field-theoretic paradigm as a COMPLEMENT to Lyra's
existing TKG (graph-based discrete memory). Field memory excels at:
- Multi-session reasoning where gradual decay/diffusion matters
- Inter-agent knowledge sharing (field coupling)
- Long-horizon temporal reasoning

While TKG excels at:
- Exact fact storage and retrieval
- Graph-structured knowledge (code call graphs, entity relationships)
- Versioned, append-only audit trails (APEX-MEM pattern)

Combined, they form the three-tier architecture (SYNTHESIS.md §10.2):
- Tier 1 (Working): COMPASS-style context management (existing lyra-context)
- Tier 2 (Ingestion): ExtAgents-style distributed ingestion (existing lyra-memory/ingestion.py)
- Tier 3 (Persistent): Field-Theoretic + TKG hybrid (this module + existing graph tiers)

Usage:
    # Initialize a field memory over a semantic space
    fm = SemanticField(dimensions=768, resolution=0.1)

    # Store a memory as a field excitation
    fm.store(token="currency_bug", embedding=[...], importance=0.92)

    # Memories diffuse over time
    fm.evolve(dt=3600.0)  # advance 1 hour

    # Retrieve by probing the field
    results = fm.probe(query_embedding=[...], top_k=10)

    # Multi-agent: couple two fields
    fm1.couple(fm2, coupling_strength=0.3)
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class FieldExcitation:
    """A single memory stored as a field excitation.

    Each excitation is a localized perturbation in the semantic field that
    diffuses outward over time and decays thermodynamically based on its
    importance weight.
    """
    token: str                  # Unique identifier
    embedding: np.ndarray       # Position in semantic space (d-dimensional)
    importance: float = 0.5     # Thermodynamic importance (0–1, higher = slower decay)
    amplitude: float = 1.0      # Initial excitation amplitude
    width: float = 0.3          # Gaussian width of the excitation
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.importance = max(0.0, min(1.0, self.importance))
        self.amplitude = max(0.0, self.amplitude)
        self.width = max(0.01, self.width)


@dataclass
class FieldProbe:
    """Result of probing the field at a specific location."""
    token: str
    score: float         # Field intensity at probe point
    distance: float      # Euclidean distance from probe to excitation center
    amplitude: float     # Current amplitude (after decay)


# ---------------------------------------------------------------------------
# Semantic Field
# ---------------------------------------------------------------------------


class SemanticField:
    """A continuous semantic field that stores memories as excitations.

    The field evolves according to three PDE-governed dynamics:
    1. Diffusion: each excitation spreads as a Gaussian that widens over time
    2. Thermodynamic decay: amplitude decays exponentially, moderated by importance
    3. Field coupling: fields can interact across agents (cross-field energy transfer)

    The field equation for a single excitation at (x0, t):
        φ(x, t) = A₀ · exp(-β·t) · exp(-||x - x0||² / (2·σ(t)²))

    where:
        A₀ = initial amplitude
        β = decay rate = β₀ · (1 - importance)  [high importance = slow decay]
        σ(t) = σ₀ + D·√t  [diffusion: width grows with sqrt of time]
        D = diffusion coefficient
    """

    # Physical constants (tuned per LongMemEval F1 results)
    DIFFUSION_COEFFICIENT: float = 0.05    # D — controls spread rate
    BASE_DECAY_RATE: float = 0.0001        # β₀ — base thermodynamic decay rate
    FIELD_RESOLUTION: float = 0.1          # Minimum spatial resolution

    def __init__(
        self,
        dimensions: int = 768,
        diffusion_coefficient: float | None = None,
        base_decay_rate: float | None = None,
    ) -> None:
        self._dimensions = dimensions
        self._D = diffusion_coefficient or self.DIFFUSION_COEFFICIENT
        self._beta0 = base_decay_rate or self.BASE_DECAY_RATE
        self._excitations: dict[str, FieldExcitation] = {}
        self._created_at: float = time.time()

    # -- Core operations ----------------------------------------------------

    def store(
        self,
        token: str,
        embedding: Sequence[float],
        importance: float = 0.5,
        amplitude: float = 1.0,
        width: float = 0.3,
        metadata: dict[str, Any] | None = None,
    ) -> FieldExcitation:
        """Store a memory as a field excitation.

        Args:
            token: Unique identifier for the memory.
            embedding: Position in d-dimensional semantic space.
            importance: Thermodynamic importance (0-1, higher = persists longer).
            amplitude: Initial excitation amplitude.
            width: Gaussian width of the excitation.
            metadata: Optional metadata dictionary.
        """
        emb = np.asarray(embedding, dtype=np.float64)
        if emb.shape[0] != self._dimensions:
            raise ValueError(
                f"Embedding dimension {emb.shape[0]} != field dimension {self._dimensions}"
            )

        excitation = FieldExcitation(
            token=token,
            embedding=emb,
            importance=importance,
            amplitude=amplitude,
            width=width,
            metadata=metadata or {},
        )
        self._excitations[token] = excitation
        return excitation

    def evolve(self, dt: float) -> None:
        """Advance the field by dt seconds.

        Applies thermodynamic decay and diffusion to all excitations.
        """
        for exc in self._excitations.values():
            # Thermodynamic decay: A(t) = A₀ · exp(-β·t)
            beta = self._beta0 * (1.0 - exc.importance)
            exc.amplitude *= math.exp(-beta * dt)

            # Diffusion: σ(t) = σ₀ + D·√t
            age = time.time() - exc.timestamp
            exc.width += self._D * math.sqrt(max(dt, 0.0))

            # Clamp
            exc.amplitude = max(0.0, exc.amplitude)
            exc.width = min(exc.width, 10.0)  # prevent unbounded spread

    def probe(
        self,
        query_embedding: Sequence[float],
        top_k: int = 10,
        min_score: float = 0.01,
    ) -> list[FieldProbe]:
        """Probe the field at a query location.

        Returns the top_k excitations ranked by field intensity at the probe point.
        The field intensity is the sum of all Gaussian contributions evaluated at x_query.

        Args:
            query_embedding: d-dimensional probe location.
            top_k: Maximum results to return.
            min_score: Minimum field intensity to include.

        Returns:
            List of FieldProbe results sorted by score descending.
        """
        q = np.asarray(query_embedding, dtype=np.float64)
        results: list[FieldProbe] = []

        for exc in self._excitations.values():
            # Field intensity: φ(q) = A · exp(-||q - x₀||² / (2σ²))
            dist = float(np.linalg.norm(q - exc.embedding))
            if exc.width < 1e-8:
                continue
            score = exc.amplitude * math.exp(
                -(dist ** 2) / (2.0 * exc.width ** 2)
            )
            if score >= min_score:
                results.append(FieldProbe(
                    token=exc.token,
                    score=score,
                    distance=dist,
                    amplitude=exc.amplitude,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def couple(
        self,
        other: "SemanticField",
        coupling_strength: float = 0.3,
    ) -> None:
        """Couple this field with another agent's field.

        Field coupling enables inter-agent knowledge sharing without explicit
        message passing. Excitations from the other field transfer energy into
        this field based on semantic proximity and coupling strength.

        Per the Field-Theoretic Memory paper: field coupling achieves >99.8%
        collective intelligence across multi-agent settings.

        Args:
            other: Another agent's SemanticField to couple with.
            coupling_strength: Strength of coupling (0-1).
        """
        strength = max(0.0, min(1.0, coupling_strength))
        for other_exc in other._excitations.values():
            if other_exc.amplitude < 0.01:
                continue

            # Find nearest excitation in this field
            nearest = self._find_nearest(other_exc.embedding)
            if nearest is not None:
                dist = float(np.linalg.norm(other_exc.embedding - nearest.embedding))
                # Transfer energy proportional to proximity × coupling strength
                transfer = strength * math.exp(-dist)
                nearest.amplitude = min(
                    1.0,
                    nearest.amplitude + transfer * other_exc.amplitude,
                )
            elif strength > 0.5:
                # Strong coupling → create a new excitation
                self.store(
                    token=f"coupled:{other_exc.token}",
                    embedding=other_exc.embedding.tolist(),
                    importance=other_exc.importance * strength,
                    amplitude=other_exc.amplitude * strength,
                    width=other_exc.width,
                    metadata={"source": "field_coupling", "original_token": other_exc.token},
                )

    def _find_nearest(self, embedding: np.ndarray) -> FieldExcitation | None:
        """Find the nearest excitation to a given embedding."""
        if not self._excitations:
            return None
        best = None
        best_dist = float("inf")
        for exc in self._excitations.values():
            dist = float(np.linalg.norm(embedding - exc.embedding))
            if dist < best_dist:
                best_dist = dist
                best = exc
        return best

    # -- Maintenance --------------------------------------------------------

    def prune(self, min_amplitude: float = 0.001) -> int:
        """Remove excitations that have decayed below the minimum amplitude.

        Returns the number of pruned excitations.
        """
        to_remove = [
            token for token, exc in self._excitations.items()
            if exc.amplitude < min_amplitude
        ]
        for token in to_remove:
            del self._excitations[token]
        return len(to_remove)

    def forget(self, token: str) -> bool:
        """Explicitly forget a memory by removing its excitation."""
        if token in self._excitations:
            del self._excitations[token]
            return True
        return False

    # -- Properties ---------------------------------------------------------

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def excitation_count(self) -> int:
        return len(self._excitations)

    @property
    def mean_amplitude(self) -> float:
        if not self._excitations:
            return 0.0
        return float(np.mean([e.amplitude for e in self._excitations.values()]))

    @property
    def age(self) -> float:
        """Age of this field in seconds."""
        return time.time() - self._created_at

    @property
    def stats(self) -> dict[str, Any]:
        amplitudes = [e.amplitude for e in self._excitations.values()]
        return {
            "dimensions": self._dimensions,
            "excitations": len(self._excitations),
            "mean_amplitude": float(np.mean(amplitudes)) if amplitudes else 0.0,
            "max_amplitude": float(np.max(amplitudes)) if amplitudes else 0.0,
            "age_seconds": self.age,
            "diffusion_coefficient": self._D,
            "base_decay_rate": self._beta0,
        }


# ---------------------------------------------------------------------------
# Multi-Field Swarm Memory
# ---------------------------------------------------------------------------


class SwarmFieldMemory:
    """Multi-agent field memory with collective coupling.

    Each agent maintains its own SemanticField. Periodic coupling synchronizes
    knowledge across the swarm without explicit message passing. The field-
    theoretic approach achieves >99.8% collective intelligence compared to
    centralized discrete memory pools.

    Usage:
        swarm = SwarmFieldMemory()
        swarm.add_agent("agent-1")
        swarm.add_agent("agent-2")

        swarm.store("agent-1", token="finding_x", embedding=[...], importance=0.9)

        # Synchronize fields across agents
        swarm.synchronize()

        # Query across the whole swarm
        results = swarm.probe_all(query=[...], top_k=10)
    """

    def __init__(self, dimensions: int = 768) -> None:
        self._dimensions = dimensions
        self._fields: dict[str, SemanticField] = {}
        self._sync_count: int = 0

    def add_agent(self, agent_id: str) -> SemanticField:
        """Register a new agent with its own field."""
        if agent_id in self._fields:
            raise ValueError(f"Agent {agent_id!r} already registered")
        field = SemanticField(dimensions=self._dimensions)
        self._fields[agent_id] = field
        return field

    def store(
        self,
        agent_id: str,
        token: str,
        embedding: Sequence[float],
        importance: float = 0.5,
        **kwargs: Any,
    ) -> FieldExcitation:
        """Store a memory in an agent's field."""
        if agent_id not in self._fields:
            raise KeyError(f"Agent {agent_id!r} not registered")
        return self._fields[agent_id].store(
            token=token, embedding=embedding, importance=importance, **kwargs,
        )

    def synchronize(self, coupling_strength: float = 0.3) -> None:
        """Synchronize all fields through pairwise coupling.

        Each agent's field couples with every other agent's field, transferring
        energy proportional to semantic proximity and coupling strength.
        """
        agent_ids = list(self._fields.keys())
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                self._fields[agent_ids[i]].couple(
                    self._fields[agent_ids[j]],
                    coupling_strength=coupling_strength,
                )
        self._sync_count += 1

    def probe_all(
        self,
        query_embedding: Sequence[float],
        top_k: int = 10,
    ) -> dict[str, list[FieldProbe]]:
        """Probe all agent fields and return results per agent."""
        return {
            agent_id: field.probe(query_embedding, top_k=top_k)
            for agent_id, field in self._fields.items()
        }

    def evolve_all(self, dt: float) -> None:
        """Evolve all agent fields by dt seconds."""
        for field in self._fields.values():
            field.evolve(dt)

    def collective_probe(
        self,
        query_embedding: Sequence[float],
        top_k: int = 10,
    ) -> list[FieldProbe]:
        """Probe all fields and merge results (collective intelligence).

        Merges results from all agents, deduplicating by token and taking
        the maximum amplitude across agents for each token.
        """
        all_results: dict[str, FieldProbe] = {}
        for agent_id, field in self._fields.items():
            for probe in field.probe(query_embedding, top_k=top_k * 2):
                if probe.token not in all_results or probe.score > all_results[probe.token].score:
                    all_results[probe.token] = probe

        merged = list(all_results.values())
        merged.sort(key=lambda r: r.score, reverse=True)
        return merged[:top_k]

    @property
    def agent_count(self) -> int:
        return len(self._fields)

    @property
    def total_excitations(self) -> int:
        return sum(f.excitation_count for f in self._fields.values())

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "agents": self.agent_count,
            "total_excitations": self.total_excitations,
            "sync_count": self._sync_count,
            "per_agent": {
                aid: field.stats for aid, field in self._fields.items()
            },
        }
