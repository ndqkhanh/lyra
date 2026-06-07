"""
Vector Search — Embedding-based semantic search for long-term memory.

Provides:
  - ``SentenceTransformerEncoder`` — wraps ``sentence-transformers/all-MiniLM-L6-v2``
  - ``TfidfEncoder`` — lightweight TF-IDF fallback (no external model weights)
  - ``VectorSearcher`` — cosine similarity over a list of text-encoder pairs

Usage::

    encoder = SentenceTransformerEncoder()
    searcher = VectorSearcher(encoder=encoder)
    texts = ["the cat sat on the mat", "dogs love to play fetch"]
    searcher.index(texts)
    results = searcher.search("feline", top_k=1)
"""

import math
import pickle
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any

import numpy as np


# =============================================================================
# Encoder abstractions
# =============================================================================


class Encoder(ABC):
    """Abstract interface for text-to-vector encoders."""

    dimension: int

    @abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray: ...

    @abstractmethod
    def encode_one(self, text: str) -> np.ndarray: ...


class SentenceTransformerEncoder(Encoder):
    """Wrapper around ``sentence-transformers/all-MiniLM-L6-v2``.

    Falls back to TF-IDF if the ``sentence_transformers`` package is not
    available or fails to load.
    """

    dimension: int = 384  # all-MiniLM-L6-v2 output dim

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model: Any = None

    def _lazy_load(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        except Exception:
            raise RuntimeError(
                f"SentenceTransformer model {self.model_name!r} could not be loaded. "
                "Install sentence-transformers or use TfidfEncoder."
            )

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return a 2-D array of shape ``(len(texts), dimension)``."""
        self._lazy_load()
        # Newer sentence-transformers (>=3.0) always returns np.ndarray;
        # older versions need convert_to_np=True.
        try:
            return self._model.encode(texts, convert_to_np=True)
        except TypeError:
            return self._model.encode(texts)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


class TfidfEncoder(Encoder):
    """Lightweight TF-IDF encoder — no external model weights required.

    Uses in-memory IDF computed from the indexed corpus at ``fit()`` time.
    ``dimension`` is the number of unique terms seen during ``fit()``.
    """

    dimension: int = 0

    def __init__(self, min_df: int = 1):
        self.min_df = min_df
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}

    def _tokenize(self, text: str) -> list[str]:
        return text.lower().split()

    def fit(self, texts: list[str]):
        """Build vocabulary and IDF from *texts*."""
        df: Counter = Counter()
        for t in texts:
            for w in set(self._tokenize(t)):
                df[w] += 1

        n_docs = len(texts)
        self._vocab = {}
        self._idf = {}
        for w, d in df.items():
            if d < self.min_df:
                continue
            idx = len(self._vocab)
            self._vocab[w] = idx
            self._idf[w] = math.log((n_docs + 1) / (d + 1)) + 1.0

        self.dimension = len(self._vocab)

    def _tfidf_vector(self, tokens: list[str]) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype=np.float32)
        tf = Counter(tokens)
        n_tokens = len(tokens) if tokens else 1
        for w, cnt in tf.items():
            if w in self._vocab:
                vec[self._vocab[w]] = (cnt / n_tokens) * self._idf[w]
        return vec

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.dimension == 0:
            raise ValueError("TfidfEncoder has not been fit() on a corpus.")
        return np.array([self._tfidf_vector(self._tokenize(t)) for t in texts])

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


# =============================================================================
# Vector Searcher
# =============================================================================


class VectorSearcher:
    """Cosine-similarity search over an indexed collection of documents.

    Typical usage::

        searcher = VectorSearcher()
        searcher.index(["doc one", "doc two", ...])
        results = searcher.search("query", top_k=3)

    Each result is ``(text, score)``.
    """

    def __init__(self, encoder: Encoder | None = None):
        self.encoder = encoder or _default_encoder()
        self._texts: list[str] = []
        self._vectors: np.ndarray | None = None

    def index(self, texts: list[str]):
        """Encode *texts* and store them for subsequent search."""
        if not texts:
            self._texts = []
            self._vectors = None
            return

        if isinstance(self.encoder, TfidfEncoder):
            self.encoder.fit(texts)

        self._texts = list(texts)
        self._vectors = self.encoder.encode(texts)

    @property
    def count(self) -> int:
        return len(self._texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Return up to *top_k* ``(text, cosine_similarity)`` results."""
        if not self._texts or self._vectors is None:
            return []
        q_vec = self.encoder.encode_one(query)
        scores = _cosine_similarity(q_vec, self._vectors)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            s = float(scores[idx])
            if s < min_score:
                break
            results.append((self._texts[idx], s))
        return results

    def batch_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[str, float, int]]:
        """Like ``search`` but also returns the internal index position."""
        if not self._texts or self._vectors is None:
            return []
        q_vec = self.encoder.encode_one(query)
        scores = _cosine_similarity(q_vec, self._vectors)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            (self._texts[idx], float(scores[idx]), idx)
            for idx in top_indices
        ]

    def get_vector(self, index: int) -> np.ndarray | None:
        """Return the raw vector at position *index*."""
        if self._vectors is None or index >= len(self._texts):
            return None
        return self._vectors[index].copy()

    def save(self, path: str):
        """Serialize encoder + index to disk."""
        with open(path, "wb") as f:
            pickle.dump({
                "encoder": self.encoder,
                "texts": self._texts,
                "vectors": self._vectors,
            }, f)

    @classmethod
    def load(cls, path: str) -> "VectorSearcher":
        """Deserialize from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        obj = cls(encoder=data["encoder"])
        obj._texts = data["texts"]
        obj._vectors = data["vectors"]
        return obj


# =============================================================================
# Internal helpers
# =============================================================================


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between vector *a* and each row of *b*."""
    norm_a = np.linalg.norm(a)
    if norm_a == 0:
        norm_a = 1.0
    norms_b = np.linalg.norm(b, axis=1)
    norms_b[norms_b == 0] = 1.0
    return (b @ a) / (norms_b * norm_a)


def _default_encoder() -> Encoder:
    """Try sentence-transformers first, fall back to TF-IDF."""
    try:
        return SentenceTransformerEncoder()
    except Exception:
        return TfidfEncoder()
