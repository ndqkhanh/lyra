"""Latent space encoder — compresses agent messages to compressed latent vectors."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import numpy as np

from lyra_recursive_link.exceptions import EncodingError


class CompressionMethod(Enum):
    PCA = auto()
    RANDOM_PROJECTION = auto()
    SEMANTIC_HASH = auto()
    QUANTIZED = auto()


@dataclass(frozen=True)
class EncodingConfig:
    target_dimension: int = 16
    compression_method: CompressionMethod = CompressionMethod.RANDOM_PROJECTION
    preserve_semantics: bool = True
    random_seed: int = 42


@dataclass(frozen=True)
class LatentVector:
    vector: np.ndarray
    original_length: int
    compressed_length: int
    compression_ratio: float
    semantic_hash: str


def compute_compression_ratio(original_tokens: int, latent_dim: int) -> float:
    if original_tokens <= 0:
        return 0.0
    if latent_dim >= original_tokens:
        return 0.0
    return 1.0 - (latent_dim / original_tokens)


def similarity(a: LatentVector, b: LatentVector) -> float:
    if len(a.vector) != len(b.vector):
        msg = f"Cannot compute similarity: vectors have different dimensions ({len(a.vector)} vs {len(b.vector)})"
        raise ValueError(msg)
    dot = np.dot(a.vector, b.vector)
    norm_a = np.linalg.norm(a.vector)
    norm_b = np.linalg.norm(b.vector)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class LatentEncoder:
    """Compresses text messages into low-dimensional latent vectors."""

    def __init__(self, default_config: EncodingConfig | None = None) -> None:
        self.default_config = default_config or EncodingConfig()
        self.vocabulary: dict[str, int] = {}
        self._term_doc_matrix: list[list[str]] = []
        self._pca_components: np.ndarray | None = None
        self._pca_mean: np.ndarray | None = None
        self._random_matrix: np.ndarray | None = None
        self._rng: np.random.Generator = np.random.default_rng(
            self.default_config.random_seed
        )

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z]+", text.lower())
        return tokens

    def _update_vocabulary(self, tokens: list[str]) -> None:
        for token in tokens:
            if token not in self.vocabulary:
                self.vocabulary[token] = len(self.vocabulary)

    def _to_vector(self, tokens: list[str]) -> np.ndarray:
        vec = np.zeros(len(self.vocabulary), dtype=np.float64)
        for token in tokens:
            idx = self.vocabulary.get(token)
            if idx is not None:
                vec[idx] += 1.0
        return vec

    def _ensure_random_matrix(self, vocab_size: int, target_dim: int) -> np.ndarray:
        if self._random_matrix is None or self._random_matrix.shape != (target_dim, vocab_size):
            self._random_matrix = self._rng.normal(
                0.0, 1.0 / np.sqrt(target_dim), (target_dim, vocab_size)
            ).astype(np.float64)
        return self._random_matrix

    def fit(self) -> None:
        """Fit PCA components from accumulated term-document matrix."""
        if len(self._term_doc_matrix) < 2:
            return
        vectors = [self._to_vector(tokens) for tokens in self._term_doc_matrix]
        matrix = np.array(vectors, dtype=np.float64)
        self._pca_mean = np.mean(matrix, axis=0)
        centered = matrix - self._pca_mean
        try:
            u, s, vh = np.linalg.svd(centered, full_matrices=False)
            self._pca_components = vh.astype(np.float64)
        except np.linalg.LinAlgError:
            self._pca_components = None

    def _apply_pca(self, vector: np.ndarray, target_dim: int) -> np.ndarray:
        if self._pca_components is not None:
            expected = len(self._pca_mean) if self._pca_mean is not None else -1
            if len(vector) == expected:
                centered = vector - self._pca_mean
                k = min(target_dim, self._pca_components.shape[0])
                return (self._pca_components[:k] @ centered).astype(np.float64)
        return self._apply_random_projection(vector, target_dim)

    def _apply_random_projection(self, vector: np.ndarray, target_dim: int) -> np.ndarray:
        mat = self._ensure_random_matrix(len(vector), target_dim)
        return (mat @ vector).astype(np.float64)

    def _apply_semantic_hash(self, vector: np.ndarray, target_dim: int) -> np.ndarray:
        vocab_size = len(vector)
        result = np.zeros(target_dim, dtype=np.float64)
        non_zero_indices = np.where(vector > 0)[0]
        for idx in non_zero_indices:
            h = hash(f"dim_{idx}_salt") % target_dim
            result[abs(h)] += vector[idx]
        return result

    def _apply_quantized(self, vector: np.ndarray, target_dim: int) -> np.ndarray:
        compressed = self._apply_random_projection(vector, target_dim)
        max_val = np.max(np.abs(compressed)) if np.max(np.abs(compressed)) > 0 else 1.0
        normalized = compressed / max_val
        quantized = np.round(normalized * 127.0) / 127.0
        return (quantized * max_val).astype(np.float64)

    def _compute_semantic_hash(self, tokens: list[str]) -> str:
        if not tokens:
            return hashlib.md5(b"empty").hexdigest()[:16]
        key_terms = sorted(set(tokens))[:20]
        return hashlib.md5(" ".join(key_terms).encode()).hexdigest()[:16]

    def _extract_key_terms(self, tokens: list[str]) -> list[str]:
        if not tokens:
            return []
        from collections import Counter

        return [t for t, _ in Counter(tokens).most_common(10)]

    def encode(
        self, text: str, config: EncodingConfig | None = None
    ) -> LatentVector:
        cfg = config or self.default_config
        tokens = self._tokenize(text)
        self._update_vocabulary(tokens)

        if not self.vocabulary:
            raise EncodingError("Vocabulary is empty; cannot encode empty text")

        vec = self._to_vector(tokens)
        original_length = len(vec)
        target_dim = cfg.target_dimension

        if cfg.compression_method == CompressionMethod.PCA:
            compressed = self._apply_pca(vec, target_dim)
        elif cfg.compression_method == CompressionMethod.SEMANTIC_HASH:
            compressed = self._apply_semantic_hash(vec, target_dim)
        elif cfg.compression_method == CompressionMethod.QUANTIZED:
            compressed = self._apply_quantized(vec, target_dim)
        else:
            compressed = self._apply_random_projection(vec, target_dim)

        if cfg.preserve_semantics:
            self._term_doc_matrix.append(tokens)
            if cfg.compression_method == CompressionMethod.PCA:
                self.fit()

        cr = compute_compression_ratio(original_length, target_dim)
        s_hash = self._compute_semantic_hash(tokens)

        return LatentVector(
            vector=compressed,
            original_length=original_length,
            compressed_length=target_dim,
            compression_ratio=cr,
            semantic_hash=s_hash,
        )

    def batch_encode(
        self, texts: list[str], config: EncodingConfig | None = None
    ) -> list[LatentVector]:
        return [self.encode(text, config) for text in texts]

    def get_key_terms(self, text: str) -> list[str]:
        tokens = self._tokenize(text)
        return self._extract_key_terms(tokens)
