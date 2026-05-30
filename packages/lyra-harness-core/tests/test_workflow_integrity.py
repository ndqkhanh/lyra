"""Tests for Workflow Integrity Verification (P4-B5)."""
from __future__ import annotations

import pytest

from lyra_harness_core.workflow_integrity import (
    Attestation,
    AttestationVerdict,
    ChainVerification,
    TrustChain,
    WorkflowIntegrity,
    generate_key,
    hash_content,
    sign,
    verify,
)


# ---------------------------------------------------------------------------
# generate_key
# ---------------------------------------------------------------------------


class TestGenerateKey:
    def test_length(self):
        key = generate_key()
        assert len(key) == 64  # 256 bits = 32 bytes = 64 hex chars

    def test_hex_only(self):
        key = generate_key()
        int(key, 16)  # no ValueError

    def test_randomness(self):
        keys = {generate_key() for _ in range(50)}
        assert len(keys) == 50  # all unique


# ---------------------------------------------------------------------------
# hash_content
# ---------------------------------------------------------------------------


class TestHashContent:
    def test_deterministic(self):
        assert hash_content("hello") == hash_content("hello")

    def test_different_content_different_hash(self):
        assert hash_content("hello") != hash_content("world")

    def test_length(self):
        h = hash_content("test")
        assert len(h) == 64  # SHA-256 hex

    def test_empty_string(self):
        h = hash_content("")
        assert len(h) == 64


# ---------------------------------------------------------------------------
# sign / verify
# ---------------------------------------------------------------------------


class TestSignVerify:
    @pytest.fixture
    def key(self):
        return generate_key()

    def test_sign_and_verify(self, key):
        sig = sign(key, "hello")
        assert verify(key, "hello", sig)

    def test_tampered_content_fails(self, key):
        sig = sign(key, "hello")
        assert not verify(key, "world", sig)

    def test_wrong_key_fails(self, key):
        sig = sign(key, "hello")
        other_key = generate_key()
        assert not verify(other_key, "hello", sig)

    def test_tampered_signature_fails(self, key):
        sig = sign(key, "hello")
        # flip first byte of signature
        tampered = ("00" if sig[:2] != "00" else "ff") + sig[2:]
        assert not verify(key, "hello", tampered)

    def test_sign_produces_hex(self, key):
        sig = sign(key, "hello")
        int(sig, 16)  # valid hex


# ---------------------------------------------------------------------------
# Attestation
# ---------------------------------------------------------------------------


class TestAttestation:
    @pytest.fixture
    def key(self):
        return generate_key()

    def test_create_basic(self, key):
        att = Attestation.create("planner", "plan content", key)
        assert att.agent_id == "planner"
        assert len(att.attestation_id) == 12
        assert len(att.content_hash) == 64
        assert len(att.signature) == 64
        assert att.prev_hash == ""
        assert att.timestamp > 0

    def test_create_with_prev_hash(self, key):
        att = Attestation.create("executor", "result", key, prev_hash="abc123")
        assert att.prev_hash == "abc123"

    def test_create_with_metadata(self, key):
        att = Attestation.create("planner", "content", key, metadata={"task": "plan"})
        assert att.metadata == {"task": "plan"}

    def test_verify_valid(self, key):
        att = Attestation.create("planner", "content", key)
        assert att.verify(key)

    def test_verify_wrong_key(self, key):
        att = Attestation.create("planner", "content", key)
        assert not att.verify(generate_key())

    def test_hash_deterministic(self, key):
        att = Attestation.create("planner", "content", key)
        assert att.hash() == att.hash()

    def test_hash_varies_by_content(self, key):
        a1 = Attestation.create("planner", "c1", key)
        a2 = Attestation.create("planner", "c2", key)
        assert a1.hash() != a2.hash()

    def test_hash_varies_by_agent(self, key):
        k1, k2 = generate_key(), generate_key()
        a1 = Attestation.create("agent1", "content", k1)
        a2 = Attestation.create("agent2", "content", k2)
        assert a1.hash() != a2.hash()

    def test_frozen(self, key):
        att = Attestation.create("planner", "content", key)
        with pytest.raises(Exception):
            att.agent_id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TrustChain
# ---------------------------------------------------------------------------


class TestTrustChain:
    @pytest.fixture
    def key(self):
        return generate_key()

    def test_empty_chain(self):
        chain = TrustChain()
        assert len(chain) == 0
        assert chain.last_hash() == ""

    def test_append_returns_attestation(self, key):
        chain = TrustChain()
        att = chain.append("planner", "plan", key)
        assert isinstance(att, Attestation)
        assert att.agent_id == "planner"

    def test_append_links_to_previous(self, key):
        chain = TrustChain()
        a1 = chain.append("planner", "step1", key)
        a2 = chain.append("executor", "step2", key)
        assert a2.prev_hash == a1.hash()

    def test_append_with_metadata(self, key):
        chain = TrustChain()
        att = chain.append("planner", "plan", key, metadata={"priority": "high"})
        assert att.metadata == {"priority": "high"}

    def test_verify_all_empty_chain(self, key):
        chain = TrustChain()
        result = chain.verify_all({"planner": key})
        assert result.all_valid
        assert result.total == 0

    def test_verify_all_single_agent(self, key):
        chain = TrustChain()
        chain.append("planner", "plan", key)
        chain.append("planner", "revised plan", key)

        result = chain.verify_all({"planner": key})
        assert result.all_valid
        assert result.total == 2
        assert result.valid_count == 2

    def test_verify_all_multi_agent(self, key):
        k1, k2, k3 = generate_key(), generate_key(), generate_key()
        chain = TrustChain()
        chain.append("planner", "plan", k1)
        chain.append("executor", "done step 1", k2)
        chain.append("reviewer", "looks good", k3)

        result = chain.verify_all({"planner": k1, "executor": k2, "reviewer": k3})
        assert result.all_valid
        assert result.total == 3
        assert result.valid_count == 3

    def test_verify_all_invalid_signature(self, key):
        chain = TrustChain()
        chain.append("planner", "plan", key)
        chain.append("executor", "done", generate_key())  # different key

        # verify with only the original key
        result = chain.verify_all({"planner": key, "executor": key})
        assert not result.all_valid
        assert result.valid_count == 1  # only planner passes

    def test_verify_all_missing_key(self, key):
        chain = TrustChain()
        chain.append("planner", "plan", key)
        chain.append("executor", "done", key)

        result = chain.verify_all({"planner": key})  # executor key missing
        assert not result.all_valid
        assert not result.attestations[1].signature_valid

    def test_verify_all_chain_link_broken(self, key):
        chain = TrustChain()
        chain.append("planner", "step1", key)
        # manually append an attestation with wrong prev_hash
        broken = Attestation.create("executor", "step2", key, prev_hash="wrong_link")
        chain.attestations.append(broken)

        result = chain.verify_all({"planner": key, "executor": key})
        assert not result.all_valid
        assert not result.attestations[1].chain_link_valid

    def test_verify_all_prev_hash_when_verifying(self, key):
        """Link integrity: each attestation's prev_hash must match previous's hash."""
        k1, k2 = generate_key(), generate_key()
        chain = TrustChain()
        a1 = chain.append("planner", "step1", k1)
        a2 = chain.append("executor", "step2", k2)
        assert a2.prev_hash == a1.hash()

        result = chain.verify_all({"planner": k1, "executor": k2})
        assert result.all_valid
        for verdict in result.attestations:
            assert verdict.chain_link_valid

    def test_last_hash(self, key):
        chain = TrustChain()
        chain.append("planner", "step1", key)
        h1 = chain.last_hash()
        chain.append("executor", "step2", key)
        assert chain.last_hash() != h1

    def test_len(self, key):
        chain = TrustChain()
        assert len(chain) == 0
        chain.append("planner", "step1", key)
        chain.append("executor", "step2", key)
        assert len(chain) == 2


# ---------------------------------------------------------------------------
# WorkflowIntegrity
# ---------------------------------------------------------------------------


class TestWorkflowIntegrity:
    def test_register_agent_returns_key(self):
        wi = WorkflowIntegrity()
        key = wi.register_agent("planner")
        assert len(key) == 64

    def test_register_agent_already_exists(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        with pytest.raises(ValueError, match="already registered"):
            wi.register_agent("planner")

    def test_register_agent_with_key(self):
        wi = WorkflowIntegrity()
        key = generate_key()
        wi.register_agent_with_key("planner", key)
        assert wi.key_for("planner") == key

    def test_register_agent_with_key_already_exists(self):
        wi = WorkflowIntegrity()
        wi.register_agent_with_key("planner", generate_key())
        with pytest.raises(ValueError, match="already registered"):
            wi.register_agent_with_key("planner", generate_key())

    def test_attest_returns_attestation(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        att = wi.attest("planner", "plan content")
        assert isinstance(att, Attestation)
        assert att.agent_id == "planner"

    def test_attest_unknown_agent(self):
        wi = WorkflowIntegrity()
        with pytest.raises(ValueError, match="unknown agent"):
            wi.attest("unknown", "content")

    def test_attest_links_chain(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.register_agent("executor")

        a1 = wi.attest("planner", "plan")
        a2 = wi.attest("executor", "done")
        assert a2.prev_hash == a1.hash()

    def test_verify_empty(self):
        wi = WorkflowIntegrity()
        result = wi.verify()
        assert result.all_valid
        assert result.total == 0

    def test_verify_valid_chain(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.register_agent("executor")
        wi.register_agent("reviewer")

        wi.attest("planner", "plan")
        wi.attest("executor", "done")
        wi.attest("reviewer", "approved")

        result = wi.verify()
        assert result.all_valid
        assert result.total == 3
        assert result.valid_count == 3

    def test_verify_content_valid(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        att = wi.attest("planner", "the plan content")
        assert wi.verify_content("planner", "the plan content", att)

    def test_verify_content_wrong_agent(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        att = wi.attest("planner", "content")
        assert not wi.verify_content("executor", "content", att)

    def test_verify_content_wrong_content(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        att = wi.attest("planner", "original content")
        assert not wi.verify_content("planner", "different content", att)

    def test_verify_content_tampered(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        att = wi.attest("planner", "original")
        # verify with wrong content
        assert not wi.verify_content("planner", "tampered", att)

    def test_chain_property(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.attest("planner", "step1")
        assert len(wi.chain) == 1

    def test_agent_ids(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.register_agent("executor")
        assert set(wi.agent_ids) == {"planner", "executor"}

    def test_key_for_registered(self):
        wi = WorkflowIntegrity()
        key = wi.register_agent("planner")
        assert wi.key_for("planner") == key

    def test_key_for_unregistered(self):
        wi = WorkflowIntegrity()
        assert wi.key_for("nonexistent") is None

    def test_workflow_with_metadata(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        att = wi.attest("planner", "plan", metadata={"task_id": "42"})
        assert att.metadata["task_id"] == "42"

    def test_complex_workflow(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.register_agent("executor")
        wi.register_agent("reviewer")

        # Simulate a real workflow
        wi.attest("planner", "Decompose task into 3 subtasks")
        wi.attest("executor", "Implemented subtask 1")
        wi.attest("executor", "Implemented subtask 2")
        wi.attest("executor", "Implemented subtask 3")
        wi.attest("reviewer", "All subtasks verified")

        result = wi.verify()
        assert result.all_valid
        assert result.total == 5

        # Chain integrity: each link references the previous
        chain = wi.chain
        for i in range(1, len(chain.attestations)):
            assert chain.attestations[i].prev_hash == chain.attestations[i - 1].hash()


# ---------------------------------------------------------------------------
# AttestationVerdict
# ---------------------------------------------------------------------------


class TestAttestationVerdict:
    def test_is_valid_both_ok(self):
        v = AttestationVerdict("a1", "planner", True, True)
        assert v.is_valid

    def test_is_valid_sig_broken(self):
        v = AttestationVerdict("a1", "planner", False, True)
        assert not v.is_valid

    def test_is_valid_link_broken(self):
        v = AttestationVerdict("a1", "planner", True, False)
        assert not v.is_valid


# ---------------------------------------------------------------------------
# ChainVerification
# ---------------------------------------------------------------------------


class TestChainVerification:
    def test_all_valid_true(self):
        results = [
            AttestationVerdict("a1", "p", True, True),
            AttestationVerdict("a2", "e", True, True),
        ]
        cv = ChainVerification(results, True, 2, 2)
        assert cv.all_valid
        assert cv.total == 2
        assert cv.valid_count == 2

    def test_all_valid_false(self):
        results = [
            AttestationVerdict("a1", "p", True, True),
            AttestationVerdict("a2", "e", False, True),
        ]
        cv = ChainVerification(results, False, 2, 1)
        assert not cv.all_valid
        assert cv.valid_count == 1


# ---------------------------------------------------------------------------
# Tamper detection (end-to-end)
# ---------------------------------------------------------------------------


class TestTamperDetection:
    def test_content_tampering_detected(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.register_agent("executor")

        att1 = wi.attest("planner", "original plan")
        wi.attest("executor", "result based on plan")

        # Verify original chain
        assert wi.verify().all_valid

        # Verify content matching
        assert wi.verify_content("planner", "original plan", att1)
        assert not wi.verify_content("planner", "tampered plan", att1)

    def test_chain_tampering_detected(self):
        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.register_agent("executor")

        wi.attest("planner", "step1")
        wi.attest("executor", "step2")

        assert wi.verify().all_valid

        # Tamper by removing middle attestation
        chain = wi.chain
        chain.attestations.pop(0)  # remove planner's attestation

        result = wi.verify()
        # First (remaining) attestation now has wrong prev_hash
        assert not result.all_valid

    def test_external_attestation_injected(self):
        """Injecting an attestation with a different key should not verify."""
        wi = WorkflowIntegrity()
        wi.register_agent("planner")

        wi.attest("planner", "legitimate")
        assert wi.verify().all_valid

        # Inject forged attestation with different key
        forged = Attestation.create("planner", "forged output", generate_key())
        wi.chain.attestations.append(forged)

        result = wi.verify()
        assert not result.all_valid
        assert not result.attestations[-1].signature_valid
