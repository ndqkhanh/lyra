"""Tests for harness_core.gates.kg_fact — KG-grounded fact verification."""
from __future__ import annotations

import pytest

from harness_core.gates import (
    FactClaim,
    KGFactGate,
    KGFactVerdict,
    KGSource,
    StaticKGSource,
)
from harness_core.verifier import Severity


# --- FactClaim ---------------------------------------------------------


class TestFactClaim:
    def test_valid(self):
        c = FactClaim(
            claim_id="c1",
            claim_text="x has y",
            fact_type="seq_length",
            asserted_value=393,
            cited_source=KGSource.UNIPROT,
            cited_id="P53_HUMAN",
        )
        assert c.claim_id == "c1"

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            FactClaim(claim_id="", claim_text="x", fact_type="t", asserted_value=1)

    def test_empty_text_rejected(self):
        with pytest.raises(ValueError):
            FactClaim(claim_id="c", claim_text="", fact_type="t", asserted_value=1)

    def test_empty_fact_type_rejected(self):
        with pytest.raises(ValueError):
            FactClaim(claim_id="c", claim_text="x", fact_type="", asserted_value=1)


# --- StaticKGSource ----------------------------------------------------


class TestStaticKGSource:
    def test_add_and_lookup(self):
        src = StaticKGSource(name=KGSource.UNIPROT)
        src.add(fact_type="seq_length", entry_id="P53", value=393)
        assert src.lookup(fact_type="seq_length", entry_id="P53") == 393
        assert src.lookup(fact_type="seq_length", entry_id="missing") is None
        assert src.lookup(fact_type="missing", entry_id="P53") is None


# --- KGFactGate -- citation gate ---------------------------------------


def _build_gate(*, require_citation: bool = True, tolerance: float = 0.05) -> KGFactGate:
    uniprot = StaticKGSource(name=KGSource.UNIPROT)
    uniprot.add(fact_type="sequence_length", entry_id="P53_HUMAN", value=393)
    uniprot.add(fact_type="molecular_weight", entry_id="P53_HUMAN", value=43653.0)

    pdb = StaticKGSource(name=KGSource.PDB)
    pdb.add(fact_type="resolution_angstroms", entry_id="1TUP", value=2.2)

    alphafold = StaticKGSource(name=KGSource.ALPHAFOLD)
    alphafold.add(fact_type="confidence", entry_id="AF-P53_HUMAN", value=0.91)

    return KGFactGate(
        sources={
            KGSource.UNIPROT: uniprot,
            KGSource.PDB: pdb,
            KGSource.ALPHAFOLD: alphafold,
        },
        relative_tolerance=tolerance,
        require_citation=require_citation,
    )


class TestKGFactGateCitation:
    def test_no_citation_required_blocks(self):
        gate = _build_gate(require_citation=True)
        claim = FactClaim(
            claim_id="c1",
            claim_text="TP53 has 400 residues",
            fact_type="sequence_length",
            asserted_value=400,
            # no cited_source / cited_id
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.ERROR
        assert "citation" in v.note.lower()

    def test_no_citation_warning_when_not_required(self):
        gate = _build_gate(require_citation=False)
        claim = FactClaim(
            claim_id="c1", claim_text="x",
            fact_type="seq", asserted_value=400,
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.WARNING

    def test_unknown_source_blocks(self):
        gate = _build_gate()
        claim = FactClaim(
            claim_id="c1", claim_text="x",
            fact_type="something", asserted_value=1,
            cited_source=KGSource.PUBCHEM,  # not configured in fixture
            cited_id="CID123",
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.ERROR
        assert "not configured" in v.note


# --- KGFactGate -- value comparison ------------------------------------


class TestKGFactGateNumericalComparison:
    def test_exact_numerical_match(self):
        gate = _build_gate()
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="sequence_length", asserted_value=393,
            cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
        )
        v = gate.verify(claim)
        assert v.grounded is True
        assert v.deviation == 0.0
        assert v.severity == Severity.INFO

    def test_within_tolerance(self):
        gate = _build_gate(tolerance=0.1)
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="sequence_length", asserted_value=400,  # 393 ± 10%
            cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
        )
        v = gate.verify(claim)
        assert v.grounded is True
        assert v.deviation == pytest.approx((400 - 393) / 393, abs=1e-4)

    def test_exceeds_tolerance(self):
        gate = _build_gate(tolerance=0.05)
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="sequence_length", asserted_value=500,  # way off
            cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.ERROR
        assert "tolerance" in v.note

    def test_float_match(self):
        gate = _build_gate(tolerance=0.05)
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="resolution_angstroms", asserted_value=2.21,  # 2.2 ± 5%
            cited_source=KGSource.PDB, cited_id="1TUP",
        )
        v = gate.verify(claim)
        assert v.grounded is True

    def test_float_above_tolerance(self):
        gate = _build_gate(tolerance=0.01)
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="resolution_angstroms", asserted_value=2.5,  # 2.2 + ~14%
            cited_source=KGSource.PDB, cited_id="1TUP",
        )
        v = gate.verify(claim)
        assert v.grounded is False

    def test_zero_ground_truth_exact_match(self):
        src = StaticKGSource(name=KGSource.CUSTOM)
        src.add(fact_type="defects", entry_id="X", value=0)
        gate = KGFactGate(sources={KGSource.CUSTOM: src})
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="defects", asserted_value=0,
            cited_source=KGSource.CUSTOM, cited_id="X",
        )
        v = gate.verify(claim)
        assert v.grounded is True
        assert v.deviation == 0.0

    def test_zero_ground_truth_nonzero_assertion(self):
        src = StaticKGSource(name=KGSource.CUSTOM)
        src.add(fact_type="defects", entry_id="X", value=0)
        gate = KGFactGate(sources={KGSource.CUSTOM: src})
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="defects", asserted_value=5,
            cited_source=KGSource.CUSTOM, cited_id="X",
        )
        v = gate.verify(claim)
        assert v.grounded is False


# --- KGFactGate -- string / categorical -------------------------------


class TestKGFactGateStringComparison:
    def test_string_exact_match(self):
        src = StaticKGSource(name=KGSource.UNIPROT)
        src.add(fact_type="organism", entry_id="P53_HUMAN", value="Homo sapiens")
        gate = KGFactGate(sources={KGSource.UNIPROT: src})
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="organism", asserted_value="Homo sapiens",
            cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
        )
        v = gate.verify(claim)
        assert v.grounded is True

    def test_string_mismatch(self):
        src = StaticKGSource(name=KGSource.UNIPROT)
        src.add(fact_type="organism", entry_id="P53_HUMAN", value="Homo sapiens")
        gate = KGFactGate(sources={KGSource.UNIPROT: src})
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="organism", asserted_value="Mus musculus",
            cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.ERROR


# --- KGFactGate -- error handling -------------------------------------


class TestKGFactGateErrors:
    def test_missing_entry_blocks(self):
        gate = _build_gate()
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="sequence_length", asserted_value=393,
            cited_source=KGSource.UNIPROT, cited_id="NONEXISTENT",
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert "not found" in v.note

    def test_lookup_error_fail_closed(self):
        class BrokenSource:
            name = KGSource.CUSTOM
            def lookup(self, *, fact_type, entry_id):
                raise RuntimeError("API down")
        gate = KGFactGate(sources={KGSource.CUSTOM: BrokenSource()}, fail_closed=True)
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="any", asserted_value=1,
            cited_source=KGSource.CUSTOM, cited_id="X",
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.ERROR
        assert "API down" in v.note

    def test_lookup_error_fail_open_warning(self):
        class BrokenSource:
            name = KGSource.CUSTOM
            def lookup(self, *, fact_type, entry_id):
                raise RuntimeError("API down")
        gate = KGFactGate(sources={KGSource.CUSTOM: BrokenSource()}, fail_closed=False)
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="any", asserted_value=1,
            cited_source=KGSource.CUSTOM, cited_id="X",
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.WARNING

    def test_type_mismatch(self):
        src = StaticKGSource(name=KGSource.CUSTOM)
        src.add(fact_type="t", entry_id="X", value="not_a_number")
        gate = KGFactGate(sources={KGSource.CUSTOM: src})
        claim = FactClaim(
            claim_id="c", claim_text="x",
            fact_type="t", asserted_value=1.5,  # numeric assertion
            cited_source=KGSource.CUSTOM, cited_id="X",
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert "type mismatch" in v.note

    def test_invalid_tolerance_rejected(self):
        with pytest.raises(ValueError):
            KGFactGate(sources={}, relative_tolerance=1.5)


# --- KGFactGate -- batch filter ---------------------------------------


class TestKGFactGateFilter:
    def test_filter_returns_grounded_only(self):
        gate = _build_gate(tolerance=0.05)
        claims = [
            FactClaim(
                claim_id="ok", claim_text="x",
                fact_type="sequence_length", asserted_value=393,
                cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
            ),
            FactClaim(
                claim_id="bad", claim_text="y",
                fact_type="sequence_length", asserted_value=999,  # off
                cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
            ),
            FactClaim(
                claim_id="no_cite", claim_text="z",
                fact_type="sequence_length", asserted_value=500,
            ),
        ]
        grounded, verdicts = gate.filter(claims)
        assert {c.claim_id for c in grounded} == {"ok"}
        assert len(verdicts) == 3

    def test_stats(self):
        gate = _build_gate(tolerance=0.05)
        claims = [
            FactClaim(
                claim_id="ok", claim_text="x",
                fact_type="sequence_length", asserted_value=393,
                cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
            ),
            FactClaim(
                claim_id="off", claim_text="y",
                fact_type="sequence_length", asserted_value=999,
                cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
            ),
            FactClaim(
                claim_id="no_cite", claim_text="z",
                fact_type="sequence_length", asserted_value=500,
            ),
        ]
        _, verdicts = gate.filter(claims)
        s = gate.stats(verdicts)
        assert s["total"] == 3
        assert s["grounded"] == 1
        assert s["no_citation"] == 1
        assert s["deviation_exceeded"] == 1


# --- End-to-end Helix scenario ----------------------------------------


class TestHelixScenario:
    def test_protein_research_workflow(self):
        """Realistic Helix-Bio scenario: research agent makes 4 claims about
        a protein; gate verifies each against UniProt + AlphaFold."""
        uniprot = StaticKGSource(name=KGSource.UNIPROT)
        uniprot.add(fact_type="sequence_length", entry_id="P53_HUMAN", value=393)
        uniprot.add(fact_type="molecular_weight_kda", entry_id="P53_HUMAN", value=43.65)
        uniprot.add(fact_type="organism", entry_id="P53_HUMAN", value="Homo sapiens")

        alphafold = StaticKGSource(name=KGSource.ALPHAFOLD)
        alphafold.add(fact_type="confidence", entry_id="AF-P53", value=0.91)

        gate = KGFactGate(
            sources={KGSource.UNIPROT: uniprot, KGSource.ALPHAFOLD: alphafold},
            relative_tolerance=0.05,
        )

        claims = [
            FactClaim(
                claim_id="length", claim_text="TP53 has 393 residues",
                fact_type="sequence_length", asserted_value=393,
                cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
            ),
            FactClaim(
                claim_id="weight", claim_text="TP53 is ~43.7 kDa",
                fact_type="molecular_weight_kda", asserted_value=43.7,
                cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
            ),
            FactClaim(
                claim_id="organism", claim_text="TP53 (human)",
                fact_type="organism", asserted_value="Homo sapiens",
                cited_source=KGSource.UNIPROT, cited_id="P53_HUMAN",
            ),
            FactClaim(
                claim_id="conf", claim_text="AlphaFold confidence 0.91",
                fact_type="confidence", asserted_value=0.91,
                cited_source=KGSource.ALPHAFOLD, cited_id="AF-P53",
            ),
        ]
        grounded, verdicts = gate.filter(claims)
        # All 4 claims are accurately grounded.
        assert len(grounded) == 4
        assert all(v.grounded for v in verdicts)

    def test_helix_blocks_uncited_numerical_claim(self):
        """A claim about TP53 weight without a citation must be blocked."""
        gate = KGFactGate(sources={}, require_citation=True)
        claim = FactClaim(
            claim_id="bad", claim_text="TP53 weighs 50 kDa",
            fact_type="molecular_weight_kda", asserted_value=50,
            # no citation
        )
        v = gate.verify(claim)
        assert v.grounded is False
        assert v.severity == Severity.ERROR
