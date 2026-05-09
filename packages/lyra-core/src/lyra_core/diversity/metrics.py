"""Diversity metrics + selection primitives.

See :mod:`lyra_core.diversity` for context. Cross-references in this file
point to the source paper (arXiv:2604.18005) by section number.
"""
from __future__ import annotations

import difflib
from typing import Callable, Iterable, Mapping, Protocol, Sequence


class DiversityMetric(Protocol):
    """Anything that maps a set of items to a non-negative scalar."""

    def __call__(self, items: Sequence[str]) -> float: ...


class PairwiseDistanceMetric(Protocol):
    """Symmetric distance in [0, 1]; ``d(a, a) == 0``."""

    def __call__(self, a: str, b: str) -> float: ...


def _normalised_token_distance(a: str, b: str) -> float:
    """Cheap, dependency-free pairwise distance.

    Uses :class:`difflib.SequenceMatcher` ratio; defined as ``1 - ratio``
    so identical strings score 0 and fully disjoint strings score 1.

    The Phase-1 implementation will swap this for an embedding-backed
    cosine distance (the paper uses Vendi / cosine throughout); the
    Protocol accepts either, so call sites stay unchanged.
    """
    if a == b:
        return 0.0
    ratio = difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()
    return max(0.0, min(1.0, 1.0 - ratio))


def mean_pairwise_distance(
    items: Sequence[str],
    *,
    distance: PairwiseDistanceMetric | None = None,
) -> float:
    """Mean pairwise distance across all unordered item pairs.

    The paper (§5.1) uses this as one of three diversity proxies (see
    its "Semantic Diversity (Dispersion)" metric). Returns 0.0 for
    fewer than two items because dispersion is undefined.
    """
    if len(items) < 2:
        return 0.0
    d: PairwiseDistanceMetric = distance or _normalised_token_distance
    pairs = 0
    total = 0.0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            total += d(items[i], items[j])
            pairs += 1
    return total / pairs if pairs else 0.0


def effective_diversity(items: Sequence[str]) -> float:
    """Cheap stand-in for the paper's Vendi Score (§2.3).

    True Vendi requires the spectral entropy of the kernel matrix; this
    fallback returns a monotone-with-Vendi proxy:

        eff = (mean pairwise distance) * (number of distinct items)

    so that a pool of 10 identical strings scores 0, a pool of 10 disjoint
    strings scores ~10, and intermediate distributions interpolate.
    Sufficient for Lyra's drift-gate purposes; v1.8 Phase 6 will swap in
    the real Vendi when the embedding stack lands.
    """
    if not items:
        return 0.0
    distinct = len(set(items))
    return mean_pairwise_distance(items) * distinct


def mmr_select(
    candidates: Sequence[str],
    *,
    k: int,
    relevance: Mapping[str, float] | Callable[[str], float],
    distance: PairwiseDistanceMetric | None = None,
    lambda_: float = 0.5,
) -> tuple[str, ...]:
    """Maximal Marginal Relevance selection.

    Carbonell & Goldstein (1998); the canonical fix for top-k RAG and
    ReasoningBank.recall returning near-duplicates (the paper's "Echo
    Chamber" failure mode mapped to retrieval). Each step picks the
    candidate that maximises::

        lambda * relevance(c) - (1 - lambda) * max_{s in selected} sim(c, s)

    Defaults (`lambda_ == 0.5`) put equal weight on relevance and
    novelty; raise ``lambda_`` toward 1.0 to recover the plain top-k
    behaviour, lower it toward 0.0 for maximal diversity.
    """
    if k <= 0:
        return ()
    if not 0.0 <= lambda_ <= 1.0:
        raise ValueError("lambda_ must be in [0, 1]")
    d: PairwiseDistanceMetric = distance or _normalised_token_distance
    if callable(relevance):
        rel_fn = relevance
    else:
        rel_map = dict(relevance)
        rel_fn = lambda c: rel_map.get(c, 0.0)  # noqa: E731 — closure form is intentional

    pool = list(dict.fromkeys(candidates))  # de-dup, preserve order
    selected: list[str] = []
    while pool and len(selected) < k:
        best: tuple[float, str] | None = None
        for c in pool:
            r = rel_fn(c)
            if selected:
                penalty = max(1.0 - d(c, s) for s in selected)  # similarity = 1 - distance
            else:
                penalty = 0.0
            score = lambda_ * r - (1.0 - lambda_) * penalty
            if best is None or score > best[0]:
                best = (score, c)
        assert best is not None
        selected.append(best[1])
        pool.remove(best[1])
    return tuple(selected)


def ngt_attempt_independence_guard(
    context_fingerprints: Iterable[str],
) -> None:
    """Enforce Nominal Group Technique's blind-generation rule.

    The paper (§5.2 Figure 10) shows NGT — where every agent generates
    independently *before* any discussion — strictly dominates the
    Standard topology on initial diversity. Lyra exposes this as a
    pre-flight check: the caller passes one fingerprint per parallel
    attempt's *generation context*. If two attempts share a fingerprint
    they will produce correlated outputs and the guard raises.

    A "generation context" should hash everything the attempt sees
    *before* generation: prompt template, prior-attempt summaries,
    retrieved-doc IDs, model id, sampling temperature. Identical
    fingerprints are the smoking gun for the Echo Chamber failure mode.
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for fp in context_fingerprints:
        if fp in seen:
            duplicates.add(fp)
        else:
            seen.add(fp)
    if duplicates:
        raise ValueError(
            "ngt_attempt_independence_guard: parallel attempts share generation "
            f"context fingerprint(s) {sorted(duplicates)!r}; this is the "
            "Echo-Chamber failure mode (arXiv:2604.18005 §5.2). Inject "
            "diversifying context (MaTTS prefix, persona, temperature) so each "
            "attempt's context fingerprint is unique."
        )
