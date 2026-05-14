"""Procedural/DCI skill retrieval — Phase J of the Lyra skill-curation plan.

Hybrid retrieval combining BM25 keyword matching and Direct Corpus
Interaction (DCI) — grep-based search over the raw skill filesystem —
alongside the existing semantic embeddings layer.

Grounded in:
- arXiv:2605.05242 — Beyond Semantic Similarity (DCI)
- arXiv:2605.06978 — Group of Skills (GoSkills)
- Key finding: semantic similarity alone is insufficient for operational
  retrieval; agentic systems need procedural/grep-based search for exact
  lexical constraints and multi-hop hypothesis refinement.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


__all__ = [
    "RetrievalResult",
    "BM25Retriever",
    "DCIRetriever",
    "HybridRetriever",
]


@dataclass
class RetrievalResult:
    """One ranked skill retrieval hit with score breakdown."""

    skill_id: str
    score: float
    bm25_score: float = 0.0
    dci_score: float = 0.0
    semantic_score: float = 0.0
    matched_lines: list[str] = field(default_factory=list)

    def __lt__(self, other: "RetrievalResult") -> bool:
        return self.score < other.score


# ------------------------------------------------------------------ #
# BM25 Retriever                                                       #
# ------------------------------------------------------------------ #

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


class BM25Retriever:
    """Okapi BM25 keyword retrieval over a skill text corpus.

    Documents are skill IDs mapped to their full text.  No embeddings needed.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._corpus: dict[str, list[str]] = {}   # skill_id → token list
        self._df: dict[str, int] = {}              # term → doc frequency
        self._avgdl: float = 0.0

    def index(self, skill_id: str, text: str) -> None:
        tokens = _tokenize(text)
        self._corpus[skill_id] = tokens
        for term in set(tokens):
            self._df[term] = self._df.get(term, 0) + 1
        self._avgdl = sum(len(t) for t in self._corpus.values()) / max(1, len(self._corpus))

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        query_terms = _tokenize(query)
        n = len(self._corpus)
        scores: dict[str, float] = {}

        for term in query_terms:
            df = self._df.get(term, 0)
            if df == 0:
                continue
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
            for skill_id, tokens in self._corpus.items():
                tf = tokens.count(term)
                if tf == 0:
                    continue
                dl = len(tokens)
                numerator = tf * (self._k1 + 1)
                denominator = tf + self._k1 * (1 - self._b + self._b * dl / max(1, self._avgdl))
                scores[skill_id] = scores.get(skill_id, 0.0) + idf * numerator / denominator

        results = [
            RetrievalResult(skill_id=sid, score=s, bm25_score=s)
            for sid, s in scores.items()
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


# ------------------------------------------------------------------ #
# DCI Retriever (grep-based direct corpus interaction)                 #
# ------------------------------------------------------------------ #

class DCIRetriever:
    """Direct Corpus Interaction: grep the raw skill filesystem.

    Implements the DCI paradigm from arXiv:2605.05242 — the agent
    searches skill files using exact pattern matching instead of
    compressed similarity.  This recovers evidence that embedding
    compression would filter out (exact terms, negations, rare tokens).
    """

    def __init__(self, skills_root: Optional[Path] = None) -> None:
        self._root = skills_root
        self._index: dict[str, str] = {}   # skill_id → full text (in-memory mode)

    def load_text(self, skill_id: str, text: str) -> None:
        self._index[skill_id] = text

    def load_directory(self, root: Path) -> int:
        count = 0
        for path in root.rglob("*.md"):
            self._index[path.stem] = path.read_text(encoding="utf-8", errors="replace")
            count += 1
        return count

    def grep(self, pattern: str, flags: re.RegexFlag = re.IGNORECASE) -> list[RetrievalResult]:
        """Return skills whose text matches *pattern*, with matched lines."""
        compiled = re.compile(pattern, flags)
        results: list[RetrievalResult] = []
        for skill_id, text in self._index.items():
            lines = [ln for ln in text.splitlines() if compiled.search(ln)]
            if lines:
                score = len(lines) / max(1, len(text.splitlines()))
                results.append(RetrievalResult(
                    skill_id=skill_id,
                    score=score,
                    dci_score=score,
                    matched_lines=lines[:5],
                ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def multi_grep(self, patterns: list[str]) -> list[RetrievalResult]:
        """Return skills matching ALL patterns (conjunction — most precise)."""
        if not patterns:
            return []
        sets = [
            {r.skill_id: r for r in self.grep(p)}
            for p in patterns
        ]
        common_ids = set(sets[0].keys())
        for s in sets[1:]:
            common_ids &= set(s.keys())
        results: list[RetrievalResult] = []
        for sid in common_ids:
            total = sum(s[sid].dci_score for s in sets if sid in s)
            avg = total / len(patterns)
            matched = []
            for s in sets:
                if sid in s:
                    matched.extend(s[sid].matched_lines)
            results.append(RetrievalResult(
                skill_id=sid,
                score=avg,
                dci_score=avg,
                matched_lines=matched[:10],
            ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results


# ------------------------------------------------------------------ #
# Hybrid Retriever                                                     #
# ------------------------------------------------------------------ #

class HybridRetriever:
    """Combines BM25 + DCI with optional semantic scores.

    Score fusion: weighted sum with configurable α (BM25) + β (DCI) + γ (semantic).
    The defaults favour BM25 + DCI over semantic to bias toward precision.
    """

    def __init__(
        self,
        bm25: Optional[BM25Retriever] = None,
        dci: Optional[DCIRetriever] = None,
        alpha: float = 0.40,   # BM25 weight
        beta: float = 0.40,    # DCI weight
        gamma: float = 0.20,   # semantic weight
    ) -> None:
        self._bm25 = bm25 or BM25Retriever()
        self._dci = dci or DCIRetriever()
        self._alpha = alpha
        self._beta = beta
        self._gamma = gamma
        self._semantic_scores: dict[str, float] = {}

    def index(self, skill_id: str, text: str) -> None:
        self._bm25.index(skill_id, text)
        self._dci.load_text(skill_id, text)

    def set_semantic_score(self, skill_id: str, score: float) -> None:
        self._semantic_scores[skill_id] = score

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        bm25_hits = {r.skill_id: r for r in self._bm25.search(query, top_k=top_k * 2)}
        dci_hits = {r.skill_id: r for r in self._dci.grep(query)}

        all_ids = set(bm25_hits) | set(dci_hits)
        fused: list[RetrievalResult] = []
        for sid in all_ids:
            b = bm25_hits[sid].bm25_score if sid in bm25_hits else 0.0
            d = dci_hits[sid].dci_score if sid in dci_hits else 0.0
            s = self._semantic_scores.get(sid, 0.0)
            combined = self._alpha * b + self._beta * d + self._gamma * s
            matched = (dci_hits[sid].matched_lines if sid in dci_hits else [])
            fused.append(RetrievalResult(
                skill_id=sid,
                score=combined,
                bm25_score=b,
                dci_score=d,
                semantic_score=s,
                matched_lines=matched,
            ))
        fused.sort(key=lambda r: r.score, reverse=True)
        return fused[:top_k]
