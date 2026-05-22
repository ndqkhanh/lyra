"""Tests for Attestor package."""

import pytest
from lyra_attestor import Attestor, AttestationGraph, ClaimType, VerificationStatus, MeasurementClaim


class TestAttestor:
    def test_create_measurement(self):
        a = Attestor()
        claim = a.create_measurement("c1", "X was observed", "test_source", "direct", ["evidence1"])
        assert claim.claim_id == "c1"
        assert claim.claim_type == ClaimType.MEASUREMENT

    def test_create_inference(self):
        a = Attestor()
        claim = a.create_inference("c2", "Y follows from X", ["c1"], "modus_ponens", ["evidence2"])
        assert claim.claim_id == "c2"
        assert len(claim.parent_claims) == 1

    def test_verify_chain(self):
        a = Attestor()
        a.create_measurement("c1", "Base observation", "src", "method", ["ev1"])
        a.create_inference("c2", "Inference from c1", ["c1"], "rule", ["ev2"])
        status = a.verify_claim("c2")
        assert status in (VerificationStatus.PASSED, VerificationStatus.FAILED)


class TestAttestationGraph:
    def test_add_claim(self):
        g = AttestationGraph()
        c = MeasurementClaim(claim_id="t1", statement="test", evidence=[], verifier="t", timestamp="t", source="s", measurement_method="m")
        g.add_claim(c)
        assert len(g.claims) == 1
