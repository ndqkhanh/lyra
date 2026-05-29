"""Tests for Attestor package."""
from datetime import datetime

from lyra_attestor import AttestationGraph, Attestor, MeasurementClaim, VerificationStatus


class TestAttestor:
    def test_create_measurement(self):
        a = Attestor()
        now = datetime.now().isoformat()
        claim = MeasurementClaim(
            claim_id="c1", statement="X was observed", evidence=["evidence1"],
            verifier="lyra-attestor", timestamp=now,
            source="test_source", measurement_method="direct"
        )
        a.graph.add_claim(claim)
        assert a.graph.claims["c1"].claim_id == "c1"

    def test_create_inference_and_verify(self):
        a = Attestor()
        now = datetime.now().isoformat()
        base = MeasurementClaim(
            claim_id="c1", statement="Base", evidence=[], verifier="t", timestamp=now,
            source="s", measurement_method="m"
        )
        a.graph.add_claim(base)
        base.status = VerificationStatus.PASSED
        claim = a.create_inference("c2", "Y follows from X", ["c1"], "modus_ponens", ["evidence2"])
        assert claim.claim_id == "c2"
        status = a.verify_claim("c2")
        assert status == VerificationStatus.PASSED


class TestAttestationGraph:
    def test_add_claim(self):
        g = AttestationGraph()
        now = datetime.now().isoformat()
        c = MeasurementClaim(claim_id="t1", statement="test", evidence=[], verifier="t", timestamp=now, source="s", measurement_method="m")
        g.add_claim(c)
        assert len(g.claims) == 1
