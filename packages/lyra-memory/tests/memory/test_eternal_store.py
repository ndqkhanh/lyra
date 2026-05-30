"""Tests for eternal memory store with cryptographic integrity."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from lyra_memory.eternal_store import (
    EternalRecord,
    EternalStore,
    MemoryStatus,
    RetentionTier,
)


@pytest.fixture
def temp_store_path():
    """Create a temporary directory for store testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def eternal_store(temp_store_path):
    """Create an eternal store instance."""
    return EternalStore(base_path=temp_store_path, auto_sign=True)


class TestEternalRecord:
    """Test EternalRecord creation and operations."""

    def test_create_record(self):
        """Test creating a new eternal record."""
        record = EternalRecord.create(
            content="Important memory",
            retention=RetentionTier.PERMANENT,
            metadata={"source": "test"},
        )

        assert record.content == "Important memory"
        assert record.retention == RetentionTier.PERMANENT
        assert record.status == MemoryStatus.ACTIVE
        assert record.version == 1
        assert dict(record.metadata) == {"source": "test"}
        assert record.content_hash is not None
        assert record.record_id is not None

    def test_record_immutability(self):
        """Test that records are immutable."""
        record = EternalRecord.create("Test content")

        with pytest.raises(AttributeError):
            record.content = "Modified"  # type: ignore[misc]

    def test_record_serialization(self):
        """Test record JSON serialization and deserialization."""
        original = EternalRecord.create(
            content="Test memory",
            retention=RetentionTier.LONG_TERM,
            metadata={"key": "value"},
        )

        json_str = original.to_json()
        restored = EternalRecord.from_json(json_str)

        assert restored.content == original.content
        assert restored.retention == original.retention
        assert restored.metadata == original.metadata
        assert restored.content_hash == original.content_hash

    def test_record_signing(self):
        """Test record signing with Ed25519."""
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
        except ImportError:
            pytest.skip("cryptography library not available")

        # Generate key pair
        private_key = ed25519.Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.Raw,
            format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PrivateFormat"]).PrivateFormat.Raw,
            encryption_algorithm=__import__("cryptography.hazmat.primitives.serialization", fromlist=["NoEncryption"]).NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.Raw,
            format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.Raw,
        )

        # Create and sign record
        record = EternalRecord.create("Signed memory")
        signed_record = record.sign(private_bytes)

        assert signed_record.signature is not None
        assert signed_record.verify(public_bytes) is True

    def test_record_chain(self):
        """Test creating a chain of records."""
        record1 = EternalRecord.create("First memory")
        record2 = EternalRecord.create("Second memory", parent_hash=record1.content_hash)
        record3 = EternalRecord.create("Third memory", parent_hash=record2.content_hash)

        assert record1.parent_hash is None
        assert record2.parent_hash == record1.content_hash
        assert record3.parent_hash == record2.content_hash


class TestEternalStore:
    """Test EternalStore operations."""

    def test_store_initialization(self, temp_store_path):
        """Test store initialization creates directory."""
        store = EternalStore(base_path=temp_store_path / "new_store")
        assert (temp_store_path / "new_store").exists()

    def test_put_and_get(self, eternal_store):
        """Test storing and retrieving records."""
        record = EternalRecord.create("Test memory")
        stored = eternal_store.put(record)

        assert stored.signature is not None  # Auto-signed

        retrieved = eternal_store.get(record.record_id)
        assert retrieved is not None
        assert retrieved.content == "Test memory"

    def test_search(self, eternal_store):
        """Test searching records by content."""
        eternal_store.put(EternalRecord.create("Python programming"))
        eternal_store.put(EternalRecord.create("JavaScript development"))
        eternal_store.put(EternalRecord.create("Python testing"))

        results = eternal_store.search("Python")
        assert len(results) == 2
        assert all("Python" in r.content for r in results)

    def test_search_limit(self, eternal_store):
        """Test search result limiting."""
        for i in range(10):
            eternal_store.put(EternalRecord.create(f"Memory {i}"))

        results = eternal_store.search("Memory", limit=5)
        assert len(results) == 5

    def test_list_by_retention(self, eternal_store):
        """Test filtering records by retention tier."""
        eternal_store.put(EternalRecord.create("Permanent", RetentionTier.PERMANENT))
        eternal_store.put(EternalRecord.create("Long term", RetentionTier.LONG_TERM))
        eternal_store.put(EternalRecord.create("Standard", RetentionTier.STANDARD))

        permanent = eternal_store.list_by_retention(RetentionTier.PERMANENT)
        assert len(permanent) == 1
        assert permanent[0].content == "Permanent"

    def test_verify_chain(self, eternal_store):
        """Test chain integrity verification."""
        record1 = EternalRecord.create("First")
        eternal_store.put(record1)

        record2 = EternalRecord.create("Second", parent_hash=record1.content_hash)
        eternal_store.put(record2)

        is_valid, errors = eternal_store.verify_chain()
        assert is_valid is True
        assert len(errors) == 0

    def test_prune_expired(self, eternal_store):
        """Test pruning expired records."""
        # Create ephemeral record (7 days)
        record = EternalRecord.create("Ephemeral", RetentionTier.EPHEMERAL)

        # Manually set expiry to past
        expired_record = EternalRecord(
            record_id=record.record_id,
            content_hash=record.content_hash,
            content=record.content,
            retention=record.retention,
            status=record.status,
            parent_hash=record.parent_hash,
            signature=record.signature,
            metadata=record.metadata,
            created_at=record.created_at,
            expires_at=time.time() - 1,  # Expired 1 second ago
            version=record.version,
        )

        eternal_store.put(expired_record)

        pruned_count = eternal_store.prune_expired()
        assert pruned_count == 1

        # Record should be marked as pruned
        retrieved = eternal_store.get(expired_record.record_id)
        assert retrieved is not None
        assert retrieved.status == MemoryStatus.PRUNED

    def test_permanent_not_pruned(self, eternal_store):
        """Test that permanent records are never pruned."""
        record = EternalRecord.create("Permanent", RetentionTier.PERMANENT)
        eternal_store.put(record)

        pruned_count = eternal_store.prune_expired()
        assert pruned_count == 0

        retrieved = eternal_store.get(record.record_id)
        assert retrieved.status == MemoryStatus.ACTIVE

    def test_export_import(self, eternal_store):
        """Test exporting and importing records."""
        record1 = EternalRecord.create("Memory 1")
        record2 = EternalRecord.create("Memory 2")

        eternal_store.put(record1)
        eternal_store.put(record2)

        # Export
        exported = eternal_store.export_all()
        assert len(exported) == 2

        # Create new store and import
        new_store = EternalStore(base_path=eternal_store.base_path.parent / "new_store")
        records = [EternalRecord.from_json(json.dumps(r)) for r in exported]
        imported_count = new_store.import_records(records)

        assert imported_count == 2
        assert new_store.size == 2

    def test_persistence(self, temp_store_path):
        """Test that records persist across store instances."""
        # Create store and add records
        store1 = EternalStore(base_path=temp_store_path / "persistent")
        record = EternalRecord.create("Persistent memory")
        store1.put(record)

        # Create new store instance with same path
        store2 = EternalStore(base_path=temp_store_path / "persistent")

        # Should load existing records
        retrieved = store2.get(record.record_id)
        assert retrieved is not None
        assert retrieved.content == "Persistent memory"

    def test_chain_length(self, eternal_store):
        """Test chain length calculation."""
        record1 = EternalRecord.create("First")
        stored1 = eternal_store.put(record1)

        record2 = EternalRecord.create("Second", parent_hash=stored1.content_hash)
        stored2 = eternal_store.put(record2)

        record3 = EternalRecord.create("Third", parent_hash=stored2.content_hash)
        eternal_store.put(record3)

        # Chain length should be at least 1 (chain head exists)
        assert eternal_store.chain_length >= 1

    def test_size_property(self, eternal_store):
        """Test store size property."""
        assert eternal_store.size == 0

        eternal_store.put(EternalRecord.create("Memory 1"))
        assert eternal_store.size == 1

        eternal_store.put(EternalRecord.create("Memory 2"))
        assert eternal_store.size == 2

    def test_clear(self, eternal_store):
        """Test clearing all records."""
        eternal_store.put(EternalRecord.create("Memory 1"))
        eternal_store.put(EternalRecord.create("Memory 2"))

        assert eternal_store.size == 2

        eternal_store.clear()

        assert eternal_store.size == 0
        assert eternal_store.chain_length == 0


class TestRetentionPolicies:
    """Test retention tier policies."""

    def test_permanent_no_expiry(self):
        """Test permanent records have no expiry."""
        record = EternalRecord.create("Permanent", RetentionTier.PERMANENT)
        assert record.expires_at is None

    def test_long_term_expiry(self):
        """Test long-term records expire after 365 days."""
        record = EternalRecord.create("Long term", RetentionTier.LONG_TERM)
        assert record.expires_at is not None

        # Should expire in ~365 days
        days_until_expiry = (record.expires_at - time.time()) / (24 * 3600)
        assert 364 < days_until_expiry < 366

    def test_standard_expiry(self):
        """Test standard records expire after 90 days."""
        record = EternalRecord.create("Standard", RetentionTier.STANDARD)
        assert record.expires_at is not None

        # Should expire in ~90 days
        days_until_expiry = (record.expires_at - time.time()) / (24 * 3600)
        assert 89 < days_until_expiry < 91

    def test_ephemeral_expiry(self):
        """Test ephemeral records expire after 7 days."""
        record = EternalRecord.create("Ephemeral", RetentionTier.EPHEMERAL)
        assert record.expires_at is not None

        # Should expire in ~7 days
        days_until_expiry = (record.expires_at - time.time()) / (24 * 3600)
        assert 6 < days_until_expiry < 8


class TestIntegration:
    """Integration tests for eternal store."""

    def test_full_workflow(self, eternal_store):
        """Test complete workflow: create, store, search, verify, prune."""
        # Create records
        record1 = EternalRecord.create("Python best practices", RetentionTier.PERMANENT)
        record2 = EternalRecord.create("Python testing guide", RetentionTier.LONG_TERM)
        record3 = EternalRecord.create("JavaScript basics", RetentionTier.STANDARD)

        # Store records
        eternal_store.put(record1)
        eternal_store.put(record2)
        eternal_store.put(record3)

        # Search
        python_results = eternal_store.search("Python")
        assert len(python_results) == 2

        # Verify chain
        is_valid, errors = eternal_store.verify_chain()
        assert is_valid is True

        # List by retention
        permanent = eternal_store.list_by_retention(RetentionTier.PERMANENT)
        assert len(permanent) == 1

        # Prune (should not prune anything as nothing expired)
        pruned = eternal_store.prune_expired()
        assert pruned == 0

        # Export
        exported = eternal_store.export_all()
        assert len(exported) == 3
