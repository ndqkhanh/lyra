"""Tests for cryptographic integrity module."""

import json
import tempfile
from pathlib import Path

import pytest

from lyra_memory.eternal.crypto_integrity import (
    CRYPTO_AVAILABLE,
    CryptoKeyPair,
    IntegrityVerifier,
    SignatureError,
    create_audit_entry,
    generate_keypair,
    sign_content,
    verify_audit_entry,
    verify_signature,
)


@pytest.fixture
def keypair():
    """Generate a test key pair."""
    if not CRYPTO_AVAILABLE:
        pytest.skip("cryptography library not available")
    return generate_keypair()


@pytest.fixture
def temp_key_path():
    """Create a temporary path for key storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_key.json"


class TestKeyGeneration:
    """Test key generation and management."""

    def test_generate_keypair(self):
        """Test generating a new Ed25519 key pair."""
        if not CRYPTO_AVAILABLE:
            pytest.skip("cryptography library not available")

        keypair = generate_keypair()

        assert keypair.private_key_bytes is not None
        assert keypair.public_key_bytes is not None
        assert len(keypair.private_key_bytes) == 32
        assert len(keypair.public_key_bytes) == 32

    def test_keypair_immutability(self, keypair):
        """Test that key pairs are immutable."""
        with pytest.raises(AttributeError):
            keypair.private_key_bytes = b"modified"  # type: ignore[misc]

    def test_keypair_serialization(self, keypair):
        """Test key pair serialization to dictionary."""
        data = keypair.to_dict()

        assert "private_key" in data
        assert "public_key" in data
        assert isinstance(data["private_key"], str)
        assert isinstance(data["public_key"], str)

    def test_keypair_deserialization(self, keypair):
        """Test key pair deserialization from dictionary."""
        data = keypair.to_dict()
        restored = CryptoKeyPair.from_dict(data)

        assert restored.private_key_bytes == keypair.private_key_bytes
        assert restored.public_key_bytes == keypair.public_key_bytes

    def test_save_and_load_keypair(self, keypair, temp_key_path):
        """Test saving and loading key pair from file."""
        # Save
        keypair.save_to_file(temp_key_path)
        assert temp_key_path.exists()

        # Check permissions (should be 0o600)
        import stat
        mode = temp_key_path.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600

        # Load
        loaded = CryptoKeyPair.load_from_file(temp_key_path)
        assert loaded.private_key_bytes == keypair.private_key_bytes
        assert loaded.public_key_bytes == keypair.public_key_bytes


class TestSigning:
    """Test content signing operations."""

    def test_sign_content(self, keypair):
        """Test signing content with private key."""
        content = "Important memory to sign"
        signature = sign_content(content, keypair.private_key_bytes)

        assert signature is not None
        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_verify_signature_valid(self, keypair):
        """Test verifying a valid signature."""
        content = "Test content"
        signature = sign_content(content, keypair.private_key_bytes)

        is_valid = verify_signature(content, signature, keypair.public_key_bytes)
        assert is_valid is True

    def test_verify_signature_invalid_content(self, keypair):
        """Test that modified content fails verification."""
        content = "Original content"
        signature = sign_content(content, keypair.private_key_bytes)

        # Modify content
        modified_content = "Modified content"
        is_valid = verify_signature(modified_content, signature, keypair.public_key_bytes)
        assert is_valid is False

    def test_verify_signature_invalid_signature(self, keypair):
        """Test that invalid signature fails verification."""
        content = "Test content"
        fake_signature = "0" * 128  # Invalid signature

        is_valid = verify_signature(content, fake_signature, keypair.public_key_bytes)
        assert is_valid is False

    def test_keypair_sign_method(self, keypair):
        """Test CryptoKeyPair.sign method."""
        data = b"Test data"
        signature = keypair.sign(data)

        assert signature is not None
        assert isinstance(signature, bytes)

    def test_keypair_verify_method(self, keypair):
        """Test CryptoKeyPair.verify method."""
        data = b"Test data"
        signature = keypair.sign(data)

        is_valid = keypair.verify(data, signature)
        assert is_valid is True

        # Test with wrong data
        is_valid = keypair.verify(b"Wrong data", signature)
        assert is_valid is False


class TestIntegrityVerifier:
    """Test IntegrityVerifier class."""

    def test_verify_record_valid(self, keypair):
        """Test verifying a valid record."""
        import hashlib
        import time

        content = "Test memory"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        record_data = {
            "record_id": "test-record-1",
            "content": content,
            "content_hash": content_hash,
            "created_at": time.time(),
            "parent_hash": None,
        }

        # Sign the record
        payload = f"{record_data['record_id']}|{record_data['content_hash']}|{record_data['created_at']}|"
        signature = sign_content(payload, keypair.private_key_bytes)
        record_data["signature"] = signature

        verifier = IntegrityVerifier(public_key_bytes=keypair.public_key_bytes)
        is_valid, errors = verifier.verify_record(record_data)

        assert is_valid is True
        assert len(errors) == 0

    def test_verify_record_invalid_hash(self, keypair):
        """Test detecting content hash mismatch."""
        import time

        record_data = {
            "record_id": "test-record-1",
            "content": "Test memory",
            "content_hash": "invalid_hash",
            "created_at": time.time(),
            "parent_hash": None,
        }

        verifier = IntegrityVerifier(public_key_bytes=keypair.public_key_bytes)
        is_valid, errors = verifier.verify_record(record_data)

        assert is_valid is False
        assert len(errors) > 0
        assert "Content hash mismatch" in errors[0]

    def test_verify_record_invalid_signature(self, keypair):
        """Test detecting invalid signature."""
        import hashlib
        import time

        content = "Test memory"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        record_data = {
            "record_id": "test-record-1",
            "content": content,
            "content_hash": content_hash,
            "created_at": time.time(),
            "parent_hash": None,
            "signature": "invalid_signature",
        }

        verifier = IntegrityVerifier(public_key_bytes=keypair.public_key_bytes)
        is_valid, errors = verifier.verify_record(record_data)

        assert is_valid is False
        assert any("Invalid signature" in e for e in errors)

    def test_verify_chain_valid(self, keypair):
        """Test verifying a valid chain of records."""
        import hashlib
        import time

        records = []
        prev_record_id = None

        for i in range(3):
            content = f"Memory {i}"
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            record = {
                "record_id": f"record-{i}",
                "content": content,
                "content_hash": content_hash,
                "created_at": time.time() + i,
                "parent_hash": prev_record_id,  # Link to previous record ID, not hash
            }

            # Sign
            payload = f"{record['record_id']}|{record['content_hash']}|{record['created_at']}|{record.get('parent_hash') or ''}"
            record["signature"] = sign_content(payload, keypair.private_key_bytes)

            records.append(record)
            prev_record_id = record["record_id"]

        verifier = IntegrityVerifier(public_key_bytes=keypair.public_key_bytes)
        is_valid, errors = verifier.verify_chain(records)

        assert is_valid is True
        assert len(errors) == 0

    def test_verify_chain_broken_link(self, keypair):
        """Test detecting broken chain links."""
        import hashlib
        import time

        record1 = {
            "record_id": "record-1",
            "content": "Memory 1",
            "content_hash": hashlib.sha256(b"Memory 1").hexdigest(),
            "created_at": time.time(),
            "parent_hash": None,
        }

        record2 = {
            "record_id": "record-2",
            "content": "Memory 2",
            "content_hash": hashlib.sha256(b"Memory 2").hexdigest(),
            "created_at": time.time(),
            "parent_hash": "missing_parent_hash",  # Broken link
        }

        verifier = IntegrityVerifier(public_key_bytes=keypair.public_key_bytes)
        is_valid, errors = verifier.verify_chain([record1, record2])

        assert is_valid is False
        assert any("Broken chain" in e for e in errors)

    def test_verify_chain_cycle(self, keypair):
        """Test detecting cycles in chain."""
        import hashlib
        import time

        record1 = {
            "record_id": "record-1",
            "content": "Memory 1",
            "content_hash": hashlib.sha256(b"Memory 1").hexdigest(),
            "created_at": time.time(),
            "parent_hash": "record-2",  # Points to record2
        }

        record2 = {
            "record_id": "record-2",
            "content": "Memory 2",
            "content_hash": hashlib.sha256(b"Memory 2").hexdigest(),
            "created_at": time.time(),
            "parent_hash": "record-1",  # Points back to record1 (cycle)
        }

        verifier = IntegrityVerifier(public_key_bytes=keypair.public_key_bytes)
        is_valid, errors = verifier.verify_chain([record1, record2])

        assert is_valid is False
        assert any("Cycle detected" in e for e in errors)

    def test_compute_chain_hash(self, keypair):
        """Test computing deterministic chain hash."""
        import hashlib
        import time

        records = [
            {
                "record_id": "record-1",
                "content": "Memory 1",
                "content_hash": hashlib.sha256(b"Memory 1").hexdigest(),
                "created_at": time.time(),
            },
            {
                "record_id": "record-2",
                "content": "Memory 2",
                "content_hash": hashlib.sha256(b"Memory 2").hexdigest(),
                "created_at": time.time() + 1,
            },
        ]

        verifier = IntegrityVerifier(public_key_bytes=keypair.public_key_bytes)
        chain_hash1 = verifier.compute_chain_hash(records)
        chain_hash2 = verifier.compute_chain_hash(records)

        # Should be deterministic
        assert chain_hash1 == chain_hash2

        # Should change if records change
        records[0]["content_hash"] = "modified"
        chain_hash3 = verifier.compute_chain_hash(records)
        assert chain_hash3 != chain_hash1


class TestAuditLog:
    """Test audit log entry creation and verification."""

    def test_create_audit_entry(self, keypair):
        """Test creating a signed audit entry."""
        entry = create_audit_entry(
            action="CREATE",
            record_id="record-1",
            content_hash="abc123",
            keypair=keypair,
            metadata={"user": "test"},
        )

        assert entry["action"] == "CREATE"
        assert entry["record_id"] == "record-1"
        assert entry["content_hash"] == "abc123"
        assert entry["signature"] is not None
        assert entry["metadata"]["user"] == "test"
        assert "timestamp" in entry

    def test_verify_audit_entry_valid(self, keypair):
        """Test verifying a valid audit entry."""
        entry = create_audit_entry(
            action="UPDATE",
            record_id="record-2",
            content_hash="def456",
            keypair=keypair,
        )

        is_valid = verify_audit_entry(entry, keypair.public_key_bytes)
        assert is_valid is True

    def test_verify_audit_entry_tampered(self, keypair):
        """Test detecting tampered audit entry."""
        entry = create_audit_entry(
            action="DELETE",
            record_id="record-3",
            content_hash="ghi789",
            keypair=keypair,
        )

        # Tamper with entry
        entry["action"] = "CREATE"  # Changed action

        is_valid = verify_audit_entry(entry, keypair.public_key_bytes)
        assert is_valid is False

    def test_audit_entry_no_signature(self, keypair):
        """Test that entry without signature fails verification."""
        entry = {
            "action": "CREATE",
            "record_id": "record-1",
            "content_hash": "abc123",
            "timestamp": 123456789,
            "metadata": {},
        }

        is_valid = verify_audit_entry(entry, keypair.public_key_bytes)
        assert is_valid is False


class TestCryptoAvailability:
    """Test behavior when cryptography library is not available."""

    def test_crypto_available_flag(self):
        """Test CRYPTO_AVAILABLE flag reflects library availability."""
        assert isinstance(CRYPTO_AVAILABLE, bool)

    def test_operations_without_crypto(self):
        """Test that operations handle missing crypto library gracefully."""
        if CRYPTO_AVAILABLE:
            pytest.skip("cryptography library is available")

        # Should raise RuntimeError when crypto is required
        with pytest.raises(RuntimeError, match="cryptography library"):
            generate_keypair()


class TestIntegration:
    """Integration tests for crypto integrity."""

    def test_full_signing_workflow(self, keypair):
        """Test complete signing and verification workflow."""
        # Create content
        content = "Critical system memory"

        # Sign
        signature = sign_content(content, keypair.private_key_bytes)

        # Verify
        is_valid = verify_signature(content, signature, keypair.public_key_bytes)
        assert is_valid is True

        # Verify fails with wrong content
        is_valid = verify_signature("Wrong content", signature, keypair.public_key_bytes)
        assert is_valid is False

    def test_key_persistence_workflow(self, keypair, temp_key_path):
        """Test saving, loading, and using keys."""
        # Save keys
        keypair.save_to_file(temp_key_path)

        # Load keys in new instance
        loaded_keypair = CryptoKeyPair.load_from_file(temp_key_path)

        # Sign with original, verify with loaded
        content = "Test content"
        signature = sign_content(content, keypair.private_key_bytes)
        is_valid = verify_signature(content, signature, loaded_keypair.public_key_bytes)

        assert is_valid is True

    def test_audit_trail_workflow(self, keypair):
        """Test creating and verifying an audit trail."""
        audit_trail = []

        # Create multiple audit entries
        for i in range(5):
            entry = create_audit_entry(
                action="CREATE" if i == 0 else "UPDATE",
                record_id=f"record-{i}",
                content_hash=f"hash-{i}",
                keypair=keypair,
                metadata={"step": i},
            )
            audit_trail.append(entry)

        # Verify all entries
        for entry in audit_trail:
            is_valid = verify_audit_entry(entry, keypair.public_key_bytes)
            assert is_valid is True

        # Tamper with one entry
        audit_trail[2]["action"] = "DELETE"

        # Verification should fail for tampered entry
        is_valid = verify_audit_entry(audit_trail[2], keypair.public_key_bytes)
        assert is_valid is False

        # Other entries should still be valid
        is_valid = verify_audit_entry(audit_trail[0], keypair.public_key_bytes)
        assert is_valid is True
