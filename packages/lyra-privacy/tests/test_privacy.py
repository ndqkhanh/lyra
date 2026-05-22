"""Tests for lyra-privacy."""
import pytest
from lyra_privacy import ConfidentialInference, DifferentialPrivacy, FederatedKnowledge, PrivacyManager


class TestConfidentialInference:
    @pytest.mark.asyncio
    async def test_secure_infer(self):
        ci = ConfidentialInference()
        result = await ci.secure_infer("test prompt", {"user": "alice"})
        assert result["verified"]
        assert "enclave_id" in result

    def test_attestation(self):
        ci = ConfidentialInference()
        proof = ci.generate_attestation()
        assert ci.verify_attestation(proof)
        assert proof.enclave_id is not None


class TestDifferentialPrivacy:
    def test_check_budget(self):
        dp = DifferentialPrivacy(epsilon=1.0)
        assert dp.check_budget("user_1", epsilon_cost=0.5)
        assert dp.check_budget("user_1", epsilon_cost=0.5)
        assert not dp.check_budget("user_1", epsilon_cost=0.1)

    def test_add_noise(self):
        dp = DifferentialPrivacy()
        noisy = dp.add_noise({"weight": 1.0, "bias": 0.5})
        assert len(noisy) == 2


class TestPrivacyManager:
    def test_summary(self):
        pm = PrivacyManager()
        s = pm.summary
        assert "confidential" in s
        assert "differential_privacy" in s
        assert "federated" in s
