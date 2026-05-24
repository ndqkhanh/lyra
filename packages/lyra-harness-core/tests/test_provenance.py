"""Tests for harness_core.provenance — Witness + Ledger + Lattice."""
from __future__ import annotations

import pytest

from harness_core.provenance import (
    ProvenanceLedger,
    Witness,
    WitnessKind,
    WitnessLattice,
    compute_witness_id,
)


# --- Witness ID computation --------------------------------------------


class TestComputeWitnessId:
    def test_deterministic(self):
        a = compute_witness_id(
            kind=WitnessKind.RETRIEVAL,
            issued_by="r1",
            issued_at=1.0,
            content={"q": "x"},
        )
        b = compute_witness_id(
            kind=WitnessKind.RETRIEVAL,
            issued_by="r1",
            issued_at=1.0,
            content={"q": "x"},
        )
        assert a == b
        assert len(a) == 64  # sha256 hex

    def test_changes_with_content(self):
        a = compute_witness_id(
            kind=WitnessKind.RETRIEVAL,
            issued_by="r1",
            issued_at=1.0,
            content={"q": "x"},
        )
        b = compute_witness_id(
            kind=WitnessKind.RETRIEVAL,
            issued_by="r1",
            issued_at=1.0,
            content={"q": "y"},  # different content
        )
        assert a != b

    def test_changes_with_kind(self):
        a = compute_witness_id(
            kind=WitnessKind.RETRIEVAL,
            issued_by="r", issued_at=1.0, content={},
        )
        b = compute_witness_id(
            kind=WitnessKind.INFERENCE,
            issued_by="r", issued_at=1.0, content={},
        )
        assert a != b

    def test_parent_order_doesnt_matter(self):
        # Sorted internally; order of parents shouldn't affect the ID.
        a = compute_witness_id(
            kind=WitnessKind.INFERENCE,
            issued_by="x", issued_at=1.0, content={},
            parent_witnesses=("p1", "p2"),
        )
        b = compute_witness_id(
            kind=WitnessKind.INFERENCE,
            issued_by="x", issued_at=1.0, content={},
            parent_witnesses=("p2", "p1"),
        )
        assert a == b


# --- Witness ----------------------------------------------------------


class TestWitness:
    def test_create_auto_computes_id(self):
        w = Witness.create(
            kind=WitnessKind.AGENT_DECISION,
            issued_by="agent-1",
            content={"action": "search"},
        )
        assert len(w.witness_id) == 64
        assert w.verify_integrity() is True

    def test_short_id(self):
        w = Witness.create(kind=WitnessKind.AGENT_DECISION, issued_by="x")
        assert len(w.short_id()) == 12
        assert len(w.short_id(length=8)) == 8

    def test_verify_integrity_detects_tamper(self):
        w = Witness.create(
            kind=WitnessKind.AGENT_DECISION,
            issued_by="agent-1",
            content={"action": "search"},
        )
        # Construct a tampered witness with the original id but modified content.
        tampered = Witness(
            witness_id=w.witness_id,
            kind=w.kind,
            issued_by=w.issued_by,
            issued_at=w.issued_at,
            content={"action": "TAMPERED"},  # changed content
            parent_witnesses=w.parent_witnesses,
        )
        assert tampered.verify_integrity() is False

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            Witness(
                witness_id="",
                kind=WitnessKind.AGENT_DECISION,
                issued_by="x",
                issued_at=0.0,
            )

    def test_empty_issuer_rejected(self):
        with pytest.raises(ValueError):
            Witness.create(kind=WitnessKind.AGENT_DECISION, issued_by="")

    def test_negative_timestamp_rejected(self):
        with pytest.raises(ValueError):
            Witness(
                witness_id="x" * 64,
                kind=WitnessKind.AGENT_DECISION,
                issued_by="x",
                issued_at=-1,
            )

    def test_with_parents(self):
        parent = Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r")
        child = Witness.create(
            kind=WitnessKind.INFERENCE,
            issued_by="agent",
            content={"claim": "x"},
            parent_witnesses=[parent.witness_id],
        )
        assert parent.witness_id in child.parent_witnesses


# --- ProvenanceLedger -------------------------------------------------


class TestProvenanceLedger:
    def test_append_and_get(self):
        ledger = ProvenanceLedger()
        w = Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r1")
        ledger.append(w)
        assert ledger.get(w.witness_id) is w
        assert w.witness_id in ledger
        assert len(ledger) == 1

    def test_idempotent_append(self):
        ledger = ProvenanceLedger()
        w = Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r1")
        ledger.append(w)
        # Re-appending the same witness should be a no-op.
        ledger.append(w)
        assert len(ledger) == 1

    def test_parent_must_exist(self):
        ledger = ProvenanceLedger()
        # A child citing a non-existent parent should raise.
        child = Witness.create(
            kind=WitnessKind.INFERENCE,
            issued_by="agent",
            content={"claim": "x"},
            parent_witnesses=["nonexistent-parent"],
        )
        with pytest.raises(KeyError):
            ledger.append(child)

    def test_tampered_witness_rejected(self):
        ledger = ProvenanceLedger()
        # Build a witness with mismatched id.
        bad = Witness(
            witness_id="a" * 64,  # bogus id
            kind=WitnessKind.AGENT_DECISION,
            issued_by="x",
            issued_at=1.0,
        )
        with pytest.raises(ValueError):
            ledger.append(bad)

    def test_witnesses_for_kind(self):
        ledger = ProvenanceLedger()
        w1 = ledger.append(Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r"))
        w2 = ledger.append(Witness.create(kind=WitnessKind.AGENT_DECISION, issued_by="a"))
        retrievals = ledger.witnesses_for(kind=WitnessKind.RETRIEVAL)
        assert {w.witness_id for w in retrievals} == {w1.witness_id}

    def test_witnesses_for_issuer(self):
        ledger = ProvenanceLedger()
        w1 = ledger.append(Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r1"))
        w2 = ledger.append(Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r2"))
        r1_witnesses = ledger.witnesses_for(issued_by="r1")
        assert {w.witness_id for w in r1_witnesses} == {w1.witness_id}

    def test_trace_provenance(self):
        ledger = ProvenanceLedger()
        # retrieval → inference1 → inference2 chain.
        retrieval = ledger.append(Witness.create(
            kind=WitnessKind.RETRIEVAL, issued_by="r",
        ))
        inference1 = ledger.append(Witness.create(
            kind=WitnessKind.INFERENCE,
            issued_by="agent",
            content={"claim": "intermediate"},
            parent_witnesses=[retrieval.witness_id],
        ))
        inference2 = ledger.append(Witness.create(
            kind=WitnessKind.INFERENCE,
            issued_by="agent",
            content={"claim": "final"},
            parent_witnesses=[inference1.witness_id],
        ))
        chain = ledger.trace_provenance(inference2.witness_id)
        # Walk: inference2 → inference1 → retrieval.
        assert [w.kind for w in chain] == [
            WitnessKind.INFERENCE, WitnessKind.INFERENCE, WitnessKind.RETRIEVAL
        ]

    def test_trace_provenance_unknown_returns_empty(self):
        ledger = ProvenanceLedger()
        assert ledger.trace_provenance("nonexistent") == []

    def test_trace_provenance_dedups_diamond(self):
        # Diamond: two children share a parent; should appear once.
        ledger = ProvenanceLedger()
        root = ledger.append(Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r"))
        child_a = ledger.append(Witness.create(
            kind=WitnessKind.INFERENCE, issued_by="a",
            content={"claim": "A"}, parent_witnesses=[root.witness_id],
        ))
        child_b = ledger.append(Witness.create(
            kind=WitnessKind.INFERENCE, issued_by="b",
            content={"claim": "B"}, parent_witnesses=[root.witness_id],
        ))
        merged = ledger.append(Witness.create(
            kind=WitnessKind.INFERENCE, issued_by="m",
            content={"claim": "M"},
            parent_witnesses=[child_a.witness_id, child_b.witness_id],
        ))
        chain = ledger.trace_provenance(merged.witness_id)
        # 4 distinct witnesses: merged, A, B, root (root only once).
        assert len(chain) == 4

    def test_verify_integrity_passes_clean(self):
        ledger = ProvenanceLedger()
        ledger.append(Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r"))
        ledger.append(Witness.create(kind=WitnessKind.AGENT_DECISION, issued_by="a"))
        ok, invalid = ledger.verify_integrity()
        assert ok is True
        assert invalid == []

    def test_stats(self):
        ledger = ProvenanceLedger()
        ledger.append(Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r1"))
        ledger.append(Witness.create(kind=WitnessKind.RETRIEVAL, issued_by="r2"))
        ledger.append(Witness.create(kind=WitnessKind.AGENT_DECISION, issued_by="r1"))
        stats = ledger.stats()
        assert stats["total"] == 3
        assert stats["retrieval"] == 2
        assert stats["agent_decision"] == 1
        assert stats["issuers"] == 2


# --- WitnessLattice ---------------------------------------------------


class TestWitnessLattice:
    def test_record_decision(self):
        lattice = WitnessLattice()
        w = lattice.record_decision(agent_id="agent-1", action="search", fingerprint="fp1")
        assert w.kind == WitnessKind.AGENT_DECISION
        assert w.content["action"] == "search"

    def test_record_retrieval(self):
        lattice = WitnessLattice()
        w = lattice.record_retrieval(
            retriever_name="hipporag",
            query="who directed Casablanca",
            doc_ids=["d1", "d2"],
        )
        assert w.kind == WitnessKind.RETRIEVAL
        assert w.content["doc_ids"] == ["d1", "d2"]

    def test_record_verdict(self):
        lattice = WitnessLattice()
        w = lattice.record_verdict(
            verifier_name="composer-1",
            passed=False,
            severity="error",
            axes={"dry_run": True, "policy": False},
        )
        assert w.content["passed"] is False
        assert w.content["axes"]["policy"] is False

    def test_record_inference_requires_supporting(self):
        lattice = WitnessLattice()
        with pytest.raises(ValueError):
            lattice.record_inference(agent_id="x", claim="c", supporting=[])

    def test_record_inference_chains(self):
        lattice = WitnessLattice()
        retrieval = lattice.record_retrieval(
            retriever_name="r", query="q", doc_ids=["d1"],
        )
        inference = lattice.record_inference(
            agent_id="agent",
            claim="X is true based on d1",
            supporting=[retrieval.witness_id],
        )
        assert retrieval.witness_id in inference.parent_witnesses

    def test_explain(self):
        lattice = WitnessLattice()
        retrieval = lattice.record_retrieval(
            retriever_name="hipporag", query="X", doc_ids=["d1"],
        )
        inference = lattice.record_inference(
            agent_id="agent", claim="X is true",
            supporting=[retrieval.witness_id],
        )
        explanation = lattice.explain(inference.witness_id)
        assert "inference" in explanation
        assert "retrieval" in explanation
        assert "agent" in explanation
        assert "hipporag" in explanation

    def test_explain_unknown(self):
        lattice = WitnessLattice()
        explanation = lattice.explain("nonexistent")
        assert "not found" in explanation

    def test_supporting_for(self):
        lattice = WitnessLattice()
        retrieval = lattice.record_retrieval(
            retriever_name="r", query="q", doc_ids=["d"],
        )
        inference = lattice.record_inference(
            agent_id="a", claim="c", supporting=[retrieval.witness_id],
        )
        supporting = lattice.supporting_for(inference.witness_id)
        assert len(supporting) == 1
        assert supporting[0].witness_id == retrieval.witness_id

    def test_cited_by(self):
        lattice = WitnessLattice()
        retrieval = lattice.record_retrieval(
            retriever_name="r", query="q", doc_ids=["d"],
        )
        inference = lattice.record_inference(
            agent_id="a", claim="c", supporting=[retrieval.witness_id],
        )
        citers = lattice.cited_by(retrieval.witness_id)
        assert len(citers) == 1
        assert citers[0].witness_id == inference.witness_id


class TestEndToEndProvenance:
    """A realistic scenario: agent reasons over retrieval, gets verifier
    approval, makes a final claim. Each step records a witness; the final
    claim's provenance trace reaches all the way back."""

    def test_full_chain(self):
        lattice = WitnessLattice()
        # 1. Agent retrieves.
        retrieval = lattice.record_retrieval(
            retriever_name="hipporag",
            query="who directed Casablanca",
            doc_ids=["d2"],
        )
        # 2. Agent emits a tool result based on the retrieval.
        tool = lattice.record_tool_result(
            agent_id="research-agent",
            tool_name="self_ask",
            args={"question": "who directed Casablanca"},
            result_summary="bridge entity = Curtiz",
            parent_witnesses=[retrieval.witness_id],
        )
        # 3. Verifier approves.
        verdict = lattice.record_verdict(
            verifier_name="composer-1",
            passed=True,
            severity="info",
            axes={"dry_run": True, "policy": True},
            parent_witnesses=[tool.witness_id],
        )
        # 4. Final inference cites the verdict (which transitively cites tool + retrieval).
        final = lattice.record_inference(
            agent_id="research-agent",
            claim="Bob Curtiz directed Casablanca",
            supporting=[verdict.witness_id],
        )
        # The full provenance trace reaches all 4 witnesses.
        chain = lattice.ledger.trace_provenance(final.witness_id)
        assert len(chain) == 4
        kinds_in_trace = {w.kind for w in chain}
        assert kinds_in_trace == {
            WitnessKind.INFERENCE,
            WitnessKind.VERIFIER_VERDICT,
            WitnessKind.TOOL_RESULT,
            WitnessKind.RETRIEVAL,
        }
        # Integrity check passes.
        ok, invalid = lattice.ledger.verify_integrity()
        assert ok is True
