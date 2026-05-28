"""MRAgent Dual Encoder — multi-representation memory encoding for hybrid retrieval.

Encodes each memory into two complementary representations:
  - Dense: continuous embedding vector for semantic similarity search
  - Sparse: bag-of-tokens vector for exact keyword/lexical matching

The dual representation enables cross-modal retrieval: query with dense
vectors, sparse keywords, or both. Grounded in MemAgents (ICLR 2026)
multi-layer memory architecture and DPR (Dense Passage Retrieval) design.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class EncoderConfig:
    """Configuration for the dual encoder."""

    dense_dim: int = 384
    sparse_vocab_size: int = 8192
    fusion_weight: float = 0.7  # dense weight in hybrid scoring
    min_token_length: int = 2
    max_ngram: int = 3


@dataclass(frozen=True)
class DenseVector:
    """Continuous embedding vector for semantic similarity."""

    values: tuple[float, ...]
    dim: int

    def __post_init__(self) -> None:
        if len(self.values) != self.dim:
            raise ValueError(f"Expected {self.dim} dimensions, got {len(self.values)}")

    def __len__(self) -> int:
        return self.dim

    def __getitem__(self, idx: int) -> float:
        return self.values[idx]

    def dot(self, other: DenseVector) -> float:
        if self.dim != other.dim:
            raise ValueError("Dimension mismatch")
        return sum(a * b for a, b in zip(self.values, other.values))

    def cosine_similarity(self, other: DenseVector) -> float:
        dot = self.dot(other)
        norm_a = math.sqrt(sum(a * a for a in self.values))
        norm_b = math.sqrt(sum(b * b for b in other.values))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def l2_norm(self) -> float:
        return math.sqrt(sum(v * v for v in self.values))


@dataclass(frozen=True)
class SparseVector:
    """Bag-of-tokens sparse vector for exact lexical matching."""

    indices: tuple[int, ...]
    values: tuple[float, ...]
    vocab_size: int

    def __post_init__(self) -> None:
        if len(self.indices) != len(self.values):
            raise ValueError("indices and values must have same length")

    def __len__(self) -> int:
        return len(self.indices)

    def dot(self, other: SparseVector) -> float:
        """Compute dot product between two sparse vectors."""
        i, j = 0, 0
        result = 0.0
        while i < len(self.indices) and j < len(other.indices):
            si, sj = self.indices[i], other.indices[j]
            if si == sj:
                result += self.values[i] * other.values[j]
                i += 1
                j += 1
            elif si < sj:
                i += 1
            else:
                j += 1
        return result

    def to_dense(self) -> tuple[float, ...]:
        dense = [0.0] * self.vocab_size
        for idx, val in zip(self.indices, self.values):
            if 0 <= idx < self.vocab_size:
                dense[idx] = val
        return tuple(dense)


@dataclass(frozen=True)
class DualEncodedMemory:
    """A memory encoded in both dense and sparse representations."""

    memory_id: str
    content: str
    dense: DenseVector
    sparse: SparseVector
    timestamp: float
    metadata: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "dense_values": list(self.dense.values),
            "sparse_indices": list(self.sparse.indices),
            "sparse_values": list(self.sparse.values),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


class DualEncoder:
    """Encodes text memories into dense + sparse dual representations.

    Dense encoding uses a learned projection (simulated via a deterministic
    hash-based embedding for reproducibility without requiring a trained model).
    Sparse encoding uses character n-gram tokenization with TF-IDF weighting.
    """

    _TOKEN_PATTERN = re.compile(r"\w+")

    def __init__(self, config: EncoderConfig | None = None) -> None:
        self.config = config or EncoderConfig()

    def encode(self, text: str, memory_id: str = "") -> DualEncodedMemory:
        """Encode text into a DualEncodedMemory with both representations."""
        mid = memory_id or self._make_id(text)
        dense = self._encode_dense(text)
        sparse = self._encode_sparse(text)
        return DualEncodedMemory(
            memory_id=mid,
            content=text,
            dense=dense,
            sparse=sparse,
            timestamp=time.time(),
        )

    def encode_batch(self, texts: list[str]) -> list[DualEncodedMemory]:
        return [self.encode(text) for text in texts]

    def hybrid_score(
        self, query: DualEncodedMemory, candidate: DualEncodedMemory
    ) -> float:
        """Compute a fused similarity score combining dense and sparse signals."""
        w = self.config.fusion_weight
        dense_sim = query.dense.cosine_similarity(candidate.dense)
        sparse_sim = self._sparse_similarity(query.sparse, candidate.sparse)
        return w * dense_sim + (1.0 - w) * sparse_sim

    def retrieve(
        self,
        query: DualEncodedMemory,
        candidates: list[DualEncodedMemory],
        top_k: int = 10,
    ) -> list[tuple[DualEncodedMemory, float]]:
        """Retrieve top-k memories by hybrid similarity score."""
        scored = [(c, self.hybrid_score(query, c)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # ── dense encoding ────────────────────────────────────────────────

    def _encode_dense(self, text: str) -> DenseVector:
        """Deterministic hash-based dense projection.

        Uses a reproducible multi-seed hash to project text into a fixed-size
        dense vector. For production, replace with a trained transformer encoder.
        """
        dim = self.config.dense_dim
        values: list[float] = []
        base_hash = hashlib.sha256(text.encode()).digest()

        for i in range(dim):
            seed = (base_hash[(i * 7) % len(base_hash)] + i) & 0xFF
            h = hashlib.sha256(bytes([seed]) + base_hash).digest()
            val = int.from_bytes(h[:4], "big") / 0xFFFFFFFF
            values.append(val * 2.0 - 1.0)

        norm = math.sqrt(sum(v * v for v in values))
        if norm > 0:
            values = [v / norm for v in values]

        return DenseVector(values=tuple(values), dim=dim)

    # ── sparse encoding ───────────────────────────────────────────────

    def _encode_sparse(self, text: str) -> SparseVector:
        """Tokenize text into character n-grams with TF-like weighting."""
        vocab_size = self.config.sparse_vocab_size
        text_lower = text.lower()
        tokens = self._TOKEN_PATTERN.findall(text_lower)

        term_freq: dict[str, float] = {}
        for token in tokens:
            if len(token) < self.config.min_token_length:
                continue
            term_freq[token] = term_freq.get(token, 0.0) + 1.0
            for n in range(2, self.config.max_ngram + 1):
                for i in range(len(token) - n + 1):
                    ngram = token[i : i + n]
                    term_freq[ngram] = term_freq.get(ngram, 0.0) + 1.0

        max_freq = max(term_freq.values()) if term_freq else 1.0
        indices: list[int] = []
        values: list[float] = []
        for term, freq in sorted(term_freq.items()):
            idx = int(hashlib.md5(term.encode()).hexdigest(), 16) % vocab_size
            indices.append(idx)
            values.append(freq / max_freq)

        return SparseVector(
            indices=tuple(indices),
            values=tuple(values),
            vocab_size=vocab_size,
        )

    @staticmethod
    def _sparse_similarity(a: SparseVector, b: SparseVector) -> float:
        """Jaccard-like similarity between two sparse vectors."""
        dot = a.dot(b)
        if dot == 0.0:
            return 0.0
        norm_a = math.sqrt(sum(v * v for v in a.values))
        norm_b = math.sqrt(sum(v * v for v in b.values))
        denom = norm_a * norm_b
        return dot / denom if denom > 0 else 0.0

    @staticmethod
    def _make_id(text: str) -> str:
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"mem-{h}"


__all__ = [
    "DenseVector",
    "DualEncodedMemory",
    "DualEncoder",
    "EncoderConfig",
    "SparseVector",
]
