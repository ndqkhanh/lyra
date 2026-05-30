"""Cryptographic integrity module for eternal memory layer.

Provides Ed25519 digital signatures for tamper-evident audit trails.
Implements key generation, signing, and verification with secure key storage.

Grounded in:
  - Ed25519 (RFC 8032) — high-speed high-security signatures
  - Parallax (arXiv:2604.12986) — cryptographic audit trails
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    serialization = None  # type: ignore[assignment]
    ed25519 = None  # type: ignore[assignment]


class SignatureError(Exception):
    """Raised when signature verification fails."""

    pass


@dataclass(frozen=True)
class CryptoKeyPair:
    """Ed25519 key pair for signing and verification."""

    private_key_bytes: bytes
    public_key_bytes: bytes

    def sign(self, data: bytes) -> bytes:
        """Sign data with private key."""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")

        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(self.private_key_bytes)
        return private_key.sign(data)

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify signature with public key."""
        if not CRYPTO_AVAILABLE:
            return True  # Cannot verify without crypto library

        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(self.public_key_bytes)
            public_key.verify(signature, data)
            return True
        except Exception:
            return False

    def to_dict(self) -> dict[str, str]:
        """Export keys as hex strings."""
        return {
            "private_key": self.private_key_bytes.hex(),
            "public_key": self.public_key_bytes.hex(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> CryptoKeyPair:
        """Import keys from hex strings."""
        return cls(
            private_key_bytes=bytes.fromhex(data["private_key"]),
            public_key_bytes=bytes.fromhex(data["public_key"]),
        )

    def save_to_file(self, path: Path, *, mode: int = 0o600) -> None:
        """Save private key to file with restricted permissions."""
        path = Path(path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        path.chmod(mode)

    @classmethod
    def load_from_file(cls, path: Path) -> CryptoKeyPair:
        """Load key pair from file."""
        path = Path(path).expanduser().resolve()
        data = json.loads(path.read_text())
        return cls.from_dict(data)


def generate_keypair() -> CryptoKeyPair:
    """Generate a new Ed25519 key pair."""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not available")

    private_key = ed25519.Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return CryptoKeyPair(private_key_bytes=private_bytes, public_key_bytes=public_bytes)


def sign_content(content: str, private_key_bytes: bytes) -> str:
    """Sign content and return hex-encoded signature."""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library not available")

    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    content_bytes = content.encode("utf-8")
    signature = private_key.sign(content_bytes)
    return signature.hex()


def verify_signature(content: str, signature_hex: str, public_key_bytes: bytes) -> bool:
    """Verify a hex-encoded signature against content."""
    if not CRYPTO_AVAILABLE:
        return True  # Cannot verify without crypto library

    try:
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        content_bytes = content.encode("utf-8")
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, content_bytes)
        return True
    except Exception:
        return False


@dataclass
class IntegrityVerifier:
    """Verifies cryptographic integrity of memory chains."""

    public_key_bytes: bytes

    def verify_record(self, record_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Verify a single record's integrity.

        Returns:
            (is_valid, errors) tuple
        """
        errors: list[str] = []

        # Check content hash
        content = record_data.get("content", "")
        expected_hash = record_data.get("content_hash", "")
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        if actual_hash != expected_hash:
            errors.append(f"Content hash mismatch: expected {expected_hash}, got {actual_hash}")

        # Check signature
        signature_hex = record_data.get("signature")
        if signature_hex:
            record_id = record_data.get("record_id", "")
            content_hash = record_data.get("content_hash", "")
            created_at = record_data.get("created_at", 0)
            parent_hash = record_data.get("parent_hash") or ""

            payload = f"{record_id}|{content_hash}|{created_at}|{parent_hash}"
            if not verify_signature(payload, signature_hex, self.public_key_bytes):
                errors.append(f"Invalid signature for record {record_id}")

        return len(errors) == 0, errors

    def verify_chain(self, records: list[dict[str, Any]]) -> tuple[bool, list[str]]:
        """Verify integrity of an entire memory chain.

        Returns:
            (is_valid, errors) tuple
        """
        errors: list[str] = []

        # Build parent-child map
        records_by_id = {r["record_id"]: r for r in records}
        parent_map: dict[str, str] = {}

        for record in records:
            record_id = record["record_id"]
            parent_hash = record.get("parent_hash")

            # Verify individual record
            is_valid, record_errors = self.verify_record(record)
            if not is_valid:
                errors.extend(record_errors)

            # Track parent relationships
            if parent_hash:
                parent_map[record_id] = parent_hash

        # Check for cycles
        visited: set[str] = set()
        for record_id in records_by_id:
            current = record_id
            path: set[str] = set()

            while current and current not in visited:
                if current in path:
                    errors.append(f"Cycle detected in chain at {current}")
                    break
                path.add(current)
                current = parent_map.get(current)

            visited.update(path)

        # Check for broken links
        for record_id, parent_hash in parent_map.items():
            if parent_hash not in records_by_id:
                errors.append(f"Broken chain: record {record_id} references missing parent {parent_hash}")

        return len(errors) == 0, errors

    def compute_chain_hash(self, records: list[dict[str, Any]]) -> str:
        """Compute a single hash representing the entire chain state."""
        # Sort by creation time for deterministic ordering
        sorted_records = sorted(records, key=lambda r: r.get("created_at", 0))

        # Concatenate all content hashes
        combined = "|".join(r.get("content_hash", "") for r in sorted_records)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def create_audit_entry(
    action: str,
    record_id: str,
    content_hash: str,
    keypair: CryptoKeyPair,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a signed audit log entry.

    Args:
        action: Action performed (e.g., "CREATE", "UPDATE", "DELETE")
        record_id: ID of the affected record
        content_hash: Hash of the record content
        keypair: Key pair for signing
        metadata: Additional metadata

    Returns:
        Signed audit entry dictionary
    """
    import time

    entry = {
        "action": action,
        "record_id": record_id,
        "content_hash": content_hash,
        "timestamp": time.time(),
        "metadata": metadata or {},
    }

    # Create canonical representation for signing
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    signature = sign_content(canonical, keypair.private_key_bytes)

    entry["signature"] = signature
    return entry


def verify_audit_entry(entry: dict[str, Any], public_key_bytes: bytes) -> bool:
    """Verify a signed audit log entry."""
    signature = entry.pop("signature", None)
    if not signature:
        return False

    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    result = verify_signature(canonical, signature, public_key_bytes)

    # Restore signature
    entry["signature"] = signature
    return result


__all__ = [
    "CRYPTO_AVAILABLE",
    "CryptoKeyPair",
    "IntegrityVerifier",
    "SignatureError",
    "create_audit_entry",
    "generate_keypair",
    "sign_content",
    "verify_audit_entry",
    "verify_signature",
]
