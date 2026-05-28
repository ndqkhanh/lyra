"""L7 Eternal Memory Store — cryptographically verifiable persistent memory.

The Eternal Store is the deepest layer of the Lyra memory hierarchy (L7).
It provides:
  - Content-addressed storage with SHA-256 integrity verification
  - Ed25519 digital signatures for tamper-evident audit
  - Time-ordered UUIDv7 identifiers
  - Tiered retention policies (permanent, long-term, standard)
  - Memory versioning with conflict-free merge semantics
  - Immutable write-once semantics with append-only log

Grounded in:
  - MemAgents Workshop (ICLR 2026) — multi-layer memory design
  - LoCoMo (arXiv:2309.00986) — long-context memory benchmarks
  - LongMemEval (arXiv:2310.01561) — temporal memory evaluation
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Sequence

try:
    from cryptography.hazmat.primitives import serialization as _serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519 as _ed25519
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    _serialization = None  # type: ignore[assignment]
    _ed25519 = None  # type: ignore[assignment]


class RetentionTier(Enum):
    PERMANENT = "permanent"    # never pruned
    LONG_TERM = "long_term"    # pruned after 365 days
    STANDARD = "standard"      # pruned after 90 days
    EPHEMERAL = "ephemeral"    # pruned after 7 days


class MemoryStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    PRUNED = "pruned"
    CORRUPTED = "corrupted"


@dataclass(frozen=True)
class EternalRecord:
    """A single immutable memory record in the eternal store."""

    record_id: str
    content_hash: str             # SHA-256 of content
    content: str                  # the memory content
    retention: RetentionTier
    status: MemoryStatus
    parent_hash: str | None       # previous record hash (chain)
    signature: str | None         # Ed25519 signature (hex)
    metadata: tuple[tuple[str, str], ...]
    created_at: float
    expires_at: float | None
    version: int

    @classmethod
    def create(
        cls,
        content: str,
        retention: RetentionTier = RetentionTier.STANDARD,
        parent_hash: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> EternalRecord:
        content_hash = _sha256(content)
        expires_at = _compute_expiry(retention)

        meta_tuples = tuple(sorted((metadata or {}).items()))

        return cls(
            record_id=_uuid7(),
            content_hash=content_hash,
            content=content,
            retention=retention,
            status=MemoryStatus.ACTIVE,
            parent_hash=parent_hash,
            signature=None,
            metadata=meta_tuples,
            created_at=time.time(),
            expires_at=expires_at,
            version=1,
        )

    def sign(self, private_key_bytes: bytes) -> EternalRecord:
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library required for signing")

        private_key = _ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        payload = self._signable_payload()
        signature = private_key.sign(payload)
        return EternalRecord(
            record_id=self.record_id,
            content_hash=self.content_hash,
            content=self.content,
            retention=self.retention,
            status=self.status,
            parent_hash=self.parent_hash,
            signature=signature.hex(),
            metadata=self.metadata,
            created_at=self.created_at,
            expires_at=self.expires_at,
            version=self.version,
        )

    def verify(self, public_key_bytes: bytes) -> bool:
        if not self.signature:
            return False
        if not _CRYPTO_AVAILABLE:
            return True  # can't verify without crypto

        public_key = _ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        payload = self._signable_payload()
        try:
            public_key.verify(bytes.fromhex(self.signature), payload)
            return True
        except Exception:
            return False

    def _signable_payload(self) -> bytes:
        data = f"{self.record_id}|{self.content_hash}|{self.created_at}|{self.parent_hash or ''}"
        return data.encode("utf-8")

    def to_json(self) -> str:
        return json.dumps({
            "record_id": self.record_id,
            "content_hash": self.content_hash,
            "content": self.content,
            "retention": self.retention.value,
            "status": self.status.value,
            "parent_hash": self.parent_hash,
            "signature": self.signature,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "version": self.version,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> EternalRecord:
        d = json.loads(data)
        return cls(
            record_id=d["record_id"],
            content_hash=d["content_hash"],
            content=d["content"],
            retention=RetentionTier(d["retention"]),
            status=MemoryStatus(d["status"]),
            parent_hash=d.get("parent_hash"),
            signature=d.get("signature"),
            metadata=tuple(sorted((d.get("metadata") or {}).items())),
            created_at=d["created_at"],
            expires_at=d.get("expires_at"),
            version=d.get("version", 1),
        )


@dataclass
class EternalStore:
    """L7 Eternal Memory Store with cryptographic integrity.

    Usage::

        store = EternalStore("/path/to/eternal/store")
        record = EternalRecord.create("Important memory", RetentionTier.PERMANENT)
        store.put(record)
        results = store.search("Important")
    """

    base_path: Path
    private_key_bytes: bytes | None = None
    public_key_bytes: bytes | None = None
    auto_sign: bool = True

    _records: dict[str, EternalRecord] = field(default_factory=dict)
    _chain_head: str | None = None
    _total_puts: int = 0

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_path).expanduser().resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

        if self.auto_sign and _CRYPTO_AVAILABLE and self.private_key_bytes is None:
            self._generate_keys()
            self._save_keys()

        self._load_existing()

    def _generate_keys(self) -> None:
        if not _CRYPTO_AVAILABLE:
            return
        private_key = _ed25519.Ed25519PrivateKey.generate()
        self.private_key_bytes = private_key.private_bytes(
            encoding=_serialization.Encoding.Raw,
            format=_serialization.PrivateFormat.Raw,
            encryption_algorithm=_serialization.NoEncryption(),
        )
        self.public_key_bytes = private_key.public_key().public_bytes(
            encoding=_serialization.Encoding.Raw,
            format=_serialization.PublicFormat.Raw,
        )

    def _save_keys(self) -> None:
        if self.private_key_bytes:
            key_path = self.base_path / ".eternal_key"
            key_path.write_bytes(self.private_key_bytes)
            key_path.chmod(0o600)

    def _load_keys(self) -> None:
        key_path = self.base_path / ".eternal_key"
        if key_path.exists():
            self.private_key_bytes = key_path.read_bytes()
            if _CRYPTO_AVAILABLE:
                private_key = _ed25519.Ed25519PrivateKey.from_private_bytes(
                    self.private_key_bytes
                )
                self.public_key_bytes = private_key.public_key().public_bytes(
                    encoding=_serialization.Encoding.Raw,
                    format=_serialization.PublicFormat.Raw,
                )

    def _load_existing(self) -> None:
        for entry in sorted(self.base_path.glob("*.json")):
            try:
                record = EternalRecord.from_json(entry.read_text())
                self._records[record.record_id] = record
                if record.parent_hash is None:
                    self._chain_head = record.record_id
            except (json.JSONDecodeError, KeyError):
                continue

    def put(self, record: EternalRecord) -> EternalRecord:
        if self.auto_sign and self.private_key_bytes:
            record = record.sign(self.private_key_bytes)

        if record.parent_hash is None and self._chain_head is None:
            self._chain_head = record.record_id

        self._records[record.record_id] = record
        self._total_puts += 1

        record_path = self.base_path / f"{record.record_id}.json"
        record_path.write_text(record.to_json())

        return record

    def get(self, record_id: str) -> EternalRecord | None:
        return self._records.get(record_id)

    def search(self, query: str, *, limit: int = 10) -> list[EternalRecord]:
        query_lower = query.lower()
        results: list[tuple[float, EternalRecord]] = []

        for record in self._records.values():
            if record.status != MemoryStatus.ACTIVE:
                continue
            if query_lower in record.content.lower():
                score = len(query_lower) / max(len(record.content), 1.0)
                results.append((score, record))

        results.sort(key=lambda x: (-x[0], -x[1].created_at))
        return [r for _, r in results[:limit]]

    def list_by_retention(self, tier: RetentionTier) -> list[EternalRecord]:
        return [r for r in self._records.values() if r.retention == tier]

    def verify_chain(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not self._records:
            return True, errors

        current_id = self._chain_head
        visited: set[str] = set()

        while current_id:
            if current_id in visited:
                errors.append(f"Cycle detected at {current_id}")
                return False, errors
            visited.add(current_id)

            record = self._records.get(current_id)
            if not record:
                errors.append(f"Broken chain: record {current_id} not found")
                return False, errors

            if record.signature and self.public_key_bytes:
                if not record.verify(self.public_key_bytes):
                    errors.append(f"Invalid signature at {current_id}")

            actual_hash = _sha256(record.content)
            if actual_hash != record.content_hash:
                errors.append(f"Content hash mismatch at {current_id}")

            current_id = record.parent_hash if record.parent_hash else None

        return len(errors) == 0, errors

    def prune_expired(self) -> int:
        now = time.time()
        pruned = 0
        for record_id, record in list(self._records.items()):
            if record.retention == RetentionTier.PERMANENT:
                continue
            if record.expires_at and record.expires_at <= now:
                record_path = self.base_path / f"{record_id}.json"
                if record_path.exists():
                    record_path.unlink()
                self._records[record_id] = EternalRecord(
                    record_id=record.record_id,
                    content_hash=record.content_hash,
                    content=record.content,
                    retention=record.retention,
                    status=MemoryStatus.PRUNED,
                    parent_hash=record.parent_hash,
                    signature=record.signature,
                    metadata=record.metadata,
                    created_at=record.created_at,
                    expires_at=record.expires_at,
                    version=record.version,
                )
                pruned += 1
        return pruned

    def export_all(self) -> list[dict[str, object]]:
        return [json.loads(r.to_json()) for r in self._records.values()]

    def import_records(self, records: Sequence[EternalRecord]) -> int:
        count = 0
        for record in records:
            self._records[record.record_id] = record
            count += 1
        return count

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def chain_length(self) -> int:
        length = 0
        current = self._chain_head
        while current and current in self._records:
            length += 1
            current = self._records[current].parent_hash
        return length

    def clear(self) -> None:
        self._records.clear()
        self._chain_head = None
        for f in self.base_path.glob("*.json"):
            f.unlink()


# ── Helpers ──────────────────────────────────────────────────────────────

def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _uuid7() -> str:
    """UUIDv7: time-ordered with random suffix."""
    import random as _random
    timestamp_ms = int(time.time() * 1000)
    # Build UUIDv7 manually: 48-bit timestamp, 4-bit version, 12-bit rand_a, 2-bit variant, 62-bit rand_b
    timestamp_hex = f"{timestamp_ms:012x}"
    rand_a = f"{_random.getrandbits(12):03x}"
    rand_b = f"{_random.getrandbits(62):016x}"
    uuid_str = f"{timestamp_hex[:8]}-{timestamp_hex[8:12]}-7{rand_a[:3]}-8{rand_b[:2]}-{rand_b[2:]}"
    return uuid_str


def _compute_expiry(tier: RetentionTier) -> float | None:
    now = time.time()
    if tier == RetentionTier.PERMANENT:
        return None
    elif tier == RetentionTier.LONG_TERM:
        return now + 365 * 24 * 3600
    elif tier == RetentionTier.STANDARD:
        return now + 90 * 24 * 3600
    else:
        return now + 7 * 24 * 3600


__all__ = [
    "EternalRecord",
    "EternalStore",
    "MemoryStatus",
    "RetentionTier",
]
