"""Tests for zkAgent — cryptographic execution receipts and verification."""

import time

import pytest

from lyra_core.safety.zkagent import (
    ChainVerification,
    ReceiptStatus,
    ReceiptStore,
    ToolReceipt,
    zkAgent,
)


class TestReceiptStatus:
    def test_status_values(self):
        assert ReceiptStatus.VALID.value == "valid"
        assert ReceiptStatus.INVALID.value == "invalid"
        assert ReceiptStatus.TAMPERED.value == "tampered"
        assert ReceiptStatus.UNVERIFIED.value == "unverified"


class TestToolReceipt:
    def test_receipt_creation(self):
        receipt = ToolReceipt(
            receipt_id="abc123",
            tool_name="bash",
            tool_input_hash="hash1",
            tool_output_hash="hash2",
            timestamp=time.time(),
            agent_id="lyra",
            session_id="default",
        )
        assert receipt.receipt_id == "abc123"
        assert receipt.tool_name == "bash"
        assert receipt.agent_id == "lyra"

    def test_receipt_to_dict(self):
        receipt = ToolReceipt(
            receipt_id="r1", tool_name="read",
            tool_input_hash="in1", tool_output_hash="out1",
            timestamp=1.0, agent_id="agent", session_id="s1",
        )
        d = receipt.to_dict()
        assert d["receipt_id"] == "r1"
        assert d["tool_name"] == "read"

    def test_integrity_hash(self):
        receipt = ToolReceipt(
            receipt_id="r1", tool_name="t",
            tool_input_hash="i", tool_output_hash="o",
            timestamp=1.0, agent_id="a", session_id="s",
        )
        h = receipt.compute_integrity_hash()
        assert isinstance(h, str)
        assert len(h) == 64

    def test_receipt_immutable(self):
        r = ToolReceipt("r1", "bash", "h1", "h2", 1.0, "a", "s")
        with pytest.raises(Exception):
            r.tool_name = "hacked"


class TestChainVerification:
    def test_valid_chain(self):
        cv = ChainVerification(
            valid=True,
            total_receipts=5,
            valid_receipts=5,
            tampered_receipts=0,
            first_break_index=-1,
            details=(),
        )
        assert cv.valid is True
        assert cv.total_receipts == 5

    def test_broken_chain(self):
        cv = ChainVerification(
            valid=False,
            total_receipts=10,
            valid_receipts=7,
            tampered_receipts=3,
            first_break_index=7,
            details=("Break at 7",),
        )
        assert cv.valid is False
        assert cv.first_break_index == 7

    def test_chain_immutable(self):
        cv = ChainVerification(True, 1, 1, 0, -1, ())
        with pytest.raises(Exception):
            cv.valid = False


class TestReceiptStore:
    def test_issue_receipt(self):
        store = ReceiptStore()
        receipt = store.issue("bash", "input_data", "output_data")
        assert isinstance(receipt, ToolReceipt)
        assert receipt.tool_name == "bash"
        assert receipt.receipt_id != ""

    def test_verify_valid_receipt(self):
        store = ReceiptStore()
        receipt = store.issue("bash", "input", "output")
        status = store.verify_receipt(receipt.receipt_id)
        assert status == ReceiptStatus.VALID

    def test_verify_unknown_receipt(self):
        store = ReceiptStore()
        status = store.verify_receipt("nonexistent")
        assert status == ReceiptStatus.UNVERIFIED

    def test_get_receipt(self):
        store = ReceiptStore()
        issued = store.issue("tool", "in", "out")
        retrieved = store.get_receipt(issued.receipt_id)
        assert retrieved is not None
        assert retrieved.receipt_id == issued.receipt_id

    def test_get_missing(self):
        store = ReceiptStore()
        assert store.get_receipt("nope") is None

    def test_chain_verification(self):
        store = ReceiptStore()
        store.issue("read", "i1", "o1")
        store.issue("edit", "i2", "o2")
        chain = store.verify_chain()
        assert isinstance(chain, ChainVerification)

    def test_store_receipts_count(self):
        store = ReceiptStore()
        assert store.count == 0
        store.issue("t1", "in", "out")
        store.issue("t2", "in", "out")
        assert store.count == 2

    def test_audit_trail(self):
        store = ReceiptStore()
        store.issue("read", "i", "o", session_id="s1")
        store.issue("write", "i", "o", session_id="s2")
        trail = store.audit_trail()
        assert len(trail) == 2


class TestZkAgent:
    def test_prover_creation(self):
        agent = zkAgent()
        assert agent.agent_id == "lyra"

    def test_attest_produces_receipt(self):
        agent = zkAgent()
        receipt = agent.attest("bash", "ls -la", "file list")
        assert isinstance(receipt, ToolReceipt)
        assert receipt.tool_name == "bash"

    def test_verify_execution(self):
        agent = zkAgent()
        receipt = agent.attest("bash", "input", "output")
        status = agent.verify_execution(receipt.receipt_id)
        assert status == ReceiptStatus.VALID

    def test_verify_session(self):
        agent = zkAgent()
        agent.attest("read", "i", "o")
        chain = agent.verify_session()
        assert isinstance(chain, ChainVerification)

    def test_get_audit_trail(self):
        agent = zkAgent()
        agent.attest("bash", "in", "out")
        trail = agent.get_audit_trail()
        assert isinstance(trail, list)
        assert len(trail) >= 1

    def test_receipt_count(self):
        agent = zkAgent()
        assert agent.receipt_count == 0
        agent.attest("t1", "in", "out")
        agent.attest("t2", "in", "out")
        assert agent.receipt_count == 2
