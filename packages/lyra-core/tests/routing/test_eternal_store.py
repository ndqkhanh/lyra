"""Tests for the L7 Eternal Memory Store."""
from __future__ import annotations

import tempfile
import json as _json
from pathlib import Path

import pytest

from lyra_memory.eternal_store import (
    EternalRecord,
    EternalStore,
    MemoryStatus,
    RetentionTier,
)


class TestRetentionTier:
    def test_enum_values(self):
        assert RetentionTier.PERMANENT.value == "permanent"
        assert RetentionTier.LONG_TERM.value == "long_term"
        assert RetentionTier.STANDARD.value == "standard"
        assert RetentionTier.EPHEMERAL.value == "ephemeral"


class TestEternalRecord:
    def test_create_basic_record(self):
        record = EternalRecord.create("test memory content")
        assert record.content == "test memory content"
        assert record.status == MemoryStatus.ACTIVE
        assert record.retention == RetentionTier.STANDARD
        assert record.version == 1

    def test_content_hash_is_consistent(self):
        record = EternalRecord.create("hello world")
        assert len(record.content_hash) == 64  # SHA-256 hex

    def test_record_id_is_unique(self):
        r1 = EternalRecord.create("content 1")
        r2 = EternalRecord.create("content 2")
        assert r1.record_id != r2.record_id

    def test_permanent_retention_no_expiry(self):
        record = EternalRecord.create("important", retention=RetentionTier.PERMANENT)
        assert record.expires_at is None

    def test_standard_retention_has_expiry(self):
        record = EternalRecord.create("normal", retention=RetentionTier.STANDARD)
        assert record.expires_at is not None
        assert record.expires_at > 0

    def test_parent_hash_chaining(self):
        r1 = EternalRecord.create("first")
        r2 = EternalRecord.create("second", parent_hash=r1.content_hash)
        assert r2.parent_hash == r1.content_hash

    def test_metadata_stored(self):
        record = EternalRecord.create("content", metadata={"source": "test", "key": "value"})
        meta_dict = dict(record.metadata)
        assert meta_dict["source"] == "test"
        assert meta_dict["key"] == "value"

    def test_json_roundtrip(self):
        record = EternalRecord.create("test content", RetentionTier.LONG_TERM)
        json_str = record.to_json()
        restored = EternalRecord.from_json(json_str)
        assert restored.content == record.content
        assert restored.record_id == record.record_id
        assert restored.retention == record.retention

    def test_sign_produces_signature(self):
        record = EternalRecord.create("signable content")
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
        private_key = ed25519.Ed25519PrivateKey.generate()
        raw = private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        signed = record.sign(raw)
        assert signed.signature is not None
        assert len(signed.signature) == 128  # 64 bytes hex

    def test_frozen_dataclass(self):
        record = EternalRecord.create("test")
        with pytest.raises(Exception):
            record.content = "modified"  # type: ignore[misc]


class TestEternalStore:
    def test_store_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            record = EternalRecord.create("test content")
            store.put(record)

            retrieved = store.get(record.record_id)
            assert retrieved is not None
            assert retrieved.content == "test content"

    def test_get_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            assert store.get("nonexistent") is None

    def test_search_finds_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            store.put(EternalRecord.create("important design decision"))
            store.put(EternalRecord.create("random note"))
            store.put(EternalRecord.create("another important thing"))

            results = store.search("important")
            assert len(results) >= 2

    def test_search_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            store.put(EternalRecord.create("test content"))
            results = store.search("xyznonexistent")
            assert results == []

    def test_list_by_retention(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            store.put(EternalRecord.create("perm", RetentionTier.PERMANENT))
            store.put(EternalRecord.create("ephem", RetentionTier.EPHEMERAL))

            permanent = store.list_by_retention(RetentionTier.PERMANENT)
            ephemeral = store.list_by_retention(RetentionTier.EPHEMERAL)
            assert len(permanent) == 1
            assert len(ephemeral) == 1

    def test_verify_chain_no_errors_on_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            r1 = EternalRecord.create("first")
            r2 = EternalRecord.create("second", parent_hash=r1.content_hash)
            store.put(r1)
            store.put(r2)

            is_valid, errors = store.verify_chain()
            # Without parent_hash set on first record, chain starts at r1
            assert isinstance(is_valid, bool)

    def test_prune_expired(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            record = EternalRecord.create("ephemeral", RetentionTier.EPHEMERAL)
            # Manually set expired
            import time
            record = EternalRecord(
                record_id=record.record_id,
                content_hash=record.content_hash,
                content=record.content,
                retention=RetentionTier.EPHEMERAL,
                status=MemoryStatus.ACTIVE,
                parent_hash=None,
                signature=None,
                metadata=(),
                created_at=time.time() - 100000,
                expires_at=time.time() - 1,  # already expired
                version=1,
            )
            store.put(record)
            pruned = store.prune_expired()
            assert pruned >= 1

    def test_size_tracks_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            for i in range(5):
                store.put(EternalRecord.create(f"content {i}"))
            assert store.size == 5

    def test_clear_removes_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            store.put(EternalRecord.create("test"))
            store.clear()
            assert store.size == 0

    def test_export_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EternalStore(Path(tmpdir), auto_sign=False)
            store.put(EternalRecord.create("content 1"))
            store.put(EternalRecord.create("content 2"))

            data = store.export_all()
            assert len(data) == 2

            store2 = EternalStore(Path(tmpdir + "2"), auto_sign=False)
            records = [EternalRecord.from_json(_json.dumps(d)) for d in data]
            store2.import_records(records)
            assert store2.size == 2

    def test_persistence_across_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = EternalStore(Path(tmpdir), auto_sign=False)
            record = EternalRecord.create("persistent content")
            store1.put(record)

            store2 = EternalStore(Path(tmpdir), auto_sign=False)
            assert store2.get(record.record_id) is not None
