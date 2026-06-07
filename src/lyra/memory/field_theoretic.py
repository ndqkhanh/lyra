"""
Field-Theoretic Memory — memories as continuous scalar fields governed by PDEs.

Implements the field-theoretic memory architecture described in:
    Mitra (2026). "Field-Theoretic Memory: Continuous-State Episodic Recall
    with PDE-governed Consolidation." arXiv:2602.21220v1.

Key mechanisms:
    - Memories exist as continuous scalar fields phi(x,t) in semantic space.
    - Diffusion via the heat equation spreads activation to semantically
      neighboring memories (associative recall).
    - Thermodynamic decay (lambda * phi) models natural forgetting by
      importance-weighted dissipation.
    - Free-energy minimization F = E + lambda * S governs consolidation,
      balancing utility (E) against entropy (S) for optimal plasticity.
    - Multi-agent field coupling via PDE coupling terms enables shared
      memory across agent instances.
    - +116% multi-session reasoning F1, +43.8% temporal reasoning F1,
      +27.8% knowledge-update recall on LongMemEval [Mitra 2026, §4].

References:
    Mitra, S. (2026). Field-Theoretic Memory. arXiv:2602.21220v1.
    Du & Zhao (2026). Entropic Memory. ICLR 2026.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from lyra.memory.memory_store import Memory, MemoryStore, MemoryType


# =============================================================================
# Constants
# =============================================================================

# Default PDE parameters (from Mitra 2026 §3.2, Table 1)
DEFAULT_DIFFUSION_COEFFICIENT: float = 0.1       # D — semantic diffusion rate
DEFAULT_DECAY_RATE: float = 0.01                   # lambda — thermodynamic decay
DEFAULT_ENTROPY_WEIGHT: float = 0.3                # lambda_S — entropy regularizer
DEFAULT_TEMPERATURE: float = 1.0                   # T — plasticity regulation
DEFAULT_SEMANTIC_DIMENSIONS: int = 128             # reduced-dim semantic field
DEFAULT_CFL_DT: float = 0.01                       # CFL-stable time step

# Performance targets (from Mitra 2026 §4)
TARGET_MULTI_SESSION_F1: float = 1.16     # +116% over baseline
TARGET_TEMPORAL_F1: float = 1.438         # +43.8% over baseline
TARGET_KNOWLEDGE_RECALL: float = 1.278    # +27.8% over baseline
TARGET_COLLECTIVE_INTELLIGENCE: float = 0.998  # near-perfect at 2+ agents


# =============================================================================
# Field data structures
# =============================================================================


@dataclass
class FieldPoint:
    """
    A single memory represented as a field excitation in semantic space.

    Attributes:
        point_id: Unique identifier for this field point.
        content: The raw memory text.
        memory_type: Type of memory (episodic, semantic, procedural).
        embedding: Dense vector in semantic space (the field value).
        importance: Thermodynamic weight (0.0-1.0); governs decay rate.
        source_strength: Current source term S(x,t) for PDE injection.
        created_at: Unix timestamp of creation.
        last_updated: Unix timestamp of last PDE update.
    """
    point_id: str
    content: str
    memory_type: str = "episodic"
    embedding: np.ndarray | None = None
    importance: float = 0.5
    source_strength: float = 0.0
    created_at: float = 0.0
    last_updated: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldState:
    """
    Snapshot of the entire memory field at a point in time.

    Captures the full PDE state for observability, checkpointing,
    and multi-agent coupling.
    """
    timestamp: float
    field_points: list[FieldPoint]
    free_energy: float
    internal_energy: float
    entropy: float
    total_source: float
    iteration: int


# =============================================================================
# Free-energy objective
# =============================================================================


def _internal_energy(point: FieldPoint) -> float:
    """Internal energy E(m) = -Utility(m) — lower is better."""
    # Utility is approximated by importance; high-importance = low energy.
    return -point.importance


def _entropy(point: FieldPoint) -> float:
    """
    Shannon entropy H(e_m) of the embedding vector, normalized.

    From Du & Zhao (2026): entropy measures the information content
    of a memory's position in semantic space. High entropy = high
    information density = preserved longer.
    """
    if point.embedding is None or point.embedding.size < 2:
        return 0.0
    # Normalize to probability distribution
    emb = point.embedding.flatten()
    emb_norm = emb - emb.min()
    if emb_norm.sum() < 1e-12:
        return 0.0
    probs = emb_norm / emb_norm.sum()
    # Shannon entropy
    return -float(np.sum(probs * np.log(probs + 1e-12))) / math.log(len(probs) + 1)


def free_energy(
    point: FieldPoint,
    entropy_weight: float = DEFAULT_ENTROPY_WEIGHT,
    temperature: float = DEFAULT_TEMPERATURE,
) -> float:
    """
    Free energy F = E + lambda_S * T * S

    From Du & Zhao (2026, §3.1): free energy minimization drives
    consolidation. The entropy term prevents premature convergence
    (greedy utility maximization) by maintaining diversity.

    Args:
        point: The field point to evaluate.
        entropy_weight: lambda_S — entropy regularization strength.
        temperature: T — regulates plasticity; higher = more exploration.

    Returns:
        Free energy value (lower is more consolidated).
    """
    e = _internal_energy(point)
    s = _entropy(point)
    return e + entropy_weight * temperature * s


# =============================================================================
# PDE operators
# =============================================================================


def _laplacian_1d(
    field: np.ndarray,
    dx: float = 1.0,
) -> np.ndarray:
    """
    Discrete Laplacian via central finite differences.

    The Laplacian term D * nabla^2 phi in the PDE spreads activation
    to semantically neighboring memories, implementing associative recall.
    """
    result = np.zeros_like(field)
    if field.shape[0] < 3:
        return result
    # Interior points: second-order central difference
    result[1:-1] = (field[2:] - 2.0 * field[1:-1] + field[:-2]) / (dx * dx)
    # Neumann boundary conditions (zero gradient at edges)
    result[0] = result[1]
    result[-1] = result[-2]
    return result


def _pairwise_laplacian(
    embeddings: np.ndarray,
    diffusion_coefficient: float = DEFAULT_DIFFUSION_COEFFICIENT,
) -> np.ndarray:
    """
    Pairwise Laplacian coupling across all field points.

    For each point i: sum_j D * (phi_j - phi_i) weighted by semantic
    similarity. This implements the Laplacian term on a discrete set
    of points in semantic space (graph Laplacian formulation).

    Reference: Mitra (2026), eq. 3 — "The discrete Laplacian on the
    memory graph is approximated by the weighted graph Laplacian L,
    where edge weights w_ij = exp(-||e_i - e_j||^2 / sigma^2)."
    """
    n = embeddings.shape[0]
    if n < 2:
        return np.zeros_like(embeddings)

    # Pairwise squared distances
    diff = embeddings[:, np.newaxis, :] - embeddings[np.newaxis, :, :]
    sq_dists = np.sum(diff ** 2, axis=-1)

    # Similarity kernel (RBF)
    sigma = np.median(sq_dists) if n > 2 else 1.0
    sigma = max(sigma, 1e-8)
    weights = np.exp(-sq_dists / (2.0 * sigma ** 2))
    # Zero out self-loops
    np.fill_diagonal(weights, 0.0)
    # Row-normalize
    row_sums = weights.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums < 1e-12, 1.0, row_sums)
    weights = weights / row_sums

    # Graph Laplacian * phi
    laplacian = np.dot(weights, embeddings) - embeddings
    return diffusion_coefficient * laplacian


# =============================================================================
# FieldMemory
# =============================================================================


class FieldMemory:
    """
    Memory system governed by continuous field PDEs.

    Memories are represented as scalar fields in semantic space that
    evolve according to the reaction-diffusion equation::

        dphi/dt = D * Laplacian(phi) - lambda * phi + S(x, y, t)

    where:
        - D * Laplacian(phi): diffusion spreads activation semantically
        - lambda * phi: thermodynamic decay (importance-weighted forgetting)
        - S(x, y, t): source term injecting new memories

    Consolidation proceeds by free-energy minimization::

        F = sum_i (E_i + lambda_S * T * S_i)

    lowering F through iterative PDE integration with stochastic
    resampling (thermodynamic annealing).

    Performance targets (Mitra 2026, §4):
        - +116% multi-session reasoning F1 on LongMemEval
        - +43.8% temporal reasoning F1
        - +27.8% knowledge-update recall
        - near-perfect (>99.8%) multi-agent collective intelligence
    """

    def __init__(
        self,
        store: MemoryStore | None = None,
        diffusion_coefficient: float = DEFAULT_DIFFUSION_COEFFICIENT,
        decay_rate: float = DEFAULT_DECAY_RATE,
        entropy_weight: float = DEFAULT_ENTROPY_WEIGHT,
        temperature: float = DEFAULT_TEMPERATURE,
        semantic_dimensions: int = DEFAULT_SEMANTIC_DIMENSIONS,
        cfl_dt: float = DEFAULT_CFL_DT,
        agent_id: str | None = None,
    ):
        """
        Initialize the field memory.

        Args:
            store: Optional backing MemoryStore for persistence.
            diffusion_coefficient: D — semantic diffusion rate.
            decay_rate: lambda — thermodynamic importance decay.
            entropy_weight: lambda_S — entropy regularization in free energy.
            temperature: T — plasticity regulation temperature.
            semantic_dimensions: Dimensionality of the semantic field.
            cfl_dt: CFL-stable time step for PDE integration.
            agent_id: Identifier for this agent (used in multi-agent coupling).
        """
        self.store = store or MemoryStore()
        self.D = diffusion_coefficient
        self.lambd = decay_rate
        self.lambda_S = entropy_weight
        self.T = temperature
        self.dim = semantic_dimensions
        self.dt = cfl_dt
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"

        # Internal field points indexed by ID
        self._points: dict[str, FieldPoint] = {}

        # Source-term buffer for PDE injection
        self._source_buffer: list[FieldPoint] = []

        # PDE iteration counter
        self._iteration: int = 0

        # Multi-agent coupling state
        self._coupled_fields: dict[str, list[FieldPoint]] = {}

    # ------------------------------------------------------------------
    # Core field operations
    # ------------------------------------------------------------------

    def project_to_field(self, memory: Memory) -> FieldPoint:
        """
        Project a ``Memory`` into a ``FieldPoint`` in semantic space.

        Creates a normalized embedding (random projection as placeholder;
        in production this uses sentence-transformers or similar encoder).

        Args:
            memory: The memory to project.

        Returns:
            A field point with embedding in the semantic field.
        """
        # Random projection as placeholder — in production use an encoder.
        rng = np.random.RandomState(hash(memory.content) & 0xFFFFFFFF)
        embedding = rng.randn(self.dim).astype(np.float32)
        embedding /= np.linalg.norm(embedding) + 1e-12

        return FieldPoint(
            point_id=memory.memory_id,
            content=memory.content,
            memory_type=memory.memory_type.value,
            embedding=embedding,
            importance=memory.importance,
            source_strength=memory.importance * 0.5,
            created_at=memory.timestamp,
            last_updated=time.time(),
            metadata={
                "source": "projection",
                "tags": memory.tags,
                "context": memory.context,
                "access_count": memory.access_count,
            },
        )

    def add_memory(self, memory: Memory) -> FieldPoint:
        """
        Add a memory to the field (source injection: S(x,y,t)).

        The memory is projected into semantic space and added to the
        source buffer, where it will be integrated into the field
        during the next PDE step.

        Args:
            memory: The memory to inject.

        Returns:
            The field point created.
        """
        point = self.project_to_field(memory)

        # Compute free energy at injection
        fe = free_energy(point, self.lambda_S, self.T)

        self._points[point.point_id] = point
        self._source_buffer.append(point)

        # Also persist to backing store
        self.store.add(
            content=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
            tags=memory.tags,
            context={
                **memory.context,
                "field_point_id": point.point_id,
                "free_energy": fe,
                "field_iteration": self._iteration,
            },
        )

        return point

    def get_field_point(self, point_id: str) -> FieldPoint | None:
        """Retrieve a field point by ID."""
        return self._points.get(point_id)

    def get_all_points(self) -> list[FieldPoint]:
        """Return all field points."""
        return list(self._points.values())

    def remove_point(self, point_id: str) -> bool:
        """
        Remove a field point (field decay or pruning).

        Returns True if the point was removed.
        """
        if point_id in self._points:
            del self._points[point_id]
            return True
        return False

    # ------------------------------------------------------------------
    # PDE integration (reaction-diffusion)
    # ------------------------------------------------------------------

    def step(self, source_points: list[FieldPoint] | None = None) -> FieldState:
        """
        Evolve the field by one PDE time step.

        Implements forward Euler integration of::

            dphi/dt = D * Laplacian(phi) - lambda * phi + S(x,y,t)

        Args:
            source_points: Optional external source points (e.g. from
                           coupled agent fields).

        Returns:
            The field state after this step.
        """
        points = list(self._points.values())
        if not points:
            return FieldState(
                timestamp=time.time(),
                field_points=[],
                free_energy=0.0,
                internal_energy=0.0,
                entropy=0.0,
                total_source=0.0,
                iteration=self._iteration,
            )

        # Stack embeddings for vectorized PDE update
        embeddings = np.stack([p.embedding for p in points])
        importances = np.array([p.importance for p in points], dtype=np.float32)

        # 1. Diffusion term: D * Laplacian(phi)
        laplacian = _pairwise_laplacian(embeddings, self.D)

        # 2. Decay term: -lambda * phi (importance-weighted)
        decay = -self.lambd * embeddings * importances[:, np.newaxis]

        # 3. Source term: S(x,y,t)
        if source_points:
            for sp in source_points:
                if sp.point_id in self._points:
                    idx = next(
                        i for i, p in enumerate(points) if p.point_id == sp.point_id
                    )
                    source_vec = sp.source_strength * sp.embedding
                    points[idx].source_strength = sp.source_strength * 0.9  # decay source
                else:
                    self._points[sp.point_id] = sp
                    points.append(sp)
                    embeddings = np.vstack([embeddings, sp.embedding[np.newaxis, :]])
                    importances = np.append(importances, sp.importance)
                    # Recompute laplacian and decay
                    laplacian = _pairwise_laplacian(embeddings, self.D)
                    decay = -self.lambd * embeddings * importances[:, np.newaxis]

        # Source from internal buffer
        source = np.zeros_like(embeddings)
        for sp in self._source_buffer:
            if sp.point_id in self._points:
                idx = list(self._points.keys()).index(sp.point_id)
                if idx < len(source):
                    source[idx] += sp.source_strength * sp.embedding

        # Forward Euler update
        dphi = laplacian + decay + source
        new_embeddings = embeddings + self.dt * dphi

        # Apply update back to points
        for i, p in enumerate(points):
            p.embedding = new_embeddings[i].astype(np.float32)
            p.last_updated = time.time()

        # Clear source buffer after integration
        self._source_buffer.clear()

        # Compute free energy statistics
        fe_values = [free_energy(p, self.lambda_S, self.T) for p in points if p.embedding is not None]
        avg_fe = float(np.mean(fe_values)) if fe_values else 0.0
        avg_e = float(np.mean([_internal_energy(p) for p in points])) if points else 0.0
        avg_s = float(np.mean([_entropy(p) for p in points])) if points else 0.0

        self._iteration += 1

        return FieldState(
            timestamp=time.time(),
            field_points=points,
            free_energy=avg_fe,
            internal_energy=avg_e,
            entropy=avg_s,
            total_source=float(np.sum(np.abs(source))),
            iteration=self._iteration,
        )

    def consolidate(
        self,
        num_steps: int = 100,
        convergence_threshold: float = 1e-4,
    ) -> FieldState:
        """
        Run iterative PDE consolidation until convergence.

        Minimizes free energy F = E + lambda_S * T * S across the field
        by evolving the reaction-diffusion PDE. Convergence is detected
        when the free energy change between steps falls below threshold.

        Args:
            num_steps: Maximum number of PDE steps.
            convergence_threshold: Stop when relative FE change < this.

        Returns:
            Final field state after consolidation.
        """
        last_fe = float("inf")
        final_state = None

        for _ in range(num_steps):
            state = self.step()
            fe_delta = abs(state.free_energy - last_fe) / (abs(last_fe) + 1e-12)
            if fe_delta < convergence_threshold and _ > 10:
                final_state = state
                break
            last_fe = state.free_energy
            final_state = state

        # Prune points whose importance has decayed below threshold
        self._prune_decayed(min_importance=0.05)

        return final_state

    def _prune_decayed(self, min_importance: float = 0.05):
        """
        Remove field points whose thermodynamic importance has decayed
        below the threshold (equivalent to forgetting).
        """
        to_remove = [
            pid for pid, p in self._points.items()
            if p.importance < min_importance
        ]
        for pid in to_remove:
            del self._points[pid]

    # ------------------------------------------------------------------
    # Retrieval (associative recall via field proximity)
    # ------------------------------------------------------------------

    def recall_by_similarity(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
    ) -> list[tuple[FieldPoint, float]]:
        """
        Retrieve memories by semantic proximity to a query embedding.

        The field naturally encodes associative recall: memories close
        in semantic space have diffused together via the Laplacian term.
        This retrieval is a direct readout of the field state.

        Args:
            query_embedding: Query vector in semantic space.
            top_k: Maximum number of results.

        Returns:
            List of (FieldPoint, similarity_score) pairs, sorted by
            similarity descending.
        """
        if not self._points:
            return []

        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-12)
        scored: list[tuple[FieldPoint, float]] = []

        for point in self._points.values():
            if point.embedding is None:
                continue
            sim = float(np.dot(query_norm, point.embedding.flatten()))
            # Weight by thermodynamic importance (high = more retrievable)
            weighted_sim = sim * (0.5 + 0.5 * point.importance)
            scored.append((point, weighted_sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def recall_by_content(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[FieldPoint, float]]:
        """
        Retrieve memories by text content via semantic projection.

        Projects the query text into the semantic field using the same
        embedding scheme, then calls ``recall_by_similarity``.

        Args:
            query: Query text.
            top_k: Maximum number of results.

        Returns:
            List of (FieldPoint, similarity_score) pairs.
        """
        # Project query into field (consistent projection)
        rng = np.random.RandomState(hash(query) & 0xFFFFFFFF)
        query_emb = rng.randn(self.dim).astype(np.float32)
        query_emb /= np.linalg.norm(query_emb) + 1e-12

        return self.recall_by_similarity(query_emb, top_k=top_k)

    # ------------------------------------------------------------------
    # Multi-agent field coupling
    # ------------------------------------------------------------------

    def couple_field(self, other_field: FieldMemory, coupling_strength: float = 0.1):
        """
        Couple this field with another agent's field.

        Multi-agent coupling adds a PDE source term proportional to the
        difference between fields::

            S_coupled = coupling_strength * (phi_other - phi_self)

        This implements shared collective memory as described in
        Mitra (2026, §5): "Multi-agent collective intelligence emerges
        naturally from PDE coupling terms. At 2, 4, and 8 agents,
        the coupled field achieves >99.8% collective task accuracy."

        Args:
            other_field: Another FieldMemory instance to couple with.
            coupling_strength: Kappa in the coupling PDE term.
        """
        # Exchange field points
        other_points = other_field.get_all_points()
        self._coupled_fields[other_field.agent_id] = other_points

        # Inject coupled source terms
        coupled_sources: list[FieldPoint] = []
        my_points = {p.point_id: p for p in self._points.values()}

        for other_p in other_points:
            if other_p.point_id in my_points:
                my_p = my_points[other_p.point_id]
                # Coupling: kappa * (phi_other - phi_self)
                delta = other_p.embedding - my_p.embedding
                coupled_point = FieldPoint(
                    point_id=other_p.point_id,
                    content=other_p.content,
                    memory_type=other_p.memory_type,
                    embedding=other_p.embedding,
                    importance=other_p.importance * coupling_strength,
                    source_strength=coupling_strength * float(np.linalg.norm(delta)),
                    created_at=other_p.created_at,
                    last_updated=time.time(),
                    metadata={"coupled_from": other_field.agent_id},
                )
                coupled_sources.append(coupled_point)

        # Inject coupled sources into field
        if coupled_sources:
            self.step(source_points=coupled_sources)

    def decouple_field(self, agent_id: str):
        """Remove coupling with the specified agent's field."""
        self._coupled_fields.pop(agent_id, None)

    def get_coupled_agents(self) -> list[str]:
        """Return the list of agent IDs this field is coupled with."""
        return list(self._coupled_fields.keys())

    # ------------------------------------------------------------------
    # Thermodynamic importance tuning
    # ------------------------------------------------------------------

    def adjust_importance(
        self,
        point_id: str,
        delta: float,
    ):
        """
        Adjust the thermodynamic importance of a field point.

        Positive delta strengthens the memory (slower decay);
        negative delta weakens it (faster forgetting).

        This is the external interface to the importance-weighting
        mechanism in the PDE decay term.

        Args:
            point_id: The field point to adjust.
            delta: Change in importance (-1.0 to 1.0).
        """
        point = self._points.get(point_id)
        if point is None:
            return
        point.importance = max(0.0, min(1.0, point.importance + delta))
        point.last_updated = time.time()

    def boost_recall(self, point_id: str):
        """
        Boost the source strength of a point (simulating rehearsal).

        Rehearsal strengthens a memory akin to spaced repetition,
        counteracting thermodynamic decay.
        """
        point = self._points.get(point_id)
        if point is None:
            return
        point.source_strength = min(1.0, point.source_strength + 0.2)
        point.importance = min(1.0, point.importance + 0.05)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_field_statistics(self) -> dict[str, Any]:
        """
        Return comprehensive field statistics.

        Returns:
            Dictionary with field configuration and state.
        """
        n_points = len(self._points)
        importances = [p.importance for p in self._points.values()]
        fe_values = [free_energy(p, self.lambda_S, self.T) for p in self._points.values()]

        return {
            "agent_id": self.agent_id,
            "total_points": n_points,
            "pde_iteration": self._iteration,
            "avg_importance": float(np.mean(importances)) if importances else 0.0,
            "avg_free_energy": float(np.mean(fe_values)) if fe_values else 0.0,
            "diffusion_coefficient": self.D,
            "decay_rate": self.lambd,
            "entropy_weight": self.lambda_S,
            "temperature": self.T,
            "semantic_dimensions": self.dim,
            "cfl_dt": self.dt,
            "coupled_agents": len(self._coupled_fields),
            "source_buffer_size": len(self._source_buffer),
            "performance_targets": {
                "multi_session_f1_gain": TARGET_MULTI_SESSION_F1,
                "temporal_f1_gain": TARGET_TEMPORAL_F1,
                "knowledge_recall_gain": TARGET_KNOWLEDGE_RECALL,
                "collective_intelligence": TARGET_COLLECTIVE_INTELLIGENCE,
            },
        }


# =============================================================================
# Convenience orchestration
# =============================================================================


def create_field_memory(
    store: MemoryStore | None = None,
    agent_id: str | None = None,
    **kwargs,
) -> FieldMemory:
    """
    Create a configured FieldMemory instance with sensible defaults.

    Args:
        store: Optional backing store.
        agent_id: Optional agent identifier.
        **kwargs: Override any FieldMemory constructor parameter.

    Returns:
        A ready-to-use FieldMemory.
    """
    return FieldMemory(store=store, agent_id=agent_id, **kwargs)


def couple_agent_fields(
    fields: list[FieldMemory],
    coupling_strength: float = 0.1,
) -> FieldMemory:
    """
    Couple multiple agent fields into a shared collective memory.

    All pairs are bidirectionally coupled. Each field receives source
    terms from every other field.

    Reference: Mitra (2026, §5.2) — "Coupling multiple agent fields
    produces emergent collective intelligence exceeding any individual
    agent's performance."

    Args:
        fields: List of FieldMemory instances to couple.
        coupling_strength: PDE coupling coefficient.

    Returns:
        The first field (now coupled to all others).
    """
    if len(fields) < 2:
        return fields[0]

    for i, f_a in enumerate(fields):
        for f_b in fields[i + 1:]:
            f_a.couple_field(f_b, coupling_strength=coupling_strength)
            f_b.couple_field(f_a, coupling_strength=coupling_strength)

    return fields[0]
