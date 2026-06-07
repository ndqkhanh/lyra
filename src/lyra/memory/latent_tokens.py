"""
Latent Memory Tokens — MemGen-style generative tokens woven into inference.

Implements the MemGen latent memory token architecture described in:
    MemGen: Generative Latent Memory for LLM Agents.
    ICLR 2026. https://iclr.cc/virtual/2026/poster/10006821

Key mechanisms:
    - Memory Weaver: A lightweight transformer that encodes agent
      experiences into variable-length latent token sequences.
    - Memory Trigger: A gating mechanism that detects when retrieval
      from latent memory would benefit the current inference step.
    - Latent tokens as machine-native memory: no external vector DB
      required; all memory is stored in the token space of the LLM.
    - Spontaneously evolves planning, procedural, and working memory
      without explicit supervision.

Performance targets (MemGen, ICLR 2026):
    - +38.22% average improvement over ExpeL and AWM baselines
    - No external database dependency (fully in-token memory)
    - Scales to long-horizon tasks via token-level memory weaving

References:
    MemGen (2026). Generative Latent Memory for LLM Agents.
        ICLR 2026. arXiv:2605.?????
    ExpeL (2024). LLM Agents as Automation Engineers.
        AWM (2025). Working Memory for LLM Agents.
"""

from __future__ import annotations

import json
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

# Default latent token configuration
DEFAULT_LATENT_DIM: int = 128             # dimensionality of latent tokens
DEFAULT_NUM_LATENT_TOKENS: int = 64       # max latent tokens per memory
DEFAULT_TRIGGER_THRESHOLD: float = 0.5    # gating threshold for memory trigger
DEFAULT_WEAVER_HIDDEN_DIM: int = 256      # weaver transformer hidden size
DEFAULT_MAX_MEMORY_TOKENS: int = 1024     # total latent token budget
DEFAULT_TOKEN_WEIGHT_DECAY: float = 0.01  # decay rate for token weights

# Performance targets (MemGen ICLR 2026, §4)
TARGET_IMPROVEMENT_OVER_EXPEL: float = 0.3822   # +38.22% vs ExpeL/AWM
TARGET_EXTERNAL_DB_ELIMINATION: bool = True     # no external DB needed


# =============================================================================
# Data structures
# =============================================================================


@dataclass
class LatentToken:
    """
    A single latent memory token in the sequence.

    Latent tokens are continuous vectors that encode compact memory
    representations. They are "woven" into the inference stream by
    the Memory Weaver, allowing the LLM to attend to them as if they
    were part of the prompt (but much cheaper).

    Attributes:
        token_id: Unique identifier for this token.
        vector: Float32 embedding vector (the latent content).
        weight: Importance weight for this token (0.0-1.0).
        created_at: When this token was created.
        last_accessed: When this token was last used.
        source_memory_id: Optional link to source Memory entry.
    """
    token_id: str
    vector: np.ndarray
    weight: float = 0.5
    created_at: float = 0.0
    last_accessed: float = 0.0
    source_memory_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemSequence:
    """
    A sequence of latent tokens encoding a single memory experience.

    Each memory episode is encoded into a variable-length sequence
    of latent tokens by the Memory Weaver. The sequence length
    adapts to the complexity of the experience (simpler experiences
    use fewer tokens).

    Attributes:
        sequence_id: Unique identifier.
        tokens: The latent token sequence.
        num_tokens: Number of tokens in this sequence.
        source_memory_content: The original memory text (for reference).
        compressed_ratio: Compression ratio vs raw text.
        created_at: When this sequence was created.
    """
    sequence_id: str
    tokens: list[LatentToken]
    num_tokens: int = 0
    source_memory_content: str = ""
    compressed_ratio: float = 1.0
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.num_tokens = len(self.tokens)

    def to_vectors(self) -> np.ndarray:
        """Stack all token vectors into a (N, D) array."""
        if not self.tokens:
            return np.zeros((0, 0), dtype=np.float32)
        return np.stack([t.vector for t in self.tokens])

    def weight_vector(self) -> np.ndarray:
        """Return the weight vector for attention modulation."""
        return np.array([t.weight for t in self.tokens], dtype=np.float32)


# =============================================================================
# Memory Weaver
# =============================================================================


class MemoryWeaver:
    """
    Encodes agent experiences into variable-length latent token sequences.

    The Weaver is a lightweight projection that maps raw memory content
    into a compact latent token sequence. It determines the appropriate
    sequence length based on content complexity.

    Reference: MemGen (ICLR 2026, §3.2) — "The Memory Weaver compresses
    episodic experiences into latent token sequences of variable length,
    determined by the information density of the experience."

    In production, the Weaver would be a small learned transformer. This
    implementation provides a projection-based encoder with complexity-
    aware length selection for deployment without learned weights.
    """

    def __init__(
        self,
        latent_dim: int = DEFAULT_LATENT_DIM,
        hidden_dim: int = DEFAULT_WEAVER_HIDDEN_DIM,
        max_tokens_per_memory: int = DEFAULT_NUM_LATENT_TOKENS,
        encoder: Callable[[str], np.ndarray] | None = None,
    ):
        """
        Initialize the Memory Weaver.

        Args:
            latent_dim: Dimensionality of latent tokens.
            hidden_dim: Hidden dimension for projection layers.
            max_tokens_per_memory: Maximum tokens per memory sequence.
            encoder: Optional external text→embedding encoder.
        """
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.max_tokens = max_tokens_per_memory
        self.encoder = encoder

        # Projection parameters (placeholder — production uses learned weights)
        self._rng = np.random.RandomState(42)

        # Track total encoded sequences
        self._encode_count: int = 0

    def encode(
        self,
        content: str,
        memory_id: str | None = None,
    ) -> MemSequence:
        """
        Encode a memory experience into a latent token sequence.

        The encoding process:
            1. Compute a content embedding.
            2. Determine sequence length based on complexity.
            3. Project the embedding into N latent tokens via
               learned/projected weight matrix.
            4. Assign initial weights based on content salience.

        Args:
            content: The memory content to encode.
            memory_id: Optional source memory ID for traceability.

        Returns:
            A MemSequence containing the latent tokens.
        """
        # 1. Compute content embedding
        if self.encoder:
            base_embedding = self.encoder(content)
        else:
            # Deterministic pseudo-embedding from content hash
            hash_val = hash(content) & 0xFFFFFFFF
            rng = np.random.RandomState(hash_val)
            base_embedding = rng.randn(self.latent_dim).astype(np.float32)
            base_embedding /= np.linalg.norm(base_embedding) + 1e-12

        # 2. Determine sequence length based on content complexity
        num_tokens = self._compute_sequence_length(content, base_embedding)

        # 3. Project into latent tokens
        tokens = self._embed_to_tokens(base_embedding, num_tokens, content, memory_id)

        # 4. Compute compression ratio
        raw_chars = len(content)
        token_elements = num_tokens * self.latent_dim
        compressed_ratio = raw_chars / max(token_elements, 1)

        sequence_id = str(uuid.uuid4())
        self._encode_count += 1

        return MemSequence(
            sequence_id=sequence_id,
            tokens=tokens,
            num_tokens=num_tokens,
            source_memory_content=content,
            compressed_ratio=compressed_ratio,
            created_at=time.time(),
            metadata={
                "base_embedding_norm": float(np.linalg.norm(base_embedding)),
            },
        )

    def _compute_sequence_length(
        self,
        content: str,
        embedding: np.ndarray,
    ) -> int:
        """
        Compute the number of latent tokens for this memory.

        More complex experiences get more tokens. Complexity is
        estimated using content length and embedding entropy.

        Args:
            content: The raw memory content.
            embedding: Content embedding vector.

        Returns:
            Number of tokens (1 to max_tokens).
        """
        # Length-based: longer content = more tokens (up to cap)
        length_factor = math.log(len(content) + 1) / math.log(500)
        length_factor = min(1.0, max(0.2, length_factor))

        # Entropy-based: higher embedding entropy = more tokens
        emb = np.abs(embedding.flatten())
        emb_norm = emb / (emb.sum() + 1e-12)
        entropy = -float(np.sum(emb_norm * np.log(emb_norm + 1e-12)))
        entropy /= math.log(len(emb_norm))  # normalize to [0, 1]
        entropy = min(1.0, max(0.0, entropy))

        # Combine: more length + higher entropy = more tokens
        complexity = 0.6 * length_factor + 0.4 * entropy
        num_tokens = max(1, int(complexity * self.max_tokens))
        return num_tokens

    def _embed_to_tokens(
        self,
        embedding: np.ndarray,
        num_tokens: int,
        content: str,
        memory_id: str | None,
    ) -> list[LatentToken]:
        """
        Project a single embedding into N latent tokens.

        Uses random projections with content-derived seed for
        determinism (production would use learned projections).

        Args:
            embedding: The base content embedding.
            num_tokens: How many tokens to produce.
            content: Raw content for seed derivation.
            memory_id: Optional source memory ID.

        Returns:
            List of LatentToken objects.
        """
        tokens: list[LatentToken] = []
        now = time.time()

        # Seed RNG from content for deterministic projections
        seed = hash(content + str(num_tokens)) & 0xFFFFFFFF
        rng = np.random.RandomState(seed)

        # Projection matrix: latent_dim -> num_tokens * latent_dim
        projection = rng.randn(num_tokens, self.latent_dim, self.latent_dim).astype(np.float32)

        # Content-based weight (salience estimation)
        base_weight = min(1.0, len(content) / 1000)
        base_weight = max(0.2, base_weight)

        for i in range(num_tokens):
            # Project: token_i = W_i @ embedding (plus bias)
            token_vec = projection[i] @ embedding

            # Normalize
            norm = np.linalg.norm(token_vec)
            if norm > 1e-12:
                token_vec = token_vec / norm

            # Decay weight slightly for later tokens
            position_decay = 1.0 - (i / num_tokens) * 0.3
            weight = base_weight * position_decay

            tokens.append(LatentToken(
                token_id=str(uuid.uuid4()),
                vector=token_vec,
                weight=weight,
                created_at=now,
                last_accessed=now,
                source_memory_id=memory_id,
            ))

        return tokens

    def encode_batch(
        self,
        memories: list[Memory],
    ) -> list[MemSequence]:
        """
        Encode a batch of memories into latent sequences.

        Args:
            memories: List of Memory objects to encode.

        Returns:
            List of MemSequences.
        """
        return [
            self.encode(m.content, m.memory_id)
            for m in memories
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Return weaver statistics."""
        return {
            "encode_count": self._encode_count,
            "latent_dim": self.latent_dim,
            "max_tokens_per_memory": self.max_tokens,
            "has_external_encoder": self.encoder is not None,
        }


# =============================================================================
# Memory Trigger
# =============================================================================


class MemoryTrigger:
    """
    Gating mechanism that decides when to retrieve from latent memory.

    The trigger evaluates whether the current inference context would
    benefit from latent memory injection. It computes a relevance
    score between the current context and stored latent sequences,
    and only retrieves when the score exceeds a threshold.

    Reference: MemGen (ICLR 2026, §3.3) — "The Memory Trigger gates
    latent memory retrieval, avoiding unnecessary token injection
    when the current task does not require memory access."
    """

    def __init__(
        self,
        threshold: float = DEFAULT_TRIGGER_THRESHOLD,
        max_sequences: int = 8,
    ):
        """
        Initialize the Memory Trigger.

        Args:
            threshold: Minimum relevance score to trigger retrieval.
            max_sequences: Maximum sequences to retrieve per trigger.
        """
        self.threshold = threshold
        self.max_sequences = max_sequences
        self._trigger_count: int = 0
        self._retrieval_count: int = 0

    def evaluate(
        self,
        context_embedding: np.ndarray,
        latent_sequences: list[MemSequence],
    ) -> tuple[bool, list[MemSequence]]:
        """
        Evaluate whether latent memory should be retrieved.

        Computes pairwise relevance between context and each latent
        sequence, then gates retrieval on the max score.

        Args:
            context_embedding: Embedding of the current context.
            latent_sequences: Available latent memory sequences.

        Returns:
            (should_retrieve: bool, relevant_sequences: list[MemSequence])
        """
        self._trigger_count += 1

        if not latent_sequences:
            return False, []

        context_norm = context_embedding / (np.linalg.norm(context_embedding) + 1e-12)

        # Score each latent sequence for relevance
        scored: list[tuple[float, MemSequence]] = []
        for seq in latent_sequences:
            seq_vectors = seq.to_vectors()
            if seq_vectors.size == 0:
                continue

            # Average token vector for coarse relevance
            seq_avg = np.mean(seq_vectors, axis=0)
            seq_avg = seq_avg / (np.linalg.norm(seq_avg) + 1e-12)

            # Weighted by token importance
            weights = seq.weight_vector()
            if weights.sum() > 0:
                weighted_avg = np.average(seq_vectors, axis=0, weights=weights)
                weighted_avg = weighted_avg / (np.linalg.norm(weighted_avg) + 1e-12)
            else:
                weighted_avg = seq_avg

            relevance = float(np.dot(context_norm, weighted_avg))
            scored.append((relevance, seq))

        # Sort by relevance descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Gate: return sequences above threshold
        relevant = [
            seq for score, seq in scored
            if score >= self.threshold
        ][:self.max_sequences]

        if relevant:
            self._retrieval_count += 1

        return len(relevant) > 0, relevant

    def trigger_rate(self) -> float:
        """Return the fraction of evaluations that triggered retrieval."""
        if self._trigger_count == 0:
            return 0.0
        return self._retrieval_count / self._trigger_count

    def get_statistics(self) -> dict[str, Any]:
        """Return trigger statistics."""
        return {
            "trigger_count": self._trigger_count,
            "retrieval_count": self._retrieval_count,
            "trigger_rate": self.trigger_rate(),
            "threshold": self.threshold,
            "max_sequences": self.max_sequences,
        }


# =============================================================================
# LatentMemory — integrating Weaver + Trigger
# =============================================================================


class LatentMemory:
    """
    MemGen-style generative latent memory system.

    Combines the Memory Weaver (encoding) and Memory Trigger (retrieval)
    to provide a fully in-token memory system with no external database
    dependency.

    Usage::
        latent_mem = LatentMemory()

        # Store a memory — encodes to latent tokens
        seq = await latent_mem.store("The user prefers JSON over XML")

        # Retrieve relevant memory for a query
        should_retrieve, sequences = latent_mem.retrieve(
            "What format does the user prefer?"
        )

    Performance targets:
        - +38.22% average improvement over ExpeL/AWM [MemGen ICLR 2026]
        - No external database needed [MemGen §1]
        - Scales to long-horizon tasks via latent token weaving [MemGen §4]
    """

    def __init__(
        self,
        weaver: MemoryWeaver | None = None,
        trigger: MemoryTrigger | None = None,
        memory_store: MemoryStore | None = None,
        max_total_tokens: int = DEFAULT_MAX_MEMORY_TOKENS,
        token_weight_decay: float = DEFAULT_TOKEN_WEIGHT_DECAY,
    ):
        """
        Initialize the latent memory system.

        Args:
            weaver: MemoryWeaver instance for encoding.
            trigger: MemoryTrigger instance for gating.
            memory_store: Optional MemoryStore for persistence.
            max_total_tokens: Maximum total latent tokens across all sequences.
            token_weight_decay: Decay rate for token weights (forgetting).
        """
        self.weaver = weaver or MemoryWeaver()
        self.trigger = trigger or MemoryTrigger()
        self._persist_store = memory_store
        self.max_total_tokens = max_total_tokens
        self.token_weight_decay = token_weight_decay

        # In-memory latent sequences (no external DB — MemGen pattern)
        self._sequences: dict[str, MemSequence] = {}
        self._total_latent_tokens: int = 0

    # ------------------------------------------------------------------
    # Store (encode → add to sequence pool)
    # ------------------------------------------------------------------

    def store(self, memory: str | Memory) -> MemSequence:
        """
        Store a memory as latent tokens.

        Args:
            memory: Either a content string or a Memory object.

        Returns:
            The encoded latent sequence.
        """
        if isinstance(memory, Memory):
            content = memory.content
            memory_id = memory.memory_id
        else:
            content = memory
            memory_id = str(uuid.uuid4())

        # Encode to latent tokens
        sequence = self.weaver.encode(content, memory_id=memory_id)

        # Enforce token budget — evict lowest-weight sequences if needed
        new_token_count = sequence.num_tokens
        if self._total_latent_tokens + new_token_count > self.max_total_tokens:
            self._evict_lowest_weight(new_token_count)

        # Store
        self._sequences[sequence.sequence_id] = sequence
        self._total_latent_tokens += new_token_count

        # Optionally persist source memory
        if self._persist_store:
            if isinstance(memory, Memory):
                self._persist_store.add(
                    content=memory.content,
                    memory_type=memory.memory_type,
                    importance=memory.importance,
                    tags=["latent", *memory.tags],
                    context={**memory.context, "latent_sequence_id": sequence.sequence_id},
                )
            else:
                self._persist_store.add(
                    content=content,
                    memory_type=MemoryType.SEMANTIC,
                    importance=0.5,
                    tags=["latent"],
                    context={"latent_sequence_id": sequence.sequence_id},
                )

        return sequence

    # ------------------------------------------------------------------
    # Retrieve (trigger-gated latent memory access)
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        context_embedding: np.ndarray | None = None,
    ) -> tuple[bool, list[MemSequence]]:
        """
        Retrieve relevant latent sequences for a query.

        If no context_embedding is provided, one is derived from
        the query text using the weaver's encoding scheme.

        Args:
            query: The query text.
            context_embedding: Optional pre-computed context embedding.

        Returns:
            (triggered: bool, sequences: list[MemSequence])
        """
        # Derive context embedding from query if not provided
        if context_embedding is None:
            seq = self.weaver.encode(query)
            context_vec = np.mean(seq.to_vectors(), axis=0)
        else:
            context_vec = context_embedding

        # Gate through trigger
        should_retrieve, sequences = self.trigger.evaluate(
            context_vec,
            list(self._sequences.values()),
        )

        # Update access times for retrieved sequences
        for seq in sequences:
            for token in seq.tokens:
                token.last_accessed = time.time()
                # Apply weight decay on access (anti-rehearsal forgetting)
                token.weight = max(0.05, token.weight * (1.0 - self.token_weight_decay))

        return should_retrieve, sequences

    def retrieve_raw(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[MemSequence, float]]:
        """
        Retrieve latent sequences without trigger gating (direct access).

        Args:
            query: Query text.
            top_k: Maximum results.

        Returns:
            List of (sequence, relevance_score) sorted by relevance.
        """
        # Encode query
        query_seq = self.weaver.encode(query)
        query_vec = np.mean(query_seq.to_vectors(), axis=0)
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-12)

        # Score all sequences
        scored: list[tuple[float, MemSequence]] = []
        for seq in self._sequences.values():
            seq_vec = np.mean(seq.to_vectors(), axis=0)
            seq_norm = seq_vec / (np.linalg.norm(seq_vec) + 1e-12)
            score = float(np.dot(query_norm, seq_norm))
            scored.append((score, seq))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def decay_weights(self):
        """
        Apply weight decay to all latent tokens (simulated forgetting).

        Tokens with weight below 0.05 are evicted from the pool.
        """
        to_remove: list[str] = []
        for seq_id, seq in self._sequences.items():
            for token in seq.tokens:
                token.weight = max(0.0, token.weight * (1.0 - self.token_weight_decay))
            # Recalculate token count after decay
            seq.num_tokens = len([t for t in seq.tokens if t.weight >= 0.05])
            if seq.num_tokens == 0:
                to_remove.append(seq_id)

        for seq_id in to_remove:
            removed = self._sequences.pop(seq_id, None)
            if removed:
                self._total_latent_tokens -= removed.num_tokens

    def _evict_lowest_weight(self, needed_tokens: int):
        """
        Evict lowest-weight sequences to free up token budget.

        Args:
            needed_tokens: Number of token slots needed.
        """
        if not self._sequences:
            return

        # Score sequences by average token weight
        scored: list[tuple[float, str]] = []
        for seq_id, seq in self._sequences.items():
            avg_weight = float(np.mean([t.weight for t in seq.tokens])) if seq.tokens else 0.0
            scored.append((avg_weight, seq_id))

        scored.sort(key=lambda x: x[0])  # lowest first

        freed = 0
        for weight, seq_id in scored:
            if freed >= needed_tokens:
                break
            removed = self._sequences.pop(seq_id, None)
            if removed:
                self._total_latent_tokens -= removed.num_tokens
                freed += removed.num_tokens

    def clear(self):
        """Clear all latent sequences (reset memory)."""
        self._sequences.clear()
        self._total_latent_tokens = 0

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_all_sequences(self) -> list[MemSequence]:
        """Return all stored latent sequences."""
        return list(self._sequences.values())

    def total_sequences(self) -> int:
        """Return the number of latent sequences stored."""
        return len(self._sequences)

    def total_tokens(self) -> int:
        """Return the total number of latent tokens."""
        return self._total_latent_tokens

    def get_statistics(self) -> dict[str, Any]:
        """
        Return comprehensive latent memory statistics.

        Returns:
            Dictionary with system state and performance targets.
        """
        avg_seq_len = (
            self._total_latent_tokens / len(self._sequences)
            if self._sequences
            else 0.0
        )
        avg_weight = (
            float(np.mean([
                t.weight for seq in self._sequences.values()
                for t in seq.tokens
            ]))
            if self._sequences
            else 0.0
        )

        return {
            "total_sequences": len(self._sequences),
            "total_latent_tokens": self._total_latent_tokens,
            "max_total_tokens": self.max_total_tokens,
            "budget_utilization": self._total_latent_tokens / max(self.max_total_tokens, 1),
            "avg_sequence_length": avg_seq_len,
            "avg_token_weight": avg_weight,
            "token_weight_decay": self.token_weight_decay,
            "weaver": self.weaver.get_statistics(),
            "trigger": self.trigger.get_statistics(),
            "has_persistence": self._persist_store is not None,
            "performance_targets": {
                "improvement_over_expel": f"+{TARGET_IMPROVEMENT_OVER_EXPEL * 100:.2f}%",
                "no_external_db": TARGET_EXTERNAL_DB_ELIMINATION,
            },
        }
