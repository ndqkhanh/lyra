"""L311-6 — Verifier coverage index.

Operationalizes the Karpathy 2026-04 framing
([`docs/238-karpathy-agentic-engineering-shift.md`](../../../../../../docs/238-karpathy-agentic-engineering-shift.md)):
task automation falls out where verifier density is high, not where
LLM benchmarks tick up. A :class:`VerifierCoverageIndex` aggregates
per-domain verifier counts, eval counts, and rolling pass rates, and
exposes a single :class:`VerifierCoverage` per domain to consumers
(`/coverage` slash, ``auto_mode`` classifier, routing weights).

The score is a deliberately simple weighted blend so a non-stats
operator can read it directly:

    score = 0.4 * verifier_norm + 0.4 * pass_rate + 0.2 * eval_norm

where ``verifier_norm = min(verifiers / 5, 1.0)`` (5 verifiers ≈
"reasonably-covered domain") and ``eval_norm = min(eval_count / 100,
1.0)`` (100 evals ≈ "reasonable suite").

Higher score → more reliable automation. Domains with score ≥ 0.7
are good candidates for ``edit_automatically`` admit; <0.4 should
stay ``ask_before_edits``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class VerifierCoverage:
    """Per-domain coverage record."""

    domain: str
    verifier_ids: tuple[str, ...]
    eval_count: int
    pass_rate_30d: float
    coverage_score: float

    @property
    def verifier_count(self) -> int:
        return len(self.verifier_ids)

    @property
    def admit_recommendation(self) -> str:
        """One of: ``edit_automatically``, ``ask_before_edits``, ``plan_mode``."""
        if self.coverage_score >= 0.7:
            return "edit_automatically"
        if self.coverage_score >= 0.4:
            return "ask_before_edits"
        return "plan_mode"


class VerifierCoverageIndex:
    """In-memory aggregator. Populate with :meth:`record` calls; read
    with :meth:`get` or :meth:`all`."""

    def __init__(self) -> None:
        self._verifiers: dict[str, set[str]] = {}
        self._eval_counts: dict[str, int] = {}
        self._pass_rates: dict[str, float] = {}

    # ---- mutation -------------------------------------------------

    def record_verifier(self, *, domain: str, verifier_id: str) -> None:
        self._verifiers.setdefault(domain, set()).add(verifier_id)

    def record_evals(self, *, domain: str, count: int) -> None:
        self._eval_counts[domain] = self._eval_counts.get(domain, 0) + count

    def record_pass_rate(self, *, domain: str, rate: float) -> None:
        if not (0.0 <= rate <= 1.0):
            raise ValueError(f"pass rate {rate} outside [0,1]")
        self._pass_rates[domain] = rate

    # ---- read -----------------------------------------------------

    def domains(self) -> tuple[str, ...]:
        keys = (
            set(self._verifiers)
            | set(self._eval_counts)
            | set(self._pass_rates)
        )
        return tuple(sorted(keys))

    def get(self, domain: str) -> VerifierCoverage:
        verifier_ids = tuple(sorted(self._verifiers.get(domain, set())))
        eval_count = self._eval_counts.get(domain, 0)
        pass_rate = self._pass_rates.get(domain, 0.0)
        score = self._score(
            verifier_count=len(verifier_ids),
            eval_count=eval_count,
            pass_rate=pass_rate,
        )
        return VerifierCoverage(
            domain=domain,
            verifier_ids=verifier_ids,
            eval_count=eval_count,
            pass_rate_30d=pass_rate,
            coverage_score=score,
        )

    def all(self) -> tuple[VerifierCoverage, ...]:
        return tuple(self.get(d) for d in self.domains())

    # ---- scoring --------------------------------------------------

    @staticmethod
    def _score(*, verifier_count: int, eval_count: int, pass_rate: float) -> float:
        verifier_norm = min(verifier_count / 5.0, 1.0)
        eval_norm = min(eval_count / 100.0, 1.0)
        return round(
            0.4 * verifier_norm + 0.4 * pass_rate + 0.2 * eval_norm, 4
        )


_GLOBAL_INDEX: VerifierCoverageIndex | None = None


def global_index() -> VerifierCoverageIndex:
    """Return the process-wide :class:`VerifierCoverageIndex` singleton.

    The :class:`AgentInstaller` auto-populates this on every successful
    install. The CLI `/coverage` slash reads it. Tests call
    :func:`reset_global_index` between cases to keep state clean.
    """
    global _GLOBAL_INDEX
    if _GLOBAL_INDEX is None:
        _GLOBAL_INDEX = VerifierCoverageIndex()
    return _GLOBAL_INDEX


def reset_global_index() -> None:
    """Drop the process-wide singleton. Test-only helper."""
    global _GLOBAL_INDEX
    _GLOBAL_INDEX = None


__all__ = [
    "VerifierCoverage",
    "VerifierCoverageIndex",
    "global_index",
    "reset_global_index",
]
