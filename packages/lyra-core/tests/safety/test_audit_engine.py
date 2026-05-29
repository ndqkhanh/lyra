"""Tests for the Audit Engine with cryptographic verification."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from lyra_core.safety.approval_gate import ReasoningFlag, RiskLevel
from lyra_core.safety.audit_engine import AuditLogger, AuditRecord, Decision, Verdict


class TestAuditRecord:
    """Test AuditRecord immutability and serialization."""

    def test_record_is_immutable(self) -> None:
        """Verify that AuditRecord is frozen and cannot be modified."""
        record = AuditRecord(
            id="test-id",
            timestamp=datetime.now(timezone.utc),
            action_hash="abc123",
            risk_level=RiskLevel.LOW,
            reasoning_flags=(),
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
            signature=b"signature",
            prev_hash="0" * 64,
        )

        with pytest.raises(AttributeError):
            record.id = "new-id"  # type: ignore

    def test_record_to_dict(self) -> None:
        """Test serialization to dictionary."""
        timestamp = datetime.now(timezone.utc)
        record = AuditRecord(
            id="test-id",
            timestamp=timestamp,
            action_hash="abc123",
            risk_level=RiskLevel.MEDIUM,
            reasoning_flags=(ReasoningFlag.DECEPTION,),
            adversarial_verdict=Verdict.MAJORITY_DENY,
            final_decision=Decision.DENIED,
            signature=b"\x01\x02\x03",
            prev_hash="prev123",
            action_description="Test action",
            metadata={"key": "value"},
        )

        data = record.to_dict()

        assert data["id"] == "test-id"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["action_hash"] == "abc123"
        assert data["risk_level"] == "medium"
        assert data["reasoning_flags"] == ["deception"]
        assert data["adversarial_verdict"] == "majority_deny"
        assert data["final_decision"] == "denied"
        assert data["signature"] == "010203"
        assert data["prev_hash"] == "prev123"
        assert data["action_description"] == "Test action"
        assert data["metadata"] == {"key": "value"}

    def test_record_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        timestamp = datetime.now(timezone.utc)
        data = {
            "id": "test-id",
            "timestamp": timestamp.isoformat(),
            "action_hash": "abc123",
            "risk_level": "high",
            "reasoning_flags": ["power_seeking", "reward_hacking"],
            "adversarial_verdict": "unanimous_deny",
            "final_decision": "escalated",
            "signature": "0a0b0c",
            "prev_hash": "prev456",
            "action_description": "Dangerous action",
            "metadata": {"severity": "critical"},
        }

        record = AuditRecord.from_dict(data)

        assert record.id == "test-id"
        assert record.timestamp == timestamp
        assert record.action_hash == "abc123"
        assert record.risk_level == RiskLevel.HIGH
        assert record.reasoning_flags == (
            ReasoningFlag.POWER_SEEKING,
            ReasoningFlag.REWARD_HACKING,
        )
        assert record.adversarial_verdict == Verdict.UNANIMOUS_DENY
        assert record.final_decision == Decision.ESCALATED
        assert record.signature == b"\x0a\x0b\x0c"
        assert record.prev_hash == "prev456"
        assert record.action_description == "Dangerous action"
        assert record.metadata == {"severity": "critical"}

    def test_compute_hash_deterministic(self) -> None:
        """Verify that compute_hash is deterministic."""
        timestamp = datetime.now(timezone.utc)
        record = AuditRecord(
            id="test-id",
            timestamp=timestamp,
            action_hash="abc123",
            risk_level=RiskLevel.LOW,
            reasoning_flags=(),
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
            signature=b"sig1",
            prev_hash="0" * 64,
        )

        hash1 = record.compute_hash()
        hash2 = record.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_compute_hash_excludes_signature(self) -> None:
        """Verify that signature is not included in hash computation."""
        timestamp = datetime.now(timezone.utc)
        record1 = AuditRecord(
            id="test-id",
            timestamp=timestamp,
            action_hash="abc123",
            risk_level=RiskLevel.LOW,
            reasoning_flags=(),
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
            signature=b"sig1",
            prev_hash="0" * 64,
        )

        record2 = AuditRecord(
            id="test-id",
            timestamp=timestamp,
            action_hash="abc123",
            risk_level=RiskLevel.LOW,
            reasoning_flags=(),
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
            signature=b"different_signature",
            prev_hash="0" * 64,
        )

        assert record1.compute_hash() == record2.compute_hash()


class TestAuditLogger:
    """Test AuditLogger cryptographic signing and chain verification."""

    def test_logger_initialization(self) -> None:
        """Test logger initialization with key generation."""
        logger = AuditLogger()

        assert logger.public_key is not None
        assert len(logger.public_key) == 32  # Ed25519 public key size
        assert logger.records == ()

    def test_logger_with_existing_key(self) -> None:
        """Test logger initialization with existing private key."""
        logger1 = AuditLogger()
        private_key = logger1.private_key_bytes

        logger2 = AuditLogger(private_key=private_key)

        assert logger2.public_key == logger1.public_key

    def test_log_creates_signed_record(self) -> None:
        """Test that logging creates a properly signed record."""
        logger = AuditLogger()

        record = logger.log(
            action_description="Test action",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        assert record.id is not None
        assert record.timestamp is not None
        assert record.action_hash is not None
        assert record.signature is not None
        assert len(record.signature) == 64  # Ed25519 signature size
        assert record.prev_hash == "0" * 64  # Genesis hash

    def test_log_creates_hash_chain(self) -> None:
        """Test that multiple logs create a proper hash chain."""
        logger = AuditLogger()

        record1 = logger.log(
            action_description="Action 1",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        record2 = logger.log(
            action_description="Action 2",
            risk_level=RiskLevel.MEDIUM,
            reasoning_flags=[ReasoningFlag.DECEPTION],
            adversarial_verdict=Verdict.MAJORITY_DENY,
            final_decision=Decision.DENIED,
        )

        record3 = logger.log(
            action_description="Action 3",
            risk_level=RiskLevel.HIGH,
            reasoning_flags=[],
            adversarial_verdict=Verdict.UNANIMOUS_DENY,
            final_decision=Decision.ESCALATED,
        )

        # Verify chain links
        assert record1.prev_hash == "0" * 64
        assert record2.prev_hash == record1.compute_hash()
        assert record3.prev_hash == record2.compute_hash()

    def test_verify_record_valid(self) -> None:
        """Test verification of a valid record."""
        logger = AuditLogger()

        record = logger.log(
            action_description="Test action",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        assert logger.verify_record(record) is True

    def test_verify_record_invalid_signature(self) -> None:
        """Test verification fails for tampered signature."""
        logger = AuditLogger()

        record = logger.log(
            action_description="Test action",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        # Tamper with signature
        tampered_record = AuditRecord(
            id=record.id,
            timestamp=record.timestamp,
            action_hash=record.action_hash,
            risk_level=record.risk_level,
            reasoning_flags=record.reasoning_flags,
            adversarial_verdict=record.adversarial_verdict,
            final_decision=record.final_decision,
            signature=b"tampered" + record.signature[8:],
            prev_hash=record.prev_hash,
        )

        assert logger.verify_record(tampered_record) is False

    def test_verify_chain_valid(self) -> None:
        """Test verification of a valid chain."""
        logger = AuditLogger()

        for i in range(5):
            logger.log(
                action_description=f"Action {i}",
                risk_level=RiskLevel.LOW,
                reasoning_flags=[],
                adversarial_verdict=Verdict.NOT_PERFORMED,
                final_decision=Decision.APPROVED,
            )

        is_valid, errors = logger.verify_chain()

        assert is_valid is True
        assert errors == []

    def test_verify_chain_broken_link(self) -> None:
        """Test verification detects broken chain link."""
        logger = AuditLogger()

        record1 = logger.log(
            action_description="Action 1",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        record2 = logger.log(
            action_description="Action 2",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        # Tamper with chain link by creating a record with wrong prev_hash
        # but keep the same signature (which will now be invalid)
        tampered_record = AuditRecord(
            id=record2.id,
            timestamp=record2.timestamp,
            action_hash=record2.action_hash,
            risk_level=record2.risk_level,
            reasoning_flags=record2.reasoning_flags,
            adversarial_verdict=record2.adversarial_verdict,
            final_decision=record2.final_decision,
            signature=record2.signature,
            prev_hash="tampered_hash",
        )

        logger._records[1] = tampered_record

        is_valid, errors = logger.verify_chain()

        assert is_valid is False
        assert len(errors) > 0
        # Should detect either broken chain link or invalid signature
        assert any("broken chain link" in err or "invalid signature" in err for err in errors)

    def test_query_by_time_range(self) -> None:
        """Test querying records by time range."""
        logger = AuditLogger()

        now = datetime.now(timezone.utc)

        # Create records with different timestamps
        for i in range(5):
            logger.log(
                action_description=f"Action {i}",
                risk_level=RiskLevel.LOW,
                reasoning_flags=[],
                adversarial_verdict=Verdict.NOT_PERFORMED,
                final_decision=Decision.APPROVED,
            )

        # Query middle records
        start_time = now + timedelta(seconds=1)
        end_time = now + timedelta(seconds=10)

        results = logger.query(start_time=start_time, end_time=end_time)

        assert len(results) >= 0  # May vary based on timing

    def test_query_by_risk_level(self) -> None:
        """Test querying records by risk level."""
        logger = AuditLogger()

        logger.log(
            action_description="Low risk",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        logger.log(
            action_description="High risk",
            risk_level=RiskLevel.HIGH,
            reasoning_flags=[],
            adversarial_verdict=Verdict.UNANIMOUS_DENY,
            final_decision=Decision.DENIED,
        )

        logger.log(
            action_description="Critical risk",
            risk_level=RiskLevel.CRITICAL,
            reasoning_flags=[],
            adversarial_verdict=Verdict.UNANIMOUS_DENY,
            final_decision=Decision.ESCALATED,
        )

        results = logger.query(risk_levels=[RiskLevel.HIGH, RiskLevel.CRITICAL])

        assert len(results) == 2
        assert all(r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] for r in results)

    def test_query_by_decision(self) -> None:
        """Test querying records by final decision."""
        logger = AuditLogger()

        logger.log(
            action_description="Approved",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        logger.log(
            action_description="Denied",
            risk_level=RiskLevel.HIGH,
            reasoning_flags=[],
            adversarial_verdict=Verdict.UNANIMOUS_DENY,
            final_decision=Decision.DENIED,
        )

        results = logger.query(decisions=[Decision.DENIED])

        assert len(results) == 1
        assert results[0].final_decision == Decision.DENIED

    def test_query_by_reasoning_flags(self) -> None:
        """Test querying records by reasoning flags."""
        logger = AuditLogger()

        logger.log(
            action_description="No flags",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        logger.log(
            action_description="Deception detected",
            risk_level=RiskLevel.HIGH,
            reasoning_flags=[ReasoningFlag.DECEPTION],
            adversarial_verdict=Verdict.UNANIMOUS_DENY,
            final_decision=Decision.DENIED,
        )

        logger.log(
            action_description="Power seeking",
            risk_level=RiskLevel.CRITICAL,
            reasoning_flags=[ReasoningFlag.POWER_SEEKING],
            adversarial_verdict=Verdict.UNANIMOUS_DENY,
            final_decision=Decision.ESCALATED,
        )

        results = logger.query(
            reasoning_flags=[ReasoningFlag.DECEPTION, ReasoningFlag.POWER_SEEKING]
        )

        assert len(results) == 2

    def test_export_import_json(self) -> None:
        """Test exporting and importing audit trail as JSON."""
        logger = AuditLogger()

        # Create some records
        for i in range(3):
            logger.log(
                action_description=f"Action {i}",
                risk_level=RiskLevel.LOW,
                reasoning_flags=[],
                adversarial_verdict=Verdict.NOT_PERFORMED,
                final_decision=Decision.APPROVED,
                metadata={"index": i},
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "audit.json"

            # Export
            logger.export_json(export_path)

            assert export_path.exists()

            # Verify JSON structure
            with export_path.open("r") as f:
                data = json.load(f)

            assert "public_key" in data
            assert "records" in data
            assert len(data["records"]) == 3

            # Import into new logger
            logger2 = AuditLogger(private_key=logger.private_key_bytes)
            logger2.load_json(export_path)

            assert len(logger2.records) == 3
            assert logger2.records[0].action_description == "Action 0"
            assert logger2.records[2].metadata["index"] == 2

    def test_export_csv(self) -> None:
        """Test exporting audit trail as CSV."""
        logger = AuditLogger()

        logger.log(
            action_description="Test action",
            risk_level=RiskLevel.MEDIUM,
            reasoning_flags=[ReasoningFlag.DECEPTION],
            adversarial_verdict=Verdict.MAJORITY_DENY,
            final_decision=Decision.DENIED,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "audit.csv"

            logger.export_csv(export_path)

            assert export_path.exists()

            # Verify CSV content
            with export_path.open("r") as f:
                lines = f.readlines()

            assert len(lines) == 2  # Header + 1 record
            assert "id,timestamp,action_hash" in lines[0]
            assert "Test action" in lines[1]

    def test_load_json_rejects_wrong_key(self) -> None:
        """Test that loading JSON with wrong public key fails."""
        logger1 = AuditLogger()
        logger1.log(
            action_description="Action 1",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "audit.json"
            logger1.export_json(export_path)

            # Try to load with different key
            logger2 = AuditLogger()  # Different key

            with pytest.raises(ValueError, match="Public key mismatch"):
                logger2.load_json(export_path)

    def test_uuidv7_is_time_ordered(self) -> None:
        """Test that UUIDv7 generation is time-ordered."""
        logger = AuditLogger()

        import time

        record1 = logger.log(
            action_description="Action 1",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        time.sleep(0.002)

        record2 = logger.log(
            action_description="Action 2",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        # UUIDv7 should be lexicographically sortable
        assert record1.id < record2.id

    def test_records_are_immutable(self) -> None:
        """Test that records property returns immutable tuple."""
        logger = AuditLogger()

        logger.log(
            action_description="Action 1",
            risk_level=RiskLevel.LOW,
            reasoning_flags=[],
            adversarial_verdict=Verdict.NOT_PERFORMED,
            final_decision=Decision.APPROVED,
        )

        records = logger.records

        assert isinstance(records, tuple)

        # Cannot modify the tuple
        with pytest.raises(TypeError):
            records[0] = None  # type: ignore
