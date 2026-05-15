"""KG-grounded fact gate — verify numerical claims against structured KGs.

Per [docs/219-helix-bio-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/219-helix-bio-multi-hop-collaborative-apply-plan.md) §4.4 —
Helix-Bio Tier-1 non-negotiable. Numerical claims (binding affinity, IC50,
fold accuracy, sequence length, molecular weight, etc.) must:

    1. Cite a structured KG source (UniProt / PDB / AlphaFold / PubChem / ChEMBL).
    2. The cited value must match the source's value within ``relative_tolerance``.

Claims without citations are flagged at ``Severity.WARNING`` (or ``ERROR`` when
``require_citation=True``). Claims with citations whose values deviate beyond
tolerance are flagged at ``Severity.ERROR``. Lookups that error are flagged
fail-closed (the operator can't verify → drop the claim).

Composes with:
    - :mod:`harness_core.gates.retraction` — a retraction gate already filters
      retracted papers; this gate filters un-grounded numerical claims.
    - :mod:`harness_core.verifier` — wrap as a single-axis verifier
      (axis=CUSTOM) for inclusion in a multi-axis composer.
    - :mod:`harness_core.provenance` — every claim verdict can be recorded
      as a witness citing the KG-source lookup.

Used by Helix-Bio. Cipher-Sec can adopt for CVE-grounded claims (cite NVD).
Polaris can adopt for typed-trust-tier-grounded claims (cite OpenScholar).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from ..verifier import Severity


class KGSource(str, enum.Enum):
    """The structured KG sources the gate verifies against."""

    UNIPROT = "uniprot"
    PDB = "pdb"
    ALPHAFOLD = "alphafold"
    PUBCHEM = "pubchem"
    CHEMBL = "chembl"
    CUSTOM = "custom"


@dataclass(frozen=True)
class FactClaim:
    """A factual numerical claim that should be KG-verified."""

    claim_id: str
    claim_text: str  # human-readable claim
    fact_type: str  # e.g. "binding_affinity", "ic50", "fold_accuracy"
    asserted_value: Any  # numeric or string the claim asserts
    asserted_unit: str = ""  # e.g. "nM", "kcal/mol", "Å"
    cited_source: Optional[KGSource] = None
    cited_id: Optional[str] = None  # entry id in the source (UniProt accession, PDB id, etc.)

    def __post_init__(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id must be non-empty")
        if not self.claim_text:
            raise ValueError("claim_text must be non-empty")
        if not self.fact_type:
            raise ValueError("fact_type must be non-empty")


@dataclass(frozen=True)
class KGFactVerdict:
    """The gate's per-claim verdict."""

    claim: FactClaim
    grounded: bool  # claim is supported by the cited source within tolerance
    severity: Severity
    note: str = ""
    ground_truth_value: Optional[Any] = None
    deviation: Optional[float] = None  # |asserted - ground_truth| / |ground_truth|

    @property
    def passed(self) -> bool:
        return self.grounded


class KGSourceProtocol(Protocol):
    """A KG lookup source (UniProt, PDB, AlphaFold, etc.)."""

    name: KGSource

    def lookup(self, *, fact_type: str, entry_id: str) -> Optional[Any]: ...


# --- Stub source for tests + cold-start ---------------------------------


@dataclass
class StaticKGSource:
    """In-memory KG source — for tests and cold-start defaults.

    Production wires a real client (``requests``-based UniProt API, etc.)
    through the :class:`KGSourceProtocol`.
    """

    name: KGSource
    facts: dict[tuple[str, str], Any] = field(default_factory=dict)

    def add(self, *, fact_type: str, entry_id: str, value: Any) -> None:
        self.facts[(fact_type, entry_id)] = value

    def lookup(self, *, fact_type: str, entry_id: str) -> Optional[Any]:
        return self.facts.get((fact_type, entry_id))


# --- The gate -----------------------------------------------------------


@dataclass
class KGFactGate:
    """Verify factual claims against structured KG sources.

    >>> uniprot = StaticKGSource(name=KGSource.UNIPROT)
    >>> uniprot.add(fact_type="sequence_length", entry_id="P53_HUMAN", value=393)
    >>> gate = KGFactGate(sources={KGSource.UNIPROT: uniprot}, relative_tolerance=0.05)
    >>> claim = FactClaim(
    ...     claim_id="c1",
    ...     claim_text="TP53 (P53_HUMAN) has 393 residues",
    ...     fact_type="sequence_length",
    ...     asserted_value=393,
    ...     cited_source=KGSource.UNIPROT,
    ...     cited_id="P53_HUMAN",
    ... )
    >>> v = gate.verify(claim)
    >>> v.grounded
    True
    """

    sources: dict[KGSource, KGSourceProtocol]
    relative_tolerance: float = 0.1
    require_citation: bool = True
    fail_closed: bool = True  # source-lookup error → drop the claim

    def __post_init__(self) -> None:
        if not 0.0 <= self.relative_tolerance <= 1.0:
            raise ValueError(
                f"relative_tolerance must be in [0, 1], got {self.relative_tolerance}"
            )

    def verify(self, claim: FactClaim) -> KGFactVerdict:
        """Verify one claim against the cited KG source."""
        # 1. Citation gate: must cite a source if require_citation.
        if claim.cited_source is None or claim.cited_id is None:
            if self.require_citation:
                return KGFactVerdict(
                    claim=claim,
                    grounded=False,
                    severity=Severity.ERROR,
                    note="numerical claim requires KG citation",
                )
            return KGFactVerdict(
                claim=claim,
                grounded=False,
                severity=Severity.WARNING,
                note="claim has no citation; require_citation=False so non-blocking",
            )

        # 2. Source must be wired.
        source = self.sources.get(claim.cited_source)
        if source is None:
            return KGFactVerdict(
                claim=claim,
                grounded=False,
                severity=Severity.ERROR,
                note=f"cited source {claim.cited_source.value!r} not configured",
            )

        # 3. Lookup.
        try:
            ground_truth = source.lookup(
                fact_type=claim.fact_type,
                entry_id=claim.cited_id,
            )
        except Exception as exc:
            severity = Severity.ERROR if self.fail_closed else Severity.WARNING
            return KGFactVerdict(
                claim=claim,
                grounded=False,
                severity=severity,
                note=f"source lookup raised {exc.__class__.__name__}: {exc}",
            )

        if ground_truth is None:
            return KGFactVerdict(
                claim=claim,
                grounded=False,
                severity=Severity.ERROR,
                note=f"entry {claim.cited_id!r} not found in {claim.cited_source.value}",
            )

        # 4. Compare values.
        return self._compare(claim=claim, ground_truth=ground_truth)

    def _compare(self, *, claim: FactClaim, ground_truth: Any) -> KGFactVerdict:
        """Compare asserted value against the KG ground truth."""
        # String / categorical claims: exact match.
        if not isinstance(claim.asserted_value, (int, float)) or isinstance(
            claim.asserted_value, bool
        ):
            if claim.asserted_value == ground_truth:
                return KGFactVerdict(
                    claim=claim,
                    grounded=True,
                    severity=Severity.INFO,
                    note=f"exact match: {claim.asserted_value!r}",
                    ground_truth_value=ground_truth,
                    deviation=0.0,
                )
            return KGFactVerdict(
                claim=claim,
                grounded=False,
                severity=Severity.ERROR,
                note=f"mismatch: asserted={claim.asserted_value!r}, "
                     f"ground_truth={ground_truth!r}",
                ground_truth_value=ground_truth,
            )

        # Numerical claims: relative-tolerance band.
        if not isinstance(ground_truth, (int, float)) or isinstance(ground_truth, bool):
            return KGFactVerdict(
                claim=claim,
                grounded=False,
                severity=Severity.ERROR,
                note=f"type mismatch: asserted is numeric, "
                     f"ground_truth={type(ground_truth).__name__}",
                ground_truth_value=ground_truth,
            )

        # Avoid divide-by-zero.
        if ground_truth == 0:
            if claim.asserted_value == 0:
                return KGFactVerdict(
                    claim=claim,
                    grounded=True,
                    severity=Severity.INFO,
                    note="exact zero match",
                    ground_truth_value=0,
                    deviation=0.0,
                )
            return KGFactVerdict(
                claim=claim,
                grounded=False,
                severity=Severity.ERROR,
                note=f"asserted={claim.asserted_value} but ground_truth=0",
                ground_truth_value=0,
            )

        deviation = abs(claim.asserted_value - ground_truth) / abs(ground_truth)
        if deviation <= self.relative_tolerance:
            return KGFactVerdict(
                claim=claim,
                grounded=True,
                severity=Severity.INFO,
                note=f"within {self.relative_tolerance:.1%} tolerance "
                     f"(deviation={deviation:.3f})",
                ground_truth_value=ground_truth,
                deviation=deviation,
            )
        return KGFactVerdict(
            claim=claim,
            grounded=False,
            severity=Severity.ERROR,
            note=f"exceeds {self.relative_tolerance:.1%} tolerance "
                 f"(deviation={deviation:.3f}; asserted={claim.asserted_value}, "
                 f"ground_truth={ground_truth})",
            ground_truth_value=ground_truth,
            deviation=deviation,
        )

    def filter(
        self,
        claims: list[FactClaim],
    ) -> tuple[list[FactClaim], list[KGFactVerdict]]:
        """Verify all claims; return (grounded_claims, all_verdicts).

        ``all_verdicts`` carries the per-claim verdict regardless of pass/fail —
        useful for the audit log even when un-grounded claims are dropped.
        """
        verdicts = [self.verify(c) for c in claims]
        grounded = [v.claim for v in verdicts if v.grounded]
        return grounded, verdicts

    def stats(self, verdicts: list[KGFactVerdict]) -> dict[str, int]:
        c = {
            "total": len(verdicts),
            "grounded": sum(1 for v in verdicts if v.grounded),
            "no_citation": sum(
                1 for v in verdicts if v.claim.cited_source is None
            ),
            "lookup_failed": sum(
                1 for v in verdicts
                if not v.grounded and "lookup" in v.note
            ),
            "deviation_exceeded": sum(
                1 for v in verdicts
                if not v.grounded and v.deviation is not None and v.deviation > 0
            ),
        }
        return c


__all__ = [
    "FactClaim",
    "KGFactGate",
    "KGFactVerdict",
    "KGSource",
    "KGSourceProtocol",
    "StaticKGSource",
]
