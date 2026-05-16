"""Semantic Retriever — Phase G.

TF-IDF cosine similarity retrieval of relevant conversation turns.
Zero-dependency: no embedding API, no external models required.
Enables RAG-style context retrieval over conversation history.

Evidence:
- RAG-based context: ~75% token reduction vs inject-all history
- "A focused 300-token context frequently outperforms a 113,000-token context"
  (Chroma Context Rot Study, 2025)
- One quality retrieval > one cheap embedding (Vectara 2024)
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import NamedTuple

_TOKEN_RE = re.compile(r'[a-zA-Z0-9_]+')


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class _Entry(NamedTuple):
    message: dict
    tokens: list[str]
    position: int


class SemanticRetriever:
    """TF-IDF based conversation turn retriever.

    Index all turns with .index(), then retrieve the most relevant
    ones for a given query with .retrieve(). Preserves original order
    in results so the model sees chronologically consistent context.
    """

    def __init__(self) -> None:
        self._store: list[_Entry] = []
        self._df: Counter = Counter()  # token → document frequency

    def index(self, message: dict) -> None:
        """Add a message to the index."""
        tokens = _tokenize(message.get("content", ""))
        position = len(self._store)
        self._store.append(_Entry(message, tokens, position))
        for token in set(tokens):
            self._df[token] += 1

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Return top_k messages most relevant to query, in original order.

        Returns empty list if index is empty or no results score > 0.
        """
        if not self._store:
            return []

        n_docs = len(self._store)
        idf = {
            t: math.log((n_docs + 1) / (freq + 1)) + 1.0
            for t, freq in self._df.items()
        }

        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        q_tf = Counter(q_tokens)
        q_total = len(q_tokens)
        q_vec = {t: (c / q_total) * idf.get(t, 1.0) for t, c in q_tf.items()}

        scored: list[tuple[float, int]] = []
        for entry in self._store:
            d_tf = Counter(entry.tokens)
            d_total = max(len(entry.tokens), 1)
            d_vec = {t: (c / d_total) * idf.get(t, 1.0) for t, c in d_tf.items()}
            score = _cosine(q_vec, d_vec)
            if score > 0.0:
                scored.append((score, entry.position))

        top_positions = {pos for _, pos in sorted(scored, key=lambda x: -x[0])[:top_k]}
        return [
            self._store[pos].message
            for pos in sorted(top_positions)
        ]

    def clear(self) -> None:
        self._store.clear()
        self._df.clear()

    @property
    def size(self) -> int:
        return len(self._store)
