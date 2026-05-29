"""Tests for Claim Verification package."""

from lyra_attestor import ClaimType
from lyra_claim_verification import Claim, ClaimDAG, ClaimVerifier


class TestClaimDAG:
    def test_add_claim(self):
        dag = ClaimDAG()
        c = Claim(id="c1", claim_type=ClaimType.MEASUREMENT, statement="test", evidence=["ev1"])
        dag.add_claim(c)
        assert "c1" in dag.claims

    def test_verification_order(self):
        dag = ClaimDAG()
        dag.add_claim(
            Claim(id="c1", claim_type=ClaimType.MEASUREMENT, statement="base", evidence=[])
        )
        dag.add_claim(
            Claim(
                id="c2",
                claim_type=ClaimType.INFERENCE,
                statement="derived",
                evidence=[],
                parent_ids=["c1"],
            )
        )
        dag.add_claim(
            Claim(
                id="c3",
                claim_type=ClaimType.INFERENCE,
                statement="final",
                evidence=[],
                parent_ids=["c2"],
            )
        )
        order = dag.get_verification_order("c3")
        assert len(order) >= 1


class TestClaimVerifier:
    def test_verify_chain(self):
        v = ClaimVerifier()
        v.dag.add_claim(
            Claim(id="c1", claim_type=ClaimType.MEASUREMENT, statement="base", evidence=[])
        )
        v.dag.add_claim(
            Claim(
                id="c2",
                claim_type=ClaimType.INFERENCE,
                statement="derived",
                evidence=[],
                parent_ids=["c1"],
            )
        )
        results = v.verify_chain("c2")
        assert len(results) >= 1
